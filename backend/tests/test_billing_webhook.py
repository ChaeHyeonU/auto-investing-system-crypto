from collections.abc import Generator
from datetime import datetime, timedelta, timezone
import json
import os

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.billing import BillingWebhookEvent, Subscription
from app.services.billing import build_test_signature_header


TEST_DATABASE_URL = "sqlite:///./test_billing_webhook.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


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
    if os.path.exists("test_billing_webhook.db"):
        os.remove("test_billing_webhook.db")


def _register_user(client: TestClient, email: str) -> tuple[str, str]:
    response = client.post("/v1/auth/register", json={"email": email, "password": "password123"})
    assert response.status_code == 201
    payload = response.json()
    return payload["user"]["id"], payload["access_token"]


def _post_signed_webhook(client: TestClient, event: dict[str, object]) -> object:
    payload = json.dumps(event).encode("utf-8")
    signature = build_test_signature_header(payload, settings.stripe_webhook_secret)
    return client.post(
        "/v1/billing/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
    )


def test_webhook_requires_valid_signature() -> None:
    client = TestClient(app)
    event = {"id": "evt_invalid_sig", "type": "invoice.paid", "data": {"object": {}}}
    payload = json.dumps(event).encode("utf-8")

    response = client.post(
        "/v1/billing/webhooks/stripe",
        content=payload,
        headers={"Stripe-Signature": "t=1,v1=invalid", "Content-Type": "application/json"},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "BILLING_WEBHOOK_SIGNATURE_INVALID"


def test_webhook_syncs_subscription_statuses() -> None:
    client = TestClient(app)
    user_id, token = _register_user(client, "webhook-sync@example.com")

    checkout_response = client.post(
        "/v1/billing/checkout-session",
        json={"plan": "pro"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert checkout_response.status_code == 200

    now = datetime.now(tz=timezone.utc)
    start_ts = int(now.timestamp())
    end_ts = int((now + timedelta(days=30)).timestamp())

    paid_event = {
        "id": "evt_paid_1",
        "type": "invoice.paid",
        "data": {
            "object": {
                "subscription": "sub_123",
                "customer": "cus_123",
                "metadata": {"user_id": user_id},
                "current_period_start": start_ts,
                "current_period_end": end_ts,
            }
        },
    }
    paid_response = _post_signed_webhook(client, paid_event)
    assert paid_response.status_code == 200
    assert paid_response.json()["status_synced"] is True

    past_due_event = {
        "id": "evt_sub_updated_1",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_123",
                "customer": "cus_123",
                "status": "past_due",
                "current_period_start": start_ts,
                "current_period_end": end_ts,
            }
        },
    }
    past_due_response = _post_signed_webhook(client, past_due_event)
    assert past_due_response.status_code == 200

    canceled_event = {
        "id": "evt_sub_deleted_1",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_123",
                "customer": "cus_123",
                "status": "canceled",
            }
        },
    }
    canceled_response = _post_signed_webhook(client, canceled_event)
    assert canceled_response.status_code == 200

    db = TestingSessionLocal()
    try:
        sub = (
            db.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .first()
        )
        assert sub is not None
        assert sub.stripe_customer_id == "cus_123"
        assert sub.stripe_subscription_id == "sub_123"
        assert sub.status == "canceled"
    finally:
        db.close()


def test_webhook_is_idempotent_for_duplicate_event() -> None:
    client = TestClient(app)
    user_id, token = _register_user(client, "webhook-idempotent@example.com")
    checkout_response = client.post(
        "/v1/billing/checkout-session",
        json={"plan": "basic"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert checkout_response.status_code == 200

    event = {
        "id": "evt_duplicate_1",
        "type": "invoice.paid",
        "data": {
            "object": {
                "subscription": "sub_dup_1",
                "customer": "cus_dup_1",
                "metadata": {"user_id": user_id},
            }
        },
    }
    first = _post_signed_webhook(client, event)
    second = _post_signed_webhook(client, event)

    assert first.status_code == 200
    assert first.json()["duplicate"] is False
    assert second.status_code == 200
    assert second.json()["duplicate"] is True

    db = TestingSessionLocal()
    try:
        count = db.query(BillingWebhookEvent).filter(BillingWebhookEvent.stripe_event_id == "evt_duplicate_1").count()
        assert count == 1
    finally:
        db.close()

