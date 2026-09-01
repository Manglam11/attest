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
MEASURED_WORST_CALLS_PER_ASK = 4

ANSWERABLE = [item["question"] for item in GOLD_SET if item["answer_key"] != "UNANSWERABLE"]

QUESTION_CATEGORIES = [
    [ANSWERABLE[i] for i in (0, 1, 2, 3, 4, 5, 7)],
    [ANSWERABLE[i] for i in (6, 8)],
    [ANSWERABLE[i] for i in (9, 10)],
    [ANSWERABLE[i] for i in (11,)],
]


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


def worst_case_calls(samples: list) -> float:
    observed = [s["calls_this_ask"] for s in samples if "calls_this_ask" in s]
    return float(max(observed)) if observed else float(MEASURED_WORST_CALLS_PER_ASK)


def check_quota(samples: list) -> None:
    needed = worst_case_calls(samples)
    have = remaining(AGENT_DAILY_CEILING)
    if needed > have:
        raise QuotaExceeded(f"next ask could cost up to {needed:.0f} calls, only {have} remain today")


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
    queues = [
        sorted(group, key=lambda q: (counts[q], ANSWERABLE.index(q)))
        for group in QUESTION_CATEGORIES
    ]
    picked = []
    while len(picked) < n and any(queues):
        for queue in queues:
            if not queue:
                continue
            picked.append(queue.pop(0))
            if len(picked) == n:
                break
    return picked


def draw(client: httpx.Client, question: str) -> dict:
    quota_before = used_today()
    started = time.perf_counter()
    response = client.post(f"{ENGINE_URL}/ask", json={"question": question})
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    payload = response.json()
    engine_latency = payload.get("latency_s")
    quota_after = used_today()
    return {
        "question": question,
        "latency_s": engine_latency if engine_latency is not None else round(elapsed, 3),
        "source": "engine" if engine_latency is not None else "client",
        "day": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sampled_at": datetime.now(timezone.utc).isoformat(),
        "quota_before": quota_before,
        "quota_after": quota_after,
        "calls_this_ask": quota_after - quota_before,
    }


def run_with_client(client: httpx.Client, n: int) -> list:
    check_health(client)
    samples = load_samples()
    targets = next_questions(samples, n)
    for index, question in enumerate(targets, start=1):
        try:
            check_quota(samples)
        except QuotaExceeded:
            save_samples(samples)
            raise
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
        worst_case = worst_case_calls(load_samples())
        n = min(len(ANSWERABLE), int(remaining(AGENT_DAILY_CEILING) // worst_case))
    print(f"agent quota: {used_today()}/{AGENT_DAILY_CEILING} calls used today, "
          f"{remaining(AGENT_DAILY_CEILING)} remaining — sampling {n} fresh ask(s)\n")
    samples = run(n)
    print(f"\n{len(samples)} total latency sample(s) accumulated in {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
