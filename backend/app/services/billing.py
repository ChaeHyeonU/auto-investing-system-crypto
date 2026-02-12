from dataclasses import dataclass
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

