import contextvars

current_owner_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_owner_id")
current_retrieved_chunks: contextvars.ContextVar[list] = contextvars.ContextVar(
    "current_retrieved_chunks"
)
