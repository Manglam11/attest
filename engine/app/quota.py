import json
import os
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler

QUOTA_DIR = Path(os.getenv("QUOTA_DIR", "/code/data/quota"))
QUOTA_PATH = QUOTA_DIR / "agent_calls.json"
AGENT_DAILY_CEILING = int(os.environ.get("AGENT_DAILY_CEILING", "20"))


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load() -> dict:
    if QUOTA_PATH.exists():
        state = json.loads(QUOTA_PATH.read_text())
        if state.get("date") == _today():
            return state
    return {"date": _today(), "count": 0}


def record_call() -> int:
    QUOTA_DIR.mkdir(parents=True, exist_ok=True)
    state = _load()
    state["count"] += 1
    QUOTA_PATH.write_text(json.dumps(state))
    return state["count"]


def used_today() -> int:
    return _load()["count"]


def remaining(ceiling: int) -> int:
    return max(0, ceiling - used_today())


class QuotaCounterCallback(BaseCallbackHandler):
    """Counts real Gemini calls, not /ask requests — a ReAct loop can burn
    several model invocations per question, and the RPD ceiling counts those,
    not the HTTP endpoint."""

    def on_chat_model_start(self, serialized, messages, **kwargs):
        record_call()
