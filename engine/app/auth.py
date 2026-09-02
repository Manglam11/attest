import base64
import hashlib
import hmac
import json
import os
import time

_SECRET = os.environ["TOKEN_SIGNING_SECRET"].encode()


class TokenError(Exception):
    pass


def _b64decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def verify_token(token: str) -> str:
    parts = token.split(".")
    if len(parts) != 2:
        raise TokenError("malformed token")
    body_b64, sig_b64 = parts
    try:
        given_sig = _b64decode(sig_b64)
    except Exception:
        raise TokenError("malformed token")

    expected_sig = hmac.new(_SECRET, body_b64.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(expected_sig, given_sig):
        raise TokenError("bad signature")

    try:
        payload = json.loads(_b64decode(body_b64))
    except Exception:
        raise TokenError("malformed token")

    owner_id = payload.get("owner_id")
    exp = payload.get("exp")
    if not owner_id or not isinstance(exp, (int, float)):
        raise TokenError("malformed token")
    if exp < time.time():
        raise TokenError("expired token")

    return owner_id
