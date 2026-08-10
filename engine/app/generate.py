import os
from google import genai
MODEL = "gemini-3.6-flash"
def build_prompt(question: str, chunks: list[dict]) -> str:
    sources = "\n\n".join(
        f"[{i}] (page {chunk['page']}) {chunk['text']}" for i, chunk in enumerate(chunks, 1)
    )
    return f"""You are a financial-document analyst. Answer the question using ONLY the numbered sources below. Do not use any outside knowledge.
Rules:
- Cite the source number in square brackets after each claim, like [1] or [2].
- If the sources do not contain the answer, say exactly: "I cannot answer this from the provided sources." Do not guess.
- Be concise and precise with figures.
Sources:
{sources}
Question: {question}
Answer:"""
def generate_answer(question: str, chunks: list[dict]) -> str:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    prompt = build_prompt(question, chunks)
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
    )
    return response.text
if __name__ == "__main__":
    from app.retrieve import retrieve
    question = "What was Apple's total net sales in the most recent fiscal year?"
    chunks = retrieve(question)
    answer = generate_answer(question, chunks)
    print(f"Q: {question}\n")
    print(f"A: {answer}")