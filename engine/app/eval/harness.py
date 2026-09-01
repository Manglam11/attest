import glob
import json
import os
import time
from datetime import datetime, timezone

import httpx

from app.eval.gold_set import GOLD_SET
from app.quota import remaining, used_today

ENGINE_URL = os.environ.get("ENGINE_URL", "http://engine:8000")
OUTPUT_DIR = "/code/data/eval"
PACE_SECONDS = float(os.environ.get("PACE_SECONDS", "30"))
TIMEOUT = 300.0
AGENT_DAILY_CEILING = int(os.environ.get("AGENT_DAILY_CEILING", "20"))


def load_previous():
    answered = {}
    for path in sorted(glob.glob(os.path.join(OUTPUT_DIR, "run_*.json"))):
        for record in json.load(open(path)):
            if not record["error"]:
                answered[record["question"]] = record
    return answered


def ask(client, question):
    started = time.perf_counter()
    response = client.post(f"{ENGINE_URL}/ask", json={"question": question})
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    return response.json(), elapsed


def collect():
    print(
        f"agent quota: {used_today()}/{AGENT_DAILY_CEILING} calls used today, "
        f"{remaining(AGENT_DAILY_CEILING)} remaining\n"
    )
    answered = load_previous()
    print(f"resuming: {len(answered)} question(s) already answered\n")

    records = []
    with httpx.Client(timeout=TIMEOUT) as client:
        for index, item in enumerate(GOLD_SET, start=1):
            question = item["question"]
            if question in answered:
                # answer/contexts/tool_calls are cached — no re-spend needed —
                # but answer_key is a display field, not a scored one, so it
                # always tracks GOLD_SET rather than whatever an older run
                # captured before a gold-key fix.
                records.append({**answered[question], "answer_key": item["answer_key"], "latency_s": None})
                print(f"[{index:2}/{len(GOLD_SET)}]   reused  {question[:58]}")
                continue

            record = {
                "question": question,
                "answer_key": item["answer_key"],
                "answer": "",
                "contexts": [],
                "tool_calls": [],
                "latency_s": None,
                "error": None,
            }
            try:
                payload, elapsed = ask(client, question)
                # §02's p95 is defined as engine timing, not a client-side
                # stopwatch — payload["latency_s"] is the FastAPI handler's
                # own measurement. elapsed (client wall time) is kept only as
                # a fallback for engines predating this instrumentation.
                engine_latency = payload.get("latency_s")
                record.update(
                    answer=payload["answer"],
                    contexts=payload["contexts"],
                    tool_calls=payload["tool_calls"],
                    latency_s=engine_latency if engine_latency is not None else round(elapsed, 2),
                )
                print(f"[{index:2}/{len(GOLD_SET)}] {record['latency_s']:6.2f}s (engine)"
                      f"  {question[:50]}")
            except Exception as exc:
                record["error"] = f"{type(exc).__name__}: {exc}"
                print(f"[{index:2}/{len(GOLD_SET)}]  FAILED  {record['error'][:70]}")
            records.append(record)
            time.sleep(PACE_SECONDS)
    return records


def main():
    records = collect()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = os.path.join(OUTPUT_DIR, f"run_{stamp}.json")
    with open(path, "w") as handle:
        json.dump(records, handle, indent=2)

    failed = sum(1 for r in records if r["error"])
    print(f"\nwrote {path}  ({len(records) - failed} usable, {failed} failed)")


if __name__ == "__main__":
    main()