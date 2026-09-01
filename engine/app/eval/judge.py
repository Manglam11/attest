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


def summarise(rows: list) -> dict:
    summary = {}
    for metric, target in TARGETS.items():
        vals = [r["scores"][metric] for r in rows if r.get("scores")]
        summary[metric] = {
            "mean": round(sum(vals) / len(vals), 4) if vals else None,
            "target": target,
            "n": len(vals),
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
    out_path = EVAL_DIR / f"judged_{run_path.stem.split('_', 1)[1]}.json"
    print(f"judging {run_path.name}  ({len(rows)} rows, model={JUDGE_MODEL})")
    print(f"writing {out_path.name} after every row\n")

    judged = []
    spent = 0
    done = prior_scores()
    if done:
        print(f"resuming — {len(done)} rows already scored\n")

    for i, row in enumerate(rows):
        if limit is not None and spent >= limit:
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
            write_judged(out_path, run_path.name, judged)
            continue

        if row["question"] in done:
            record["scores"] = done[row["question"]]
            s = record["scores"]
            print(f"[{i}] f={s['faithfulness']:.2f} ar={s['answer_relevancy']:.2f} "
                  f"cp={s['context_precision']:.2f}  (cached)")
            judged.append(record)
            write_judged(out_path, run_path.name, judged)
            continue

        t0 = time.time()
        try:
            record["scores"] = await judge_row(row, metrics)
            spent += 1
            s = record["scores"]
            print(f"[{i}] f={s['faithfulness']:.2f} ar={s['answer_relevancy']:.2f} "
                  f"cp={s['context_precision']:.2f}  ({time.time() - t0:.0f}s) "
                  f"| {row['question'][:50]}")
        except Exception as e:
            spent += 1
            record["error"] = f"{type(e).__name__}: {e}"
            print(f"[{i}] ERROR {record['error']}")
            judged.append(record)
            write_judged(out_path, run_path.name, judged)
            if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
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
                write_judged(out_path, run_path.name, judged)
                print("\n!! rate limit — stopping. Scored rows are on disk; re-run to resume.")
                break
            continue

        judged.append(record)
        write_judged(out_path, run_path.name, judged)

    summary = summarise(judged)
    print("\n— summary —")
    for metric, target in TARGETS.items():
        s = summary[metric]
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