import base64
import hashlib
import hmac
import os
import time
from urllib.parse import quote


def generate_base32_secret(num_bytes: int = 20) -> str:
    secret = base64.b32encode(os.urandom(num_bytes)).decode("ascii")
    return secret.rstrip("=")


def _normalize_base32(secret: str) -> bytes:
    padding = "=" * ((8 - (len(secret) % 8)) % 8)
    return base64.b32decode((secret + padding).upper())


def _hotp(secret: str, counter: int, digits: int = 6) -> str:
    key = _normalize_base32(secret)
    msg = counter.to_bytes(8, "big")
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = ((h[offset] & 0x7F) << 24) | ((h[offset + 1] & 0xFF) << 16) | ((h[offset + 2] & 0xFF) << 8) | (h[offset + 3] & 0xFF)
    return str(code % (10**digits)).zfill(digits)


def generate_totp(secret: str, for_time: int | None = None, step: int = 30, digits: int = 6) -> str:
    ts = for_time if for_time is not None else int(time.time())
    counter = ts // step
    return _hotp(secret, counter, digits=digits)


def verify_totp(secret: str, code: str, valid_window: int = 1, step: int = 30, digits: int = 6) -> bool:
    now = int(time.time())
    counter = now // step
    normalized = code.strip()
    if not normalized.isdigit():
        return False
    for offset in range(-valid_window, valid_window + 1):
        expected = _hotp(secret, counter + offset, digits=digits)
        if hmac.compare_digest(expected, normalized):
            return True
    return False


def provisioning_uri(secret: str, account_name: str, issuer_name: str) -> str:
    account = quote(account_name)
    issuer = quote(issuer_name)
    return f"otpauth://totp/{issuer}:{account}?secret={secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"

