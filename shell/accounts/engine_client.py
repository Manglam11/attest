import httpx
from django.conf import settings

from accounts.tokens import mint_token

# Worst end-to-end /ask latency measured so far is ~196s (see JOURNAL.md).
# This must clear that with margin, not the library default.
TIMEOUT_SECONDS = 210.0


class EngineError(Exception):
    pass


class EngineUnreachable(EngineError):
    pass


class EngineAuthError(EngineError):
    pass


class EngineResponseError(EngineError):
    pass


def _client() -> httpx.Client:
    # retries=0 is httpx's own default; stating it explicitly so a future
    # transport swap can't silently reintroduce a retry on a metered call.
    return httpx.Client(transport=httpx.HTTPTransport(retries=0), timeout=TIMEOUT_SECONDS)


def _post_ask(token: str, question: str) -> dict:
    try:
        with _client() as client:
            response = client.post(
                f"{settings.ENGINE_URL}/ask",
                json={"question": question},
                headers={"Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        raise EngineUnreachable(str(exc)) from exc

    if response.status_code == 401:
        raise EngineAuthError(response.text)
    if response.status_code != 200:
        raise EngineResponseError(f"{response.status_code}: {response.text}")

    return response.json()


def ask_engine(user, question: str) -> dict:
    token = mint_token(user.get_username())
    return _post_ask(token, question)


def engine_health() -> dict:
    try:
        with _client() as client:
            response = client.get(f"{settings.ENGINE_URL}/health")
    except httpx.HTTPError as exc:
        raise EngineUnreachable(str(exc)) from exc

    if response.status_code != 200:
        raise EngineResponseError(f"{response.status_code}: {response.text}")

    return response.json()
