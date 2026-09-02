import base64
import hashlib
import hmac
import json
import os
import time

_SECRET = os.environ["TOKEN_SIGNING_SECRET"].encode()
TTL_SECONDS = 60


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def mint_token(owner_id: str, ttl_seconds: int = TTL_SECONDS) -> str:
    payload = {"owner_id": owner_id, "exp": int(time.time()) + ttl_seconds}
    body_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    sig_b64 = _b64encode(hmac.new(_SECRET, body_b64.encode(), hashlib.sha256).digest())
    return f"{body_b64}.{sig_b64}"
