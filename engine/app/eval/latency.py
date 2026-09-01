import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.eval.gold_set import GOLD_SET
from app.quota import remaining, used_today

ENGINE_URL = os.environ.get("ENGINE_URL", "http://engine:8000")
OUTPUT_PATH = Path(os.environ.get("EVAL_DIR", "/code/data/eval")) / "latency_samples.json"
TIMEOUT = 300.0
PACE_SECONDS = float(os.environ.get("PACE_SECONDS", "30"))
AGENT_DAILY_CEILING = int(os.environ.get("AGENT_DAILY_CEILING", "20"))
CALLS_PER_ASK = 2.08

ANSWERABLE = [item["question"] for item in GOLD_SET if item["answer_key"] != "UNANSWERABLE"]


class EngineUnhealthy(RuntimeError):
    pass


class QuotaExceeded(RuntimeError):
    pass


def check_health(client: httpx.Client) -> None:
    try:
        response = client.get(f"{ENGINE_URL}/health")
    except httpx.HTTPError as exc:
        raise EngineUnhealthy(f"{type(exc).__name__}: {exc}") from exc
    if response.status_code != 200 or response.json().get("status") != "alive":
        raise EngineUnhealthy(f"unexpected /health response: {response.status_code} {response.text[:120]}")


def check_quota(n: int) -> None:
    needed = n * CALLS_PER_ASK
    have = remaining(AGENT_DAILY_CEILING)
    if needed > have:
        raise QuotaExceeded(f"{n} asks needs ~{needed:.1f} calls, only {have} remain today")


def load_samples() -> list:
    if OUTPUT_PATH.exists():
        return json.loads(OUTPUT_PATH.read_text())["samples"]
    return []


def save_samples(samples: list) -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps({"samples": samples}, indent=2))


def next_questions(samples: list, n: int) -> list:
    counts = {q: 0 for q in ANSWERABLE}
    for s in samples:
        if s["question"] in counts:
            counts[s["question"]] += 1
    ordered = sorted(ANSWERABLE, key=lambda q: (counts[q], ANSWERABLE.index(q)))
    return ordered[:n]


def draw(client: httpx.Client, question: str) -> dict:
    started = time.perf_counter()
    response = client.post(f"{ENGINE_URL}/ask", json={"question": question})
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    payload = response.json()
    engine_latency = payload.get("latency_s")
    return {
        "question": question,
        "latency_s": engine_latency if engine_latency is not None else round(elapsed, 3),
        "source": "engine" if engine_latency is not None else "client",
        "day": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sampled_at": datetime.now(timezone.utc).isoformat(),
        "quota_used_after": used_today(),
    }


def run_with_client(client: httpx.Client, n: int) -> list:
    check_health(client)
    check_quota(n)
    samples = load_samples()
    targets = next_questions(samples, n)
    for index, question in enumerate(targets, start=1):
        try:
            sample = draw(client, question)
        except Exception:
            save_samples(samples)
            raise
        samples.append(sample)
        print(f"[{index:2}/{len(targets)}] {sample['latency_s']:6.2f}s (day {sample['day']})  {question[:50]}")
        save_samples(samples)
        if index < len(targets):
            time.sleep(PACE_SECONDS)
    return samples


def run(n: int) -> list:
    with httpx.Client(timeout=TIMEOUT) as client:
        return run_with_client(client, n)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=None)
    args = parser.parse_args()
    n = args.n
    if n is None:
        n = min(len(ANSWERABLE), int(remaining(AGENT_DAILY_CEILING) // CALLS_PER_ASK))
    print(f"agent quota: {used_today()}/{AGENT_DAILY_CEILING} calls used today, "
          f"{remaining(AGENT_DAILY_CEILING)} remaining — sampling {n} fresh ask(s)\n")
    samples = run(n)
    print(f"\n{len(samples)} total latency sample(s) accumulated in {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
