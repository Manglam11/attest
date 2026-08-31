import argparse
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import instructor
from google import genai
from ragas.embeddings import GoogleEmbeddings
from ragas.llms.base import InstructorLLM
from ragas.metrics.collections import (
    AnswerRelevancy,
    ContextPrecisionWithoutReference,
    Faithfulness,
)

EVAL_DIR = Path(os.getenv("EVAL_DIR", "/code/data/eval"))
JUDGE_MODEL = "gemini-3.5-flash-lite"
EMBED_MODEL = "gemini-embedding-001"
REFUSAL = "I cannot answer this from the provided sources"
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

def prior_scores() -> dict:
    judged = sorted(EVAL_DIR.glob("judged_*.json"))
    if not judged:
        return {}
    prior = json.load(open(judged[-1]))
    return {
        r["question"]: r["scores"]
        for r in prior.get("rows", [])
        if r.get("scores")
    }
async def judge_row(row, metrics):
    faith, relevancy, precision = metrics
    q, a, ctx = row["question"], row["answer"] or "", row.get("contexts") or []

    faithfulness = score_value(
        await faith.ascore(user_input=q, response=a, retrieved_contexts=ctx)
    )
    await asyncio.sleep(PACE_S)

    answer_relevancy = score_value(await relevancy.ascore(user_input=q, response=a))
    await asyncio.sleep(PACE_S)

    context_precision = score_value(
        await precision.ascore(user_input=q, response=a, retrieved_contexts=ctx)
    )
    await asyncio.sleep(PACE_S)

    return {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
    }


async def main(limit):
    key = os.getenv("JUDGE_API_KEY")
    if not key:
        raise SystemExit("JUDGE_API_KEY not set in this container")

    client = genai.Client(api_key=key)
    llm = build_llm(client)
    embeddings = GoogleEmbeddings(client=client, model=EMBED_MODEL)

    metrics = (
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        ContextPrecisionWithoutReference(llm=llm),
    )

    run_path = newest_run()
    rows = json.load(open(run_path))
    print(f"judging {run_path.name}  ({len(rows)} rows, model={JUDGE_MODEL})\n")

    judged = []
    done = prior_scores()
    if done:
        print(f"resuming — {len(done)} rows already scored\n")

    for i, row in enumerate(rows):
        if limit is not None and len(judged) >= limit:
            break

        record = {
            "question": row["question"],
            "answer_key": row["answer_key"],
            "answer": row["answer"],
            "refused": REFUSAL.lower() in (row["answer"] or "").lower(),
            "scores": None,
            "error": None,
        }

        if row["answer_key"] == "UNANSWERABLE":
            print(f"[{i}] {'REFUSED' if record['refused'] else 'NO REFUSAL':<10} | "
                  f"unanswerable — LLM metrics skipped")
            judged.append(record)
            continue

        if row["question"] in done:
            record["scores"] = done[row["question"]]
            s = record["scores"]
            print(f"[{i}] f={s['faithfulness']:.2f} ar={s['answer_relevancy']:.2f} "
                  f"cp={s['context_precision']:.2f}  (cached)")
            judged.append(record)
            continue

        t0 = time.time()
        try:
            record["scores"] = await judge_row(row, metrics)
            s = record["scores"]
            print(f"[{i}] f={s['faithfulness']:.2f} ar={s['answer_relevancy']:.2f} "
                  f"cp={s['context_precision']:.2f}  ({time.time() - t0:.0f}s) "
                  f"| {row['question'][:50]}")
        except Exception as e:
            record["error"] = f"{type(e).__name__}: {e}"
            print(f"[{i}] ERROR {record['error'][:120]}")
            judged.append(record)
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                print("\n!! rate limit — stopping. Re-run to resume from here.")
                judged.extend(
                    {
                        "question": r["question"],
                        "answer_key": r["answer_key"],
                        "answer": r["answer"],
                        "refused": REFUSAL.lower() in (r["answer"] or "").lower(),
                        "scores": None,
                        "error": "not attempted",
                    }
                    for r in rows[i + 1:]
                )
                break
            continue

        judged.append(record)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    asyncio.run(main(ap.parse_args().limit))