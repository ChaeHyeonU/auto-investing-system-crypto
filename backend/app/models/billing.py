from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(20), nullable=False, default="basic")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="trialing")
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="subscriptions")
    invoices = relationship("BillingInvoice", back_populates="subscription", cascade="all, delete-orphan")


class BillingInvoice(Base):
    __tablename__ = "billing_invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    subscription_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stripe_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount_usd: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    subscription = relationship("Subscription", back_populates="invoices")

