import json
import os
from pathlib import Path

EVAL_DIR = Path(os.environ.get("EVAL_DIR", "/code/data/eval"))
JUDGED_ARTIFACT_NAME = "judged_20260831T101752Z.json"

TARGETS = {
    "faithfulness": 0.90,
    "answer_relevancy": 0.85,
    "context_precision": 0.85,
}
HALLUCINATION_TARGET = 0.50

TILE_LABELS = {
    "faithfulness": "Faithfulness",
    "answer_relevancy": "Answer relevance",
    "context_precision": "Retrieval precision",
}

# The blueprint's differentiator question: a forward-looking figure no 10-K
# can ground, correctly refused rather than hallucinated. Matched by exact
# text since the gold set carries no tag for it.
RED_ROW_QUESTION = "What does Apple forecast its total net sales will be for fiscal 2026?"


def load_judged_run(eval_dir: Path | None = None):
    """Returns (data, error). data is None if the artifact could not be
    read or parsed; error is a plain-English reason, None on success."""
    path = (eval_dir if eval_dir is not None else EVAL_DIR) / JUDGED_ARTIFACT_NAME
    try:
        raw = path.read_text()
    except OSError as exc:
        return None, f"Evaluation artifact not found at {path} ({exc.__class__.__name__})."
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return None, f"Evaluation artifact at {path} is not valid JSON ({exc})."


def summarise_for_dashboard(data: dict) -> dict:
    """Builds the §02 tiles and the gold-row breakdown straight from the
    judged artifact's own summary and rows — no number here is computed
    from anything but what the artifact itself reports, except the
    hallucination-flag figure, which is 1 - refusal_rate, both terms read
    from the artifact."""
    summary = data["summary"]
    tiles = []
    for key, label in TILE_LABELS.items():
        m = summary[key]
        tiles.append(
            {
                "label": label,
                "value": m["mean"],
                "target": TARGETS[key],
                "n": m["n"],
                "passed": m["mean"] >= TARGETS[key],
                "comparator": "≥",
            }
        )

    refusal_rate = summary["refusal_rate"]["value"]
    hallucination_rate = 1.0 - refusal_rate
    tiles.append(
        {
            "label": "Hallucination flag",
            "value": hallucination_rate,
            "target": HALLUCINATION_TARGET,
            "n": summary["refusal_rate"]["n"],
            "passed": hallucination_rate < HALLUCINATION_TARGET,
            "comparator": "<",
            "note": "1 − refusal rate on unanswerable questions",
        }
    )

    gold_rows = []
    for row in data["rows"]:
        gold_rows.append(
            {
                "question": row["question"],
                "answer_key": row["answer_key"],
                "refused": row["refused"],
                "scores": row["scores"],
                "is_red_row": row["question"] == RED_ROW_QUESTION,
            }
        )

    return {
        "run": data["run"],
        "judge_model": data["judge_model"],
        "judged_at": data["judged_at"],
        "n_gold_questions": len(data["rows"]),
        "tiles": tiles,
        "gold_rows": gold_rows,
    }
