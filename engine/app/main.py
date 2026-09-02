import logging
import time

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.agent import run_agent
from app.auth import TokenError, verify_token

app = FastAPI(title="Attest Engine")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("attest.engine")


class AskRequest(BaseModel):
    question: str


def require_owner(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        return verify_token(token)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@app.get("/health")
def health():
    return {"status": "alive", "service": "engine"}


@app.post("/ask")
def ask(request: AskRequest, owner_id: str = Depends(require_owner)):
    t0 = time.perf_counter()
    result = run_agent(request.question, owner_id)
    latency_s = round(time.perf_counter() - t0, 3)
    logger.info("ask latency_s=%.3f question=%r", latency_s, request.question[:80])
    return {
        "question": request.question,
        "answer": result["answer"],
        "tool_calls": result["tool_calls"],
        "contexts": result["contexts"],
        "sources": result["sources"],
        "refused": result["refused"],
        "latency_s": latency_s,
    }
