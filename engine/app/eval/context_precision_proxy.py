import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from app.eval.gold_set import GOLD_SET
from app.retrieve import retrieve

RUN_ARTIFACT = Path(os.environ.get("EVAL_DIR", "/code/data/eval")) / "run_20260831T101752Z.json"
JUDGED_ARTIFACT = Path(os.environ.get("EVAL_DIR", "/code/data/eval")) / "judged_20260831T101752Z.json"
OUTPUT_DIR = Path(os.environ.get("EVAL_DIR", "/code/data/eval"))

NUMBER_TOKEN = re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b")

ANSWERABLE = [item for item in GOLD_SET if item["answer_key"] != "UNANSWERABLE"]
OPERAND_KEYS_BY_QUESTION = {item["question"]: item.get("operand_keys") for item in GOLD_SET}


def average_precision(relevance_flags: list[bool]) -> float:
    """RAGAS's context_precision, as reproduced from the judged artifact: a
    binary relevance verdict per retrieved context, weighted by precision@k
    at each relevant rank, normalized by how many relevant contexts were
    actually retrieved — not by any external ground-truth count. This is
    the formula validated in T2.1c part one against 11 of 12 answerable
    rows, exact to 1e-6."""
    n_relevant = sum(relevance_flags)
    if n_relevant == 0:
        return 0.0
    hits, total = 0, 0.0
    for rank, flag in enumerate(relevance_flags, start=1):
        if flag:
            hits += 1
            total += hits / rank
    return total / n_relevant


def is_relevant(context: str, answer_key: str, operand_keys: list[str] | None = None) -> bool:
    """General rule: retrieval can only be held responsible for surfacing
    the literal values an answer is built from. Most gold rows' answer_key
    IS that value. A derived row (gold_set.py's operand_keys field) instead
    declares the operands its computed answer_key is built from, since the
    result of arithmetic no chunk performs will never appear verbatim in
    the corpus — checking for it would always score 0 regardless of what
    retrieval actually found. When operand_keys is present, a context
    counts as relevant if it carries ANY one of the operands: a chunk
    supplying half of what's needed is still doing retrieval's job, even
    if the other operand comes from elsewhere in the returned set. This
    branch applies to any row that declares operand_keys, not just the
    one that does today."""
    tokens = NUMBER_TOKEN.findall(context)
    if operand_keys:
        return any(op in tokens for op in operand_keys)
    return answer_key in tokens


def validate_against_judged() -> dict:
    """Part one: reproduce every judged answerable row's context_precision
    from the persisted run contexts, under average_precision() above. This
    validates the formula before it's trusted for anything downstream —
    a proxy that can't reproduce the metric of record is not a ruler."""
    run = json.loads(RUN_ARTIFACT.read_text())
    judged = json.loads(JUDGED_ARTIFACT.read_text())
    run_by_q = {r["question"]: r for r in run}

    rows = []
    for jr in judged["rows"]:
        if jr["scores"] is None:
            continue
        question = jr["question"]
        answer_key = jr["answer_key"]
        operand_keys = OPERAND_KEYS_BY_QUESTION.get(question)
        contexts = run_by_q[question]["contexts"]
        flags = [is_relevant(c, answer_key, operand_keys) for c in contexts]
        reproduced = average_precision(flags)
        judged_cp = jr["scores"]["context_precision"]
        rows.append(
            {
                "question": question,
                "judged_context_precision": judged_cp,
                "reproduced_ap": reproduced,
                "match": abs(reproduced - judged_cp) < 1e-6,
            }
        )
    matched = sum(1 for r in rows if r["match"])
    return {
        "n_rows": len(rows),
        "n_matched": matched,
        "n_mismatched": len(rows) - matched,
        "mismatched_questions": [r["question"] for r in rows if not r["match"]],
        "rows": rows,
    }


def self_test() -> dict:
    """Proves the check can fail: an all-false relevance vector (nothing in
    the returned set actually contains the answer) must score exactly 0.0,
    not some smoothed nonzero value — and a single relevant hit at rank 1
    with nothing else must score exactly 1.0. Both are asserted, not just
    printed, so a broken formula stops the run rather than silently
    producing a plausible-looking artifact."""
    zero_case = average_precision([False, False, False])
    perfect_case = average_precision([True, False, False])
    known_case = average_precision([True, False, False, True])  # matches "net income"-style pattern: rel@1, rel@4
    expected_known = (1 / 1 + 2 / 4) / 2

    # A broken derived-value check would look like: falling back to
    # literal answer_key matching even when operand_keys is given (in
    # which case a derived answer never present in the corpus scores every
    # context False and the row goes to 0.0 exactly as before this fix —
    # the bug this fix is for), or matching on ANY number rather than the
    # declared operands (in which case an unrelated figure would count).
    # Both are asserted against directly.
    derived_no_fallback = is_relevant("[page 1] net sales were 381,611 higher", "381,611", ["416,161", "34,550"]) is False
    derived_finds_operand = is_relevant("[page 33] Net sales 416,161 total", "381,611", ["416,161", "34,550"]) is True
    derived_ignores_unrelated_number = is_relevant("[page 9] the fiscal year 2025 covers 366 days", "381,611", ["416,161", "34,550"]) is False
    non_derived_unaffected = is_relevant("[page 33] Net income 112,010", "112,010", None) is True

    passed = (
        zero_case == 0.0
        and perfect_case == 1.0
        and abs(known_case - expected_known) < 1e-9
        and derived_no_fallback
        and derived_finds_operand
        and derived_ignores_unrelated_number
        and non_derived_unaffected
    )
    return {
        "zero_relevant_case": zero_case,
        "expected_zero": 0.0,
        "single_hit_rank1_case": perfect_case,
        "expected_one": 1.0,
        "known_pattern_case": known_case,
        "expected_known_pattern": expected_known,
        "derived_no_fallback_to_literal_answer_key": derived_no_fallback,
        "derived_finds_declared_operand": derived_finds_operand,
        "derived_ignores_unrelated_number": derived_ignores_unrelated_number,
        "non_derived_rows_unaffected": non_derived_unaffected,
        "passed": passed,
    }


def format_chunk(chunk: dict) -> str:
    return f"[page {chunk['page']}] {chunk['text']}"


def agent_queries_for(question: str, run_by_q: dict) -> list[str]:
    tool_calls = run_by_q[question]["tool_calls"]
    return [call["query"] for call in tool_calls]


def collect_agent_contexts(queries: list[str]) -> list[str]:
    """Replicates agent.py's _collect_contexts: each query is retrieved
    independently at the tool's default top_k, formatted exactly as the
    tool renders it, concatenated in call order, deduped by exact text —
    not simplified into a single merged call, because multi-query rows
    (the cash/securities question issued two) don't behave like one."""
    contexts: list[str] = []
    for query in queries:
        for chunk in retrieve(query):
            formatted = format_chunk(chunk)
            if formatted not in contexts:
                contexts.append(formatted)
    return contexts


def score_agent_queries() -> list[dict]:
    run = json.loads(RUN_ARTIFACT.read_text())
    run_by_q = {r["question"]: r for r in run}
    judged = json.loads(JUDGED_ARTIFACT.read_text())
    judged_by_q = {r["question"]: r for r in judged["rows"]}

    rows = []
    for item in ANSWERABLE:
        question = item["question"]
        answer_key = item["answer_key"]
        operand_keys = item.get("operand_keys")
        queries = agent_queries_for(question, run_by_q)
        contexts = collect_agent_contexts(queries)
        flags = [is_relevant(c, answer_key, operand_keys) for c in contexts]
        score = average_precision(flags)
        judged_cp = judged_by_q[question]["scores"]["context_precision"]
        rows.append(
            {
                "question": question,
                "answer_key": answer_key,
                "operand_keys": operand_keys,
                "queries_used": queries,
                "n_queries": len(queries),
                "n_contexts": len(contexts),
                "relevance_flags": flags,
                "proxy_context_precision": score,
                "judged_context_precision_for_reference": judged_cp,
            }
        )
    return rows


def main():
    print("--- part one: validate AP formula against judged artifact ---")
    validation = validate_against_judged()
    print(f"reproduced {validation['n_matched']}/{validation['n_rows']} answerable rows exactly "
          f"(tolerance 1e-6)")
    if validation["mismatched_questions"]:
        print(f"mismatched: {validation['mismatched_questions']}")

    print("\n--- self-test ---")
    st = self_test()
    print(f"self-test: {'PASS' if st['passed'] else 'FAIL'}  {st}")
    if not st["passed"]:
        raise SystemExit("self-test failed — AP formula is broken, refusing to score")

    print("\n--- part two: score returned sets on the agent's actual queries ---")
    rows = score_agent_queries()
    for i, r in enumerate(rows, start=1):
        print(f"[{i:2}/{len(rows)}] proxy={r['proxy_context_precision']:.3f}  "
              f"judged={r['judged_context_precision_for_reference']:.3f}  "
              f"n_q={r['n_queries']} n_ctx={r['n_contexts']}  {r['question'][:45]}")

    proxy_mean = sum(r["proxy_context_precision"] for r in rows) / len(rows)
    judged_mean = sum(r["judged_context_precision_for_reference"] for r in rows) / len(rows)
    print(f"\nproxy mean: {proxy_mean:.4f}   judged mean (of record): {judged_mean:.4f}")

    artifact = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "query_source": (
            "persisted agent tool_calls from run_20260831T101752Z.json, not re-derived live — "
            "re-deriving would invoke the metered agent key. Fidelity cost: these are the "
            "queries Gemini actually issued on 2026-08-31 under the current system prompt "
            "(unchanged since, confirmed via git log), not a fresh sample; the model is not "
            "deterministic, so a live re-ask could phrase differently."
        ),
        "ap_formula": (
            "average precision; relevance = literal answer_key token present in the context "
            "(regex \\b\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?\\b), OR — for a gold row that declares "
            "operand_keys in gold_set.py — any one of those operand tokens present instead, "
            "since a derived answer_key never appears verbatim in the corpus and retrieval "
            "can only be held responsible for surfacing what it was computed from; weight = "
            "precision@k at each relevant rank; normalized by relevant-count within the "
            "returned set, not an external ground truth"
        ),
        "validation": validation,
        "self_test": st,
        "rows": rows,
        "summary": {
            "n_rows": len(rows),
            "proxy_mean": proxy_mean,
            "judged_mean_of_record": judged_mean,
        },
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"context_precision_proxy_{stamp}.json"
    path.write_text(json.dumps(artifact, indent=2))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
