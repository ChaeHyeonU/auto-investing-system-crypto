from collections.abc import Generator
import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.billing import Subscription
from app.services.billing import BillingProviderError, get_billing_provider


TEST_DATABASE_URL = "sqlite:///./test_billing_checkout.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


class FailingBillingProvider:
    def create_checkout_session(self, user_id: str, plan: str) -> None:
        _ = (user_id, plan)
        raise BillingProviderError(
            code="BILLING_STRIPE_ERROR",
            message="stripe checkout session creation failed",
            details={"reason": "stripe unavailable"},
        )


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_module() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db


def teardown_module() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_billing_checkout.db"):
        os.remove("test_billing_checkout.db")


def _register_and_get_token(client: TestClient, email: str) -> str:
    response = client.post("/v1/auth/register", json={"email": email, "password": "password123"})
    assert response.status_code == 201
    return response.json()["access_token"]


def test_checkout_session_success() -> None:
    client = TestClient(app)
    token = _register_and_get_token(client, "billing-success@example.com")

    response = client.post(
        "/v1/billing/checkout-session",
        json={"plan": "pro"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["checkout_url"].startswith("https://checkout.stripe.com/pay/stub-pro")
    assert payload["session_id"].startswith("cs_test_")

    db = TestingSessionLocal()
    try:
        sub = db.query(Subscription).order_by(Subscription.created_at.desc()).first()
        assert sub is not None
        assert sub.plan == "pro"
        assert sub.status == "pending_checkout"
    finally:
        db.close()


def test_checkout_session_plan_validation() -> None:
    client = TestClient(app)
    token = _register_and_get_token(client, "billing-invalid-plan@example.com")

    response = client.post(
        "/v1/billing/checkout-session",
        json={"plan": "enterprise"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422


def test_checkout_session_provider_error_standard_code() -> None:
    client = TestClient(app)
    token = _register_and_get_token(client, "billing-provider-error@example.com")

    app.dependency_overrides[get_billing_provider] = lambda: FailingBillingProvider()
    try:
        response = client.post(
            "/v1/billing/checkout-session",
            json={"plan": "basic"},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.pop(get_billing_provider, None)

    assert response.status_code == 502
    payload = response.json()
    assert payload["code"] == "BILLING_STRIPE_ERROR"
    assert payload["message"] == "stripe checkout session creation failed"
    assert payload["details"]["reason"] == "stripe unavailable"

