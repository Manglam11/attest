import contextvars

current_owner_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_owner_id")
