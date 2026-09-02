import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

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

OUTPUT_DIR = Path(os.environ.get("EVAL_DIR", "/code/data/eval"))

NUMBER_TOKEN = re.compile(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b")

ANSWERABLE = [item for item in GOLD_SET if item["answer_key"] != "UNANSWERABLE"]

# Disambiguation for answer_keys with more than one exact-token match across
# the full corpus — a keyword that must co-occur in the same chunk to count
# as the answer-bearing one. Filled in only after an empirical scan showed
# which rows actually collide; most collisions turned out to be the filing
# genuinely restating the same figure across MD&A/statements/notes (inspected
# by hand, kept as-is, all count as correct). "100" was the one real
# coincidence — basis points, commercial paper, share-repurchase rows also
# tokenize to "100" — so it alone gets narrowed to the stock-performance
# table and its figure caption, both of which mention the benchmark "Index".
DISAMBIGUATION_KEYWORDS: dict[str, str] = {
    "What base amount was assumed invested in the stock performance comparison graph as of September 2020?": "Index",
}

# The one gold row whose answer_key is an arithmetic result (net sales minus
# R&D) rather than a value written anywhere in the filing — no chunk can
# ever satisfy the exact-token check. Reported separately from genuine
# retrieval misses; recorded here so the row's context is checkable, not
# asserted in prose.
DERIVED_ANSWER_OPERANDS: dict[str, list[str]] = {
    "How much larger was Apple's total net sales than its research and development spend in fiscal 2025?": [
        "416,161",
        "34,550",
    ],
}


class HealthCheckFailed(RuntimeError):
    pass


def health_gate() -> None:
    """/health returns 'alive' as soon as the port opens, before the dense
    and reranker models finish loading — it cannot prove retrieval works.
    This runs a real query with a known answer and checks the value actually
    comes back, which fails if any stage (embed, qdrant, rerank) is broken."""
    from app.retrieve import retrieve

    question = "What was Apple's net income for fiscal 2025?"
    expected = "112,010"
    chunks = retrieve(question, top_k=TOP_K)
    if not any(expected in c["text"] for c in chunks):
        raise HealthCheckFailed(
            f"health gate failed: {expected!r} not in top-{TOP_K} for {question!r}"
        )


def dump_corpus() -> list[dict]:
    points = []
    offset = None
    while True:
        batch, offset = _client.scroll(
            collection_name=COLLECTION,
            limit=200,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points.extend(
            {"id": p.id, "page": p.payload["page"], "text": p.payload["text"]}
            for p in batch
        )
        if offset is None:
            break
    return points


def corpus_point_count() -> int:
    return _client.count(collection_name=COLLECTION, exact=True).count


def find_corpus_matches(answer_key: str, corpus: list[dict]) -> list[dict]:
    matches = []
    for chunk in corpus:
        tokens = NUMBER_TOKEN.findall(chunk["text"])
        if answer_key in tokens:
            matches.append({"id": chunk["id"], "page": chunk["page"]})
    return matches


def resolve_correct_chunks(question: str, answer_key: str, corpus: list[dict]) -> dict:
    corpus_by_id = {c["id"]: c for c in corpus}
    matches = find_corpus_matches(answer_key, corpus)
    if len(matches) == 0:
        return {
            "corpus_matches": matches,
            "ambiguous": True,
            "disambiguation": "no-match",
            "correct_chunk_ids": [],
        }
    if len(matches) == 1:
        return {
            "corpus_matches": matches,
            "ambiguous": False,
            "disambiguation": "unique",
            "correct_chunk_ids": [matches[0]["id"]],
        }
    keyword = DISAMBIGUATION_KEYWORDS.get(question)
    if keyword:
        narrowed = [
            m for m in matches if keyword.lower() in corpus_by_id[m["id"]]["text"].lower()
        ]
        if 0 < len(narrowed) < len(matches):
            return {
                "corpus_matches": matches,
                "ambiguous": False,
                "disambiguation": f"keyword:{keyword!r} narrowed {len(matches)}->{len(narrowed)}",
                "correct_chunk_ids": [m["id"] for m in narrowed],
            }
    return {
        "corpus_matches": matches,
        "ambiguous": True,
        "disambiguation": "unresolved-multiple",
        "correct_chunk_ids": [m["id"] for m in matches],
    }


def fusion_pool(question: str) -> list[dict]:
    dense = embed_question_dense(question)
    sparse = embed_question_sparse(question)
    hits = _client.query_points(
        collection_name=COLLECTION,
        prefetch=[
            Prefetch(query=dense, using=DENSE_NAME, limit=PREFETCH),
            Prefetch(query=sparse, using=SPARSE_NAME, limit=PREFETCH),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=RERANK_POOL,
    ).points
    return [{"id": hit.id, "page": hit.payload["page"], "text": hit.payload["text"]} for hit in hits]


def rerank_all(question: str, pool: list[dict]) -> list[dict]:
    pairs = [(question, c["text"]) for c in pool]
    scores = _rerank_model.predict(pairs)
    ranked = sorted(zip(pool, scores), key=lambda pair: pair[1], reverse=True)
    return [{**c, "rerank_score": float(s)} for c, s in ranked]


def rank_of(chunk_ids: set, ordered: list[dict]) -> int | None:
    for i, c in enumerate(ordered, start=1):
        if c["id"] in chunk_ids:
            return i
    return None


def derived_value_note(question: str, corpus: list[dict], pool: list[dict]) -> dict | None:
    operands = DERIVED_ANSWER_OPERANDS.get(question)
    if not operands:
        return None
    operand_matches = [find_corpus_matches(op, corpus) for op in operands]
    ids_per_operand = [set(m["id"] for m in matches) for matches in operand_matches]
    chunks_with_all_operands = set.intersection(*ids_per_operand) if ids_per_operand else set()
    pool_ids = [c["id"] for c in pool]
    in_pool = sorted(i for i in chunks_with_all_operands if i in pool_ids)
    return {
        "operands": operands,
        "chunks_containing_all_operands": sorted(chunks_with_all_operands),
        "operand_chunks_in_fusion_pool": in_pool,
        "operand_chunk_fusion_rank": (pool_ids.index(in_pool[0]) + 1) if in_pool else None,
    }


def measure_row(item: dict, corpus: list[dict]) -> dict:
    question = item["question"]
    answer_key = item["answer_key"]
    resolution = resolve_correct_chunks(question, answer_key, corpus)
    correct_ids = set(resolution["correct_chunk_ids"])

    pool = fusion_pool(question)
    fusion_ids_ordered = [c["id"] for c in pool]
    fusion_rank = rank_of(correct_ids, pool)

    reranked = rerank_all(question, pool)
    rerank_rank = rank_of(correct_ids, reranked)
    top1 = reranked[0]
    correct_entry = next((c for c in reranked if c["id"] in correct_ids), None)

    if fusion_rank is None:
        stage = "never_entered_pool"
    elif rerank_rank is not None and rerank_rank <= TOP_K:
        stage = "clean"
    else:
        stage = "reranked_below_cut"

    return {
        "question": question,
        "answer_key": answer_key,
        "corpus_matches": resolution["corpus_matches"],
        "ambiguous": resolution["ambiguous"],
        "disambiguation": resolution["disambiguation"],
        "correct_chunk_ids": sorted(correct_ids),
        "fusion_pool_size": len(pool),
        "fusion_rank": fusion_rank,
        "rerank_pool_size": len(reranked),
        "rerank_rank": rerank_rank,
        "rerank_score_correct": correct_entry["rerank_score"] if correct_entry else None,
        "rerank_score_top1": top1["rerank_score"],
        "top1_chunk_id": top1["id"],
        "margin": (top1["rerank_score"] - correct_entry["rerank_score"])
        if correct_entry and correct_entry["id"] != top1["id"]
        else (0.0 if correct_entry else None),
        "stage_responsible": stage,
        "top_k_cut": TOP_K,
        "derived_value_note": derived_value_note(question, corpus, pool),
    }


def run_self_test(corpus: list[dict]) -> dict:
    """Proves the corpus-match check can fail: an answer_key that is not in
    the corpus at all must come back as zero matches, not a false hit."""
    bogus_key = "999,999,999"
    question = ANSWERABLE[0]["question"]
    resolution = resolve_correct_chunks(question, bogus_key, corpus)
    passed = resolution["disambiguation"] == "no-match" and resolution["correct_chunk_ids"] == []
    return {
        "description": "a fabricated answer_key absent from the corpus must resolve to zero matches",
        "question_used": question,
        "bogus_key_used": bogus_key,
        "result": resolution,
        "passed": passed,
    }


def summarize(rows: list[dict]) -> dict:
    clean = [r for r in rows if r["stage_responsible"] == "clean"]
    near_miss = [r for r in rows if r["stage_responsible"] == "reranked_below_cut"]
    genuine_miss = [r for r in rows if r["stage_responsible"] == "never_entered_pool"]
    derived = [r for r in rows if r["derived_value_note"] is not None]
    genuine_miss_not_derived = [r for r in genuine_miss if r["derived_value_note"] is None]
    margins = [r["margin"] for r in near_miss if r["margin"] is not None]
    return {
        "n_answerable": len(rows),
        "clean": len(clean),
        "near_miss": len(near_miss),
        "genuine_miss": len(genuine_miss),
        "genuine_miss_excluding_derived_value_rows": len(genuine_miss_not_derived),
        "derived_value_rows": len(derived),
        "ambiguous_rows": sum(1 for r in rows if r["ambiguous"]),
        "near_miss_margins": margins,
        "near_miss_margin_min": min(margins) if margins else None,
        "near_miss_margin_max": max(margins) if margins else None,
    }


def main():
    health_gate()
    print("health gate: PASS (real retrieval, known answer confirmed)\n")

    count = corpus_point_count()
    print(f"corpus point count (live, exact): {count}\n")

    corpus = dump_corpus()
    assert len(corpus) == count, f"scroll returned {len(corpus)} points, count() says {count}"

    self_test = run_self_test(corpus)
    print(f"self-test (bogus key must produce zero matches): "
          f"{'PASS' if self_test['passed'] else 'FAIL'}\n")

    rows = []
    for index, item in enumerate(ANSWERABLE, start=1):
        row = measure_row(item, corpus)
        rows.append(row)
        flag = " AMBIGUOUS" if row["ambiguous"] else ""
        print(f"[{index:2}/{len(ANSWERABLE)}] fusion={row['fusion_rank']!s:>4} "
              f"rerank={row['rerank_rank']!s:>4} {row['stage_responsible']:<18} "
              f"{row['question'][:45]}{flag}")

    summary = summarize(rows)
    print(f"\n--- retrieval baseline, prefetch={PREFETCH} rerank_pool={RERANK_POOL} top_k={TOP_K} ---")
    print(f"clean: {summary['clean']}/{summary['n_answerable']}  "
          f"near-miss: {summary['near_miss']}  genuine-miss: {summary['genuine_miss']} "
          f"({summary['genuine_miss_excluding_derived_value_rows']} excluding derived-value rows)  "
          f"ambiguous: {summary['ambiguous_rows']}")

    artifact = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "corpus_point_count": count,
        "config": {
            "embed_model": "BAAI/bge-small-en-v1.5",
            "sparse_model": "Qdrant/bm25",
            "rerank_model": "BAAI/bge-reranker-base",
            "prefetch": PREFETCH,
            "rerank_pool": RERANK_POOL,
            "top_k": TOP_K,
        },
        "chunk_id_method": (
            "exact grouped-number token match (regex \\b\\d{1,3}(?:,\\d{3})*(?:\\.\\d+)?\\b) "
            "against the full live corpus; ties broken by a required co-occurring keyword, "
            "else left ambiguous and every matching chunk id counts as correct"
        ),
        "self_test": self_test,
        "rows": rows,
        "summary": summary,
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / f"retrieval_baseline_{stamp}.json"
    path.write_text(json.dumps(artifact, indent=2))
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
