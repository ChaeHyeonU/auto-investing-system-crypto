from dataclasses import dataclass
import hashlib
import hmac
import time
from typing import Protocol
from uuid import uuid4


@dataclass
class CheckoutSession:
    checkout_url: str
    session_id: str


class BillingProviderError(Exception):
    def __init__(self, code: str, message: str, details: dict[str, object] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class BillingProvider(Protocol):
    def create_checkout_session(self, user_id: str, plan: str) -> CheckoutSession:
        ...


class StripeStubBillingProvider:
    def create_checkout_session(self, user_id: str, plan: str) -> CheckoutSession:
        session_id = f"cs_test_{uuid4().hex[:16]}"
        return CheckoutSession(
            checkout_url=f"https://checkout.stripe.com/pay/stub-{plan}-{user_id[:8]}",
            session_id=session_id,
        )


def get_billing_provider() -> BillingProvider:
    return StripeStubBillingProvider()


def verify_stripe_signature(payload: bytes, signature_header: str | None, webhook_secret: str, tolerance_seconds: int = 300) -> bool:
    if not signature_header:
        return False

    parts: dict[str, str] = {}
    for segment in signature_header.split(","):
        if "=" not in segment:
            continue
        key, value = segment.split("=", 1)
        parts[key.strip()] = value.strip()

    timestamp_raw = parts.get("t")
    signature_v1 = parts.get("v1")
    if not timestamp_raw or not signature_v1:
        return False

    try:
        timestamp = int(timestamp_raw)
    except ValueError:
        return False

    now = int(time.time())
    if abs(now - timestamp) > tolerance_seconds:
        return False

    signed_payload = f"{timestamp}.{payload.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_v1)


def build_test_signature_header(payload: bytes, webhook_secret: str, timestamp: int | None = None) -> str:
    ts = timestamp if timestamp is not None else int(time.time())
    signed_payload = f"{ts}.{payload.decode('utf-8')}".encode("utf-8")
    signature = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={signature}"
