from datetime import datetime, timedelta, timezone
import json
from typing import Literal

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.billing import BillingWebhookEvent, Subscription
from app.models.user import User
from app.services.billing import (
    BillingProviderError,
    get_billing_provider,
    verify_stripe_signature,
)

router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: Literal["basic", "pro", "premium"]


def _to_datetime(value: object) -> datetime | None:
    if isinstance(value, int):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    return None


def _map_subscription_status(event_type: str, stripe_status: object) -> str | None:
    if event_type == "invoice.paid":
        return "active"
    if event_type == "customer.subscription.deleted":
        return "canceled"

    stripe_to_local = {
        "active": "active",
        "trialing": "trialing",
        "past_due": "past_due",
        "canceled": "canceled",
        "unpaid": "past_due",
        "incomplete": "past_due",
        "incomplete_expired": "canceled",
    }
    if isinstance(stripe_status, str):
        return stripe_to_local.get(stripe_status)
    return None


def _find_subscription_from_event(db: Session, event_object: dict[str, object]) -> Subscription | None:
    stripe_subscription_id = event_object.get("id")
    if not isinstance(stripe_subscription_id, str):
        stripe_subscription_id = event_object.get("subscription")

    stripe_customer_id = event_object.get("customer")
    metadata = event_object.get("metadata")
    metadata_user_id = metadata.get("user_id") if isinstance(metadata, dict) else None

    if isinstance(stripe_subscription_id, str):
        sub = db.query(Subscription).filter(Subscription.stripe_subscription_id == stripe_subscription_id).first()
        if sub:
            return sub

    if isinstance(stripe_customer_id, str):
        sub = db.query(Subscription).filter(Subscription.stripe_customer_id == stripe_customer_id).first()
        if sub:
            return sub

    if isinstance(metadata_user_id, str):
        return (
            db.query(Subscription)
            .filter(Subscription.user_id == metadata_user_id)
            .order_by(Subscription.created_at.desc())
            .first()
        )
    return None


@router.post("/checkout-session")
def create_checkout_session(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    billing_provider=Depends(get_billing_provider),
) -> dict[str, str]:
    try:
        checkout = billing_provider.create_checkout_session(current_user.id, payload.plan)
    except BillingProviderError as exc:
        return JSONResponse(
            status_code=502,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    now = datetime.now(tz=timezone.utc)
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if subscription is None:
        subscription = Subscription(
            user_id=current_user.id,
            plan=payload.plan,
            status="pending_checkout",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db.add(subscription)
    else:
        subscription.plan = payload.plan
        subscription.status = "pending_checkout"
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=30)
    db.commit()

    return {
        "checkout_url": checkout.checkout_url,
        "session_id": checkout.session_id,
    }


@router.get("/subscription")
def get_subscription(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> dict[str, str]:
    subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .order_by(Subscription.created_at.desc())
        .first()
    )
    if subscription is None:
        return {"plan": "basic", "status": "trialing"}
    return {
        "plan": subscription.plan,
        "status": subscription.status,
    }


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db),
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> JSONResponse:
    payload_bytes = await request.body()

    if not verify_stripe_signature(payload_bytes, stripe_signature, settings.stripe_webhook_secret):
        return JSONResponse(
            status_code=400,
            content={
                "code": "BILLING_WEBHOOK_SIGNATURE_INVALID",
                "message": "invalid stripe webhook signature",
                "details": None,
            },
        )

    try:
        event = json.loads(payload_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "code": "BILLING_WEBHOOK_PAYLOAD_INVALID",
                "message": "invalid webhook payload",
                "details": None,
            },
        )

    event_id = event.get("id")
    event_type = event.get("type")
    if not isinstance(event_id, str) or not isinstance(event_type, str):
        return JSONResponse(
            status_code=400,
            content={
                "code": "BILLING_WEBHOOK_EVENT_INVALID",
                "message": "missing event id or type",
                "details": None,
            },
        )

    existing = db.query(BillingWebhookEvent).filter(BillingWebhookEvent.stripe_event_id == event_id).first()
    if existing is not None:
        return JSONResponse(status_code=200, content={"received": True, "duplicate": True})

    event_object = event.get("data", {}).get("object", {})
    if not isinstance(event_object, dict):
        event_object = {}

    subscription = _find_subscription_from_event(db, event_object)
    status_synced = False
    processing_result = "ignored"

    if subscription is not None:
        mapped_status = _map_subscription_status(event_type, event_object.get("status"))
        if mapped_status:
            subscription.status = mapped_status
            status_synced = True

        stripe_customer_id = event_object.get("customer")
        if isinstance(stripe_customer_id, str):
            subscription.stripe_customer_id = stripe_customer_id

        stripe_subscription_id = event_object.get("id")
        if not isinstance(stripe_subscription_id, str):
            stripe_subscription_id = event_object.get("subscription")
        if isinstance(stripe_subscription_id, str):
            subscription.stripe_subscription_id = stripe_subscription_id

        period_start = _to_datetime(event_object.get("current_period_start"))
        period_end = _to_datetime(event_object.get("current_period_end"))
        if period_start:
            subscription.current_period_start = period_start
        if period_end:
            subscription.current_period_end = period_end

        processing_result = "processed"

    db.add(
        BillingWebhookEvent(
            stripe_event_id=event_id,
            event_type=event_type,
            processing_result=processing_result,
        )
    )
    db.commit()

    return JSONResponse(status_code=200, content={"received": True, "duplicate": False, "status_synced": status_synced})
