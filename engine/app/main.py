from fastapi import FastAPI
from pydantic import BaseModel

from app.retrieve import retrieve
from app.generate import generate_answer

app = FastAPI(title="Attest Engine")


class AskRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "alive", "service": "engine"}


@app.post("/ask")
def ask(request: AskRequest):
    chunks = retrieve(request.question)
    answer = generate_answer(request.question, chunks)
    return {
        "question": request.question,
        "answer": answer,
        "sources": chunks,
    }