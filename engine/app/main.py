from fastapi import FastAPI
from pydantic import BaseModel

from app.agent import run_agent

app = FastAPI(title="Attest Engine")


class AskRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "alive", "service": "engine"}


@app.post("/ask")
def ask(request: AskRequest):
    result = run_agent(request.question)
    return {
        "question": request.question,
        "answer": result["answer"],
        "tool_calls": result["tool_calls"],
        "contexts": result["contexts"],
    }