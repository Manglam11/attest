REFUSAL_TEXT = "I cannot answer this from the provided sources."


def is_refusal(answer: str) -> bool:
    return REFUSAL_TEXT.rstrip(".").lower() in (answer or "").lower()
