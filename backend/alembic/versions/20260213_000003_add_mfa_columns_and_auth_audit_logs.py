"""add mfa columns and auth audit logs

Revision ID: 20260213_000003
Revises: 20260213_000002
Create Date: 2026-02-13 09:15:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20260213_000003"
down_revision: Union[str, None] = "20260213_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("mfa_secret", sa.String(length=255), nullable=True))
    op.add_column(
        "users", sa.Column("mfa_failed_attempts", sa.Integer(), nullable=False, server_default=sa.text("0"))
    )
    op.add_column("users", sa.Column("mfa_locked_until", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "auth_audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_audit_logs_user_id"), "auth_audit_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_audit_logs_user_id"), table_name="auth_audit_logs")
    op.drop_table("auth_audit_logs")
    op.drop_column("users", "mfa_locked_until")
    op.drop_column("users", "mfa_failed_attempts")
    op.drop_column("users", "mfa_secret")

