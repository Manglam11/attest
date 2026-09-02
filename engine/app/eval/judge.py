import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import instructor
from google import genai
from ragas.embeddings import HuggingFaceEmbeddings
from ragas.llms.base import InstructorLLM
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecisionWithoutReference,
    Faithfulness,
)

from app.refusal import is_refusal

EVAL_DIR = Path(os.getenv("EVAL_DIR", "/code/data/eval"))
JUDGE_MODEL = "gemini-3.5-flash-lite"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
PACE_S = float(os.getenv("JUDGE_PACE_S", "45"))
TARGETS = {
    "faithfulness": 0.90,
    "answer_relevancy": 0.85,
    "context_precision": 0.85,
}


def build_llm(client):
    return InstructorLLM(
        client=instructor.from_genai(client, use_async=True),
        model=JUDGE_MODEL,
        provider="google",
    )


def newest_run() -> Path:
    runs = sorted(EVAL_DIR.glob("run_*.json"))
    if not runs:
        raise SystemExit(f"no run_*.json in {EVAL_DIR}")
    return runs[-1]


def score_value(result) -> float:
    return float(getattr(result, "value", result))


def prior_records() -> dict:
    judged = sorted(EVAL_DIR.glob("judged_*.json"))
    if not judged:
        return {}
    prior = json.load(open(judged[-1]))
    return {r["question"]: r for r in prior.get("rows", [])}


def summarise(rows: list) -> dict:
    summary = {}
    for metric, target in TARGETS.items():
        vals = [r["scores"][metric] for r in rows if r.get("scores")]
        summary[metric] = {
            "mean": round(sum(vals) / len(vals), 4) if vals else None,
            "target": target,
            "n": len(vals),
        }

    # answer_relevancy is the only metric whose value depends on which embedder
    # scored it. A mean across rows scored by different embedders — or any row
    # scored without its embedder recorded at all — is not a single ruler, so
    # refuse it rather than print a number that looks like one.
    ar_rows = [r for r in rows if r.get("scores")]
    embed_models = {r.get("embed_model") for r in ar_rows}
    if ar_rows and (len(embed_models) > 1 or None in embed_models):
        counts = {}
        for r in ar_rows:
            m = r.get("embed_model")
            counts[m] = counts.get(m, 0) + 1
        summary["answer_relevancy"] = {
            "mean": None,
            "target": TARGETS["answer_relevancy"],
            "n": len(ar_rows),
            "unclaimable": True,
            "reason": f"mixed/unrecorded embed_model across scored rows: {counts}",
        }

    unanswerable = [r for r in rows if r["answer_key"] == "UNANSWERABLE"]
    refused = [r for r in unanswerable if r["refused"]]
    summary["refusal_rate"] = {
        "value": round(len(refused) / len(unanswerable), 4) if unanswerable else None,
        "n": len(unanswerable),
    }
    return summary


def write_judged(out_path: Path, run_name: str, rows: list) -> None:
    out_path.write_text(
        json.dumps(
            {
                "run": run_name,
                "judge_model": JUDGE_MODEL,
                "embed_model": EMBED_MODEL,
                "judged_at": datetime.now(timezone.utc).isoformat(),
                "summary": summarise(rows),
                "rows": rows,
            },
            indent=2,
        )
    )


async def judge_row(row, metrics, only=None):
    faith, relevancy, precision = metrics
    q, a, ctx = row["question"], row["answer"] or "", row.get("contexts") or []
    scores = {}

    if only is None or "faithfulness" in only:
        scores["faithfulness"] = score_value(
            await faith.ascore(user_input=q, response=a, retrieved_contexts=ctx)
        )
        await asyncio.sleep(PACE_S)

    if only is None or "answer_relevancy" in only:
        scores["answer_relevancy"] = score_value(
            await relevancy.ascore(user_input=q, response=a)
        )
        await asyncio.sleep(PACE_S)

    if only is None or "context_precision" in only:
        scores["context_precision"] = score_value(
            await precision.ascore(user_input=q, response=a, retrieved_contexts=ctx)
        )
        await asyncio.sleep(PACE_S)

    return scores


async def main(limit):
    key = os.getenv("JUDGE_API_KEY")
    if not key:
        raise SystemExit("JUDGE_API_KEY not set in this container")

    client = genai.Client(api_key=key)
    llm = build_llm(client)
    embeddings = HuggingFaceEmbeddings(model=EMBED_MODEL)
    metrics = (
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        ContextPrecisionWithoutReference(llm=llm),
    )

    run_path = newest_run()
    rows = json.load(open(run_path))
    out_path = EVAL_DIR / f"judged_{run_path.stem.split('_', 1)[1]}.json"
    print(f"judging {run_path.name}  ({len(rows)} rows, model={JUDGE_MODEL})")
    print(f"writing {out_path.name} after every row\n")

    prior = prior_records()
    judged_by_q = dict(prior)
    done = {q: r["scores"] for q, r in prior.items() if r.get("scores")}
    spent = 0
    if prior:
        print(f"resuming — {len(prior)} rows on disk, {len(done)} already scored\n")

    def flush():
        ordered = [judged_by_q[r["question"]] for r in rows if r["question"] in judged_by_q]
        write_judged(out_path, run_path.name, ordered)

    for i, row in enumerate(rows):
        if limit is not None and spent >= limit:
            break

        q = row["question"]
        record = {
            "question": q,
            "answer_key": row["answer_key"],
            "answer": row["answer"],
            "refused": is_refusal(row["answer"]),
            "scores": None,
            "embed_model": None,
            "error": None,
        }

        if row["answer_key"] == "UNANSWERABLE":
            print(f"[{i}] {'REFUSED' if record['refused'] else 'NO REFUSAL':<10} | "
                  f"unanswerable — LLM metrics skipped")
            judged_by_q[q] = record
            flush()
            continue

        prior_row = judged_by_q.get(q)
        prior_scores = prior_row["scores"] if prior_row else None
        prior_embed_model = prior_row.get("embed_model") if prior_row else None

        if prior_scores and prior_embed_model == EMBED_MODEL:
            # faithfulness/context_precision never touch the embedder, so this
            # only skips work when answer_relevancy was scored under the same
            # ruler we're using now
            record["scores"] = prior_scores
            record["embed_model"] = prior_embed_model
            s = record["scores"]
            print(f"[{i}] f={s['faithfulness']:.2f} ar={s['answer_relevancy']:.2f} "
                  f"cp={s['context_precision']:.2f}  (cached, embed_model={EMBED_MODEL})")
            judged_by_q[q] = record
            flush()
            continue

        # a scored row whose answer_relevancy was produced by a different
        # embedder needs only that metric recomputed — faithfulness and
        # context_precision are still valid under the new ruler
        only = {"answer_relevancy"} if prior_scores else None

        t0 = time.time()
        try:
            fresh = await judge_row(row, metrics, only=only)
            spent += 1
            record["scores"] = {**prior_scores, **fresh} if prior_scores else fresh
            record["embed_model"] = EMBED_MODEL
            s = record["scores"]
            tag = f"ar-only, was {prior_embed_model}" if prior_scores else "fresh"
            print(f"[{i}] f={s['faithfulness']:.2f} ar={s['answer_relevancy']:.2f} "
                  f"cp={s['context_precision']:.2f}  ({time.time() - t0:.0f}s) "
                  f"[{tag}] | {row['question'][:50]}")
        except Exception as e:
            spent += 1
            record["error"] = f"{type(e).__name__}: {e}"
            if prior_scores:
                # keep the still-valid faithfulness/context_precision; embed_model
                # stays unset so a later run knows answer_relevancy is stale
                record["scores"] = prior_scores
            print(f"[{i}] ERROR {record['error']}")
            judged_by_q[q] = record
            flush()
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                for r in rows[i + 1:]:
                    rq = r["question"]
                    if rq in judged_by_q:
                        # already known from a prior run — do not clobber with a placeholder
                        continue
                    judged_by_q[rq] = {
                        "question": rq,
                        "answer_key": r["answer_key"],
                        "answer": r["answer"],
                        "refused": is_refusal(r["answer"]),
                        "scores": None,
                        "embed_model": None,
                        "error": "not attempted",
                    }
                flush()
                print("\n!! rate limit — stopping. Scored rows are on disk; re-run to resume.")
                break
            continue

        judged_by_q[q] = record
        flush()

    final_rows = [judged_by_q[r["question"]] for r in rows if r["question"] in judged_by_q]
    summary = summarise(final_rows)
    print("\n— summary —")
    for metric, target in TARGETS.items():
        s = summary[metric]
        if s.get("unclaimable"):
            print(f"{metric:<20} UNCLAIMABLE — {s['reason']}")
            continue
        if s["mean"] is None:
            print(f"{metric:<20} no rows scored")
            continue
        verdict = "PASS" if s["mean"] >= target else "FAIL"
        print(f"{metric:<20} {s['mean']:.3f}  (target {target}, n={s['n']})  {verdict}")
    r = summary["refusal_rate"]
    if r["value"] is not None:
        print(f"{'refusal_rate':<20} {r['value']:.3f}  (n={r['n']})")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    asyncio.run(main(ap.parse_args().limit))
