import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev

from qdrant_client.models import Fusion, FusionQuery, Prefetch

from app.eval.gold_set import GOLD_SET
from app.retrieve import (
    COLLECTION,
    DENSE_NAME,
    PREFETCH,
    RERANK_POOL,
    SPARSE_NAME,
    TOP_K,
    _client,
    _rerank_model,
    embed_question_dense,
    embed_question_sparse,
)

RUN_ARTIFACT = Path(os.environ.get("EVAL_DIR", "/code/data/eval")) / "run_20260831T101752Z.json"
LATENCY_ARTIFACT = Path(os.environ.get("EVAL_DIR", "/code/data/eval")) / "latency_samples.json"
OUTPUT_DIR = Path(os.environ.get("EVAL_DIR", "/code/data/eval"))

STAGES = ["embed_dense", "embed_sparse", "qdrant_hybrid_query", "unpack_candidates", "rerank"]

ANSWERABLE = [item for item in GOLD_SET if item["answer_key"] != "UNANSWERABLE"]


class HealthCheckFailed(RuntimeError):
    pass


def health_gate() -> None:
    """Same discipline as T2.1/T2.1c: /health proves the port is open, not
    that the models finished loading. A real query with a known answer is
    the only genuine gate."""
    from app.retrieve import retrieve

    question = "What was Apple's net income for fiscal 2025?"
    expected = "112,010"
    chunks = retrieve(question, top_k=TOP_K)
    if not any(expected in c["text"] for c in chunks):
        raise HealthCheckFailed(
            f"health gate failed: {expected!r} not in top-{TOP_K} for {question!r}"
        )


def timed_search(question: str) -> dict:
    """Reimplements retrieve.search() stage by stage, purely for timing —
    retrieve.py itself is untouched. Each stage is timed with perf_counter;
    the outer wall clock is timed independently so stage-sum-vs-total is a
    built-in consistency check, not an assumption."""
    t_outer_start = time.perf_counter()
    timings = {}

    t0 = time.perf_counter()
    dense = embed_question_dense(question)
    timings["embed_dense"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    sparse = embed_question_sparse(question)
    timings["embed_sparse"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    hits = _client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            Prefetch(query=dense, using=DENSE_NAME, limit=PREFETCH),
            Prefetch(query=sparse, using=SPARSE_NAME, limit=PREFETCH),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=RERANK_POOL,
    ).points
    timings["qdrant_hybrid_query"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    candidates = [
        {"text": hit.payload["text"], "page": hit.payload["page"]} for hit in hits
    ]
    timings["unpack_candidates"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    pairs = [(question, c["text"]) for c in candidates]
    scores = _rerank_model.predict(pairs)
    sorted(zip(candidates, scores), key=lambda pair: pair[1], reverse=True)
    timings["rerank"] = time.perf_counter() - t0

    total_outer = time.perf_counter() - t_outer_start
    return {"stage_timings_s": timings, "total_outer_s": total_outer,
            "stage_sum_s": sum(timings.values()), "pool_size": len(hits)}


def warm_queries_from_run() -> list[dict]:
    """Same query source as T2.1c and same reasoning: the agent's persisted
    tool-call queries, not the gold question, and not simplified for the
    multi-call row — every individual retrieve() call the pipeline actually
    makes gets its own measurement."""
    run = json.loads(RUN_ARTIFACT.read_text())
    run_by_q = {r["question"]: r for r in run}
    calls = []
    for item in ANSWERABLE:
        question = item["question"]
        tool_calls = run_by_q[question]["tool_calls"]
        for i, call in enumerate(tool_calls):
            calls.append({
                "question": question,
                "call_index": i,
                "n_calls_this_question": len(tool_calls),
                "query": call["query"],
            })
    return calls


def measure_cold() -> dict:
    """One-time cost paid once per process (container start), not per call.
    Measured in a fresh subprocess so it doesn't touch this process's
    already-warm state: import time (HF cache is warm on disk already —
    this is model deserialization into memory, not download) plus the
    first retrieval call served immediately after, since first-inference
    JIT/graph-setup cost is a real cold cost distinct from import alone."""
    script = (
        "import time, sys; "
        "t0=time.perf_counter(); "
        "import app.retrieve as r; "
        "import_s=time.perf_counter()-t0; "
        "t0=time.perf_counter(); "
        "chunks=r.retrieve('What was Apple\\'s net income for fiscal 2025?', top_k=5); "
        "first_call_s=time.perf_counter()-t0; "
        "ok=any('112,010' in c['text'] for c in chunks); "
        "import json; print(json.dumps({'import_s': import_s, 'first_call_s': first_call_s, 'health_ok': ok}))"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd="/code",
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cold measurement subprocess failed: {result.stderr[-2000:]}")
    lines = [l for l in result.stdout.strip().splitlines() if l.startswith("{")]
    return json.loads(lines[-1])


def reconcile_end_to_end(warm_calls: list[dict]) -> dict:
    """Connects retrieval's measured per-call cost to the observed 43-196s
    /ask range: for each latency sample, look up how many retrieval calls
    that question actually made (from the persisted run's tool_calls),
    multiply by mean warm per-call retrieval time, and compare against the
    engine-measured total."""
    if not LATENCY_ARTIFACT.exists():
        return {"error": "latency_samples.json not found — cannot reconcile"}
    samples = json.loads(LATENCY_ARTIFACT.read_text())["samples"]
    run = json.loads(RUN_ARTIFACT.read_text())
    run_by_q = {r["question"]: r for r in run}

    per_call_totals = [c["total_outer_s"] for c in warm_calls]
    mean_call_s = mean(per_call_totals)

    rows = []
    for s in samples:
        q = s["question"]
        n_retrieval_calls = len(run_by_q[q]["tool_calls"]) if q in run_by_q else None
        est_retrieval_s = (n_retrieval_calls * mean_call_s) if n_retrieval_calls is not None else None
        pct = (est_retrieval_s / s["latency_s"] * 100) if est_retrieval_s is not None else None
        rows.append({
            "question": q,
            "observed_latency_s": s["latency_s"],
            "calls_this_ask_gemini": s["calls_this_ask"],
            "n_retrieval_calls": n_retrieval_calls,
            "estimated_retrieval_s": est_retrieval_s,
            "estimated_retrieval_pct_of_total": pct,
        })
    return {
        "mean_warm_retrieval_call_s": mean_call_s,
        "rows": rows,
    }


def self_test(warm_calls: list[dict]) -> dict:
    """Proves the timing check can fail: stage_sum_s must track total_outer_s
    closely (only Python glue between perf_counter() calls separates them).
    A bogus/broken instrumentation — a stage silently skipped, or double
    counted — would show stage_sum_s diverging sharply from total_outer_s.
    Asserted per call, not just eyeballed."""
    max_gap_s = 0.0
    max_gap_pct = 0.0
    worst = None
    for c in warm_calls:
        gap = abs(c["total_outer_s"] - c["stage_sum_s"])
        gap_pct = gap / c["total_outer_s"] * 100 if c["total_outer_s"] else 0
        if gap_pct > max_gap_pct:
            max_gap_pct = gap_pct
            max_gap_s = gap
            worst = c["query"]
    passed = max_gap_pct < 5.0  # glue code between 5 perf_counter() pairs should be near-zero
    return {
        "description": "stage_sum_s must be within 5% of independently-measured total_outer_s per call",
        "max_gap_s": max_gap_s,
        "max_gap_pct": max_gap_pct,
        "worst_query": worst,
        "passed": passed,
    }


def main():
    health_gate()
    print("health gate: PASS (real retrieval, known answer confirmed)\n")

    print("--- cold: fresh subprocess, HF cache warm on disk, models not yet in memory ---")
    cold = measure_cold()
    print(f"import (model load into memory): {cold['import_s']:.3f}s")
    print(f"first retrieval call after import: {cold['first_call_s']:.3f}s  "
          f"(health check inside subprocess: {'PASS' if cold['health_ok'] else 'FAIL'})\n")

    print("--- warm: models resident, agent's actual persisted queries, one call per query ---")
    query_specs = warm_queries_from_run()
    warm_calls = []
    for i, spec in enumerate(query_specs, start=1):
        measured = timed_search(spec["query"])
        call = {**spec, **measured}
        warm_calls.append(call)
        st = measured["stage_timings_s"]
        print(f"[{i:2}/{len(query_specs)}] total={measured['total_outer_s']:.3f}s  "
              f"dense={st['embed_dense']:.3f} sparse={st['embed_sparse']:.3f} "
              f"qdrant={st['qdrant_hybrid_query']:.3f} rerank={st['rerank']:.3f}  "
              f"{spec['query'][:40]}")

    stage_stats = {}
    for stage in STAGES:
        vals = [c["stage_timings_s"][stage] for c in warm_calls]
        stage_stats[stage] = {"min": min(vals), "max": max(vals), "mean": mean(vals), "stdev": pstdev(vals)}
    total_vals = [c["total_outer_s"] for c in warm_calls]
    total_stats = {"min": min(total_vals), "max": max(total_vals), "mean": mean(total_vals), "stdev": pstdev(total_vals)}

    print("\n--- warm stage stats across", len(warm_calls), "calls ---")
    for stage, s in stage_stats.items():
        print(f"  {stage:<20} min={s['min']:.3f} mean={s['mean']:.3f} max={s['max']:.3f} stdev={s['stdev']:.3f}")
    print(f"  {'TOTAL':<20} min={total_stats['min']:.3f} mean={total_stats['mean']:.3f} "
          f"max={total_stats['max']:.3f} stdev={total_stats['stdev']:.3f}")

    dominant_stage = max(stage_stats, key=lambda s: stage_stats[s]["mean"])
    print(f"\ndominant warm stage: {dominant_stage} ({stage_stats[dominant_stage]['mean']:.3f}s mean, "
          f"{stage_stats[dominant_stage]['mean'] / total_stats['mean'] * 100:.0f}% of per-call total)")

    print("\n--- self-test: stage_sum_s must track total_outer_s ---")
    st_result = self_test(warm_calls)
    print(f"self-test: {'PASS' if st_result['passed'] else 'FAIL'}  "
          f"max gap {st_result['max_gap_s']*1000:.1f}ms ({st_result['max_gap_pct']:.1f}%) on {st_result['worst_query'][:40]!r}")
    if not st_result["passed"]:
        raise SystemExit("self-test failed — timing instrumentation is inconsistent, refusing to persist")

    print("\n--- end-to-end reconciliation against latency_samples.json ---")
    reconciliation = reconcile_end_to_end(warm_calls)
    for r in reconciliation["rows"]:
        print(f"  observed={r['observed_latency_s']:7.2f}s  gemini_calls={r['calls_this_ask_gemini']}  "
              f"retrieval_calls={r['n_retrieval_calls']}  est_retrieval={r['estimated_retrieval_s']:.3f}s "
              f"({r['estimated_retrieval_pct_of_total']:.2f}% of total)  {r['question'][:40]}")

    artifact = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "stages": STAGES,
        "cold": cold,
        "warm": {
            "calls": warm_calls,
            "stage_stats": stage_stats,
            "total_stats": total_stats,
            "dominant_stage": dominant_stage,
        },
        "self_test": st_result,
        "end_to_end_reconciliation": reconciliation,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"retrieval_timing_{stamp}.json"
    path.write_text(json.dumps(artifact, indent=2))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
