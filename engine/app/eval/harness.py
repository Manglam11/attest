import glob
import json
import os
import time
from datetime import datetime, timezone

import httpx

from app.eval.gold_set import GOLD_SET

ENGINE_URL = os.environ.get("ENGINE_URL", "http://engine:8000")
OUTPUT_DIR = "/code/data/eval"
PACE_SECONDS = float(os.environ.get("PACE_SECONDS", "30"))
TIMEOUT = 300.0


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
    answered = load_previous()
    print(f"resuming: {len(answered)} question(s) already answered\n")

    records = []
    with httpx.Client(timeout=TIMEOUT) as client:
        for index, item in enumerate(GOLD_SET, start=1):
            question = item["question"]
            if question in answered:
                records.append(answered[question])
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
                record.update(
                    answer=payload["answer"],
                    contexts=payload["contexts"],
                    tool_calls=payload["tool_calls"],
                    latency_s=round(elapsed, 2),
                )
                print(f"[{index:2}/{len(GOLD_SET)}] {elapsed:6.1f}s  {question[:58]}")
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