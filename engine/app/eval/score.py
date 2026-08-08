from app.retrieve import retrieve
from app.eval.gold_set import GOLD_SET


def score_one(question: str, answer_key: str, top_k: int = 5) -> dict:
    chunks = retrieve(question, top_k)
    relevant = sum(1 for chunk in chunks if answer_key in chunk)
    return {
        "hit": relevant > 0,
        "precision": relevant / len(chunks) if chunks else 0.0,
        "relevant": relevant,
        "retrieved": len(chunks),
    }


def run() -> None:
    results = []
    for item in GOLD_SET:
        r = score_one(item["question"], item["answer_key"])
        results.append(r)
        mark = "HIT " if r["hit"] else "MISS"
        print(f"[{mark}] {r['relevant']}/{r['retrieved']}  {item['question']}")

    n = len(results)
    hit_rate = sum(1 for r in results if r["hit"]) / n
    precision = sum(r["precision"] for r in results) / n

    print("\n--- baseline: vector-only, top-5 ---")
    print(f"hit rate:  {hit_rate:.2f}  ({sum(1 for r in results if r['hit'])}/{n} questions)")
    print(f"precision: {precision:.2f}  (§02 target >= 0.85)")


if __name__ == "__main__":
    run()