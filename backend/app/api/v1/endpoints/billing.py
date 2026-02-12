from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.billing import Subscription
from app.models.user import User

router = APIRouter()


class CheckoutRequest(BaseModel):
    plan: str


@router.post("/checkout-session")
def create_checkout_session(
    payload: CheckoutRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, str]:
    now = datetime.now(tz=timezone.utc)
    subscription = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if subscription is None:
        subscription = Subscription(
            user_id=current_user.id,
            plan=payload.plan,
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
        )
        db.add(subscription)
    else:
        subscription.plan = payload.plan
        subscription.status = "active"
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=30)
    db.commit()

    return {
        "checkout_url": f"https://checkout.stripe.com/pay/stub-{payload.plan}",
        "session_id": "cs_test_stub",
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
