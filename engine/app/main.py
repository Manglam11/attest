import logging
import time

from fastapi import FastAPI
from pydantic import BaseModel

from app.agent import run_agent

app = FastAPI(title="Attest Engine")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("attest.engine")


class AskRequest(BaseModel):
    question: str


@app.get("/health")
def health():
    return {"status": "alive", "service": "engine"}


@app.post("/ask")
def ask(request: AskRequest):
    t0 = time.perf_counter()
    result = run_agent(request.question)
    latency_s = round(time.perf_counter() - t0, 3)
    logger.info("ask latency_s=%.3f question=%r", latency_s, request.question[:80])
    return {
        "question": request.question,
        "answer": result["answer"],
        "tool_calls": result["tool_calls"],
        "contexts": result["contexts"],
        "latency_s": latency_s,
    }
