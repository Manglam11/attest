from langchain.tools import tool
from app.request_context import current_owner_id, current_retrieved_chunks
from app.retrieve import retrieve


@tool
def retrieve_document_chunks(question: str) -> str:
    """Search the indexed financial document and return the most relevant
    passages for a question. Use this whenever you need facts, figures, or
    text from the document to answer. Returns the passage text with page
    numbers."""
    chunks = retrieve(question, current_owner_id.get())
    try:
        current_retrieved_chunks.get().extend(chunks)
    except LookupError:
        pass
    return "\n\n".join(f"[page {c['page']}] {c['text']}" for c in chunks)
