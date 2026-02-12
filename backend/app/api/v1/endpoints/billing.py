from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.billing import Subscription
from app.models.user import User
from app.services.billing import BillingProviderError, get_billing_provider

router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: Literal["basic", "pro", "premium"]


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
