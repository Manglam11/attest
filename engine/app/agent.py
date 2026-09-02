import os
import re

from langchain.agents import create_agent
from langchain_core.messages import ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.quota import QuotaCounterCallback
from app.refusal import REFUSAL_TEXT, is_refusal
from app.request_context import current_owner_id, current_retrieved_chunks
from app.tools import retrieve_document_chunks

MODEL = "gemini-3.6-flash"

SYSTEM_PROMPT = (
    "You are Attest, a financial-document analyst. "
    "Answer questions using ONLY the indexed document. "
    "Call retrieve_document_chunks to fetch passages before answering. "
    "For a question with multiple parts, retrieve for each part. "
    "Cite the page numbers you used. "
    "If the document does not contain the answer, say: "
    f"'{REFUSAL_TEXT}'"
)

CHUNK_BOUNDARY = re.compile(r"\n\n(?=\[page )")

model = ChatGoogleGenerativeAI(
    model=MODEL,
    api_key=os.environ["GEMINI_API_KEY"],
)

agent = create_agent(
    model,
    tools=[retrieve_document_chunks],
    system_prompt=SYSTEM_PROMPT,
)


def _flatten_content(content) -> str:
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(block["text"])
        elif isinstance(block, str):
            parts.append(block)
    return "".join(parts)


def _collect_contexts(messages) -> list[str]:
    contexts = []
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue
        for chunk in CHUNK_BOUNDARY.split(_flatten_content(message.content)):
            chunk = chunk.strip()
            if chunk and chunk not in contexts:
                contexts.append(chunk)
    return contexts


def _dedupe_sources(chunks: list[dict]) -> list[dict]:
    seen = set()
    sources = []
    for c in chunks:
        key = (c["doc_id"], c["page"], c["text"])
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "doc_id": c["doc_id"],
                "owner_id": c["owner_id"],
                "page": c["page"],
                "score": c["score"],
                "text": c["text"],
            }
        )
    return sources


def run_agent(question: str, owner_id: str) -> dict:
    owner_token = current_owner_id.set(owner_id)
    chunks_token = current_retrieved_chunks.set([])
    try:
        result = agent.invoke(
            {"messages": [{"role": "user", "content": question}]},
            config={"callbacks": [QuotaCounterCallback()]},
        )
        sources = _dedupe_sources(current_retrieved_chunks.get())
    finally:
        current_owner_id.reset(owner_token)
        current_retrieved_chunks.reset(chunks_token)
    messages = result["messages"]

    tool_calls = []
    for message in messages:
        for call in getattr(message, "tool_calls", []) or []:
            tool_calls.append(
                {"tool": call["name"], "query": call["args"].get("question", "")}
            )

    answer = _flatten_content(messages[-1].content)

    return {
        "answer": answer,
        "tool_calls": tool_calls,
        "contexts": _collect_contexts(messages),
        "sources": sources,
        "refused": is_refusal(answer),
    }