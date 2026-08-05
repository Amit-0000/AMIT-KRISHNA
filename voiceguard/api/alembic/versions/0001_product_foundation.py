"""Product Foundation: users, user_preferences, oauth_accounts, refresh_tokens,
email_verifications, password_reset_tokens, audit_logs.

Revision ID: 0001_product_foundation
Revises:
Create Date: 2026-07-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_product_foundation"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(60), nullable=True),
        sa.Column("role", sa.Enum("user", "admin", name="user_role"), nullable=False, server_default="user"),
        sa.Column(
            "subscription_tier",
            sa.Enum("free", "pro", "enterprise", name="subscription_tier"),
            nullable=False,
            server_default="free",
        ),
        sa.Column("email_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("onboarding_completed", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("display_name", sa.String(64), nullable=True),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column(
            "usage_context",
            sa.Enum(
                "personal", "journalist", "hr", "cybersecurity", "creator", "developer", "unknown",
                name="usage_context",
            ),
            nullable=True,
        ),
        sa.Column("deletion_scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deletion_purge_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("theme", sa.Enum("system", "light", "dark", name="preference_theme"), nullable=False, server_default="system"),
        sa.Column("language", sa.String(10), nullable=False, server_default="en"),
        sa.Column("show_gradcam", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("expanded_technical_details", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "waveform_player_size",
            sa.Enum("compact", "full", name="waveform_player_size"),
            nullable=False,
            server_default="compact",
        ),
        sa.Column("show_quick_stats", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "dashboard_chart_type",
            sa.Enum("bar", "donut", "hidden", name="dashboard_chart_type"),
            nullable=False,
            server_default="donut",
        ),
        sa.Column("email_scan_complete", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("email_model_updates", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("email_product_news", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("inapp_scan_complete", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("inapp_model_updates", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "notification_frequency",
            sa.Enum("realtime", "daily", "weekly", name="notification_frequency"),
            nullable=False,
            server_default="realtime",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_user_preferences_user_id", "user_preferences", ["user_id"], unique=True)

    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(254), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("provider IN ('google', 'github')", name="ck_oauth_accounts_provider"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_accounts_provider_identity"),
    )
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "email_verifications",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("email_address", sa.String(254), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_email_verifications_token_hash", "email_verifications", ["token_hash"], unique=True)
    op.create_index("ix_email_verifications_user_id", "email_verifications", ["user_id"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=True)
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("service", sa.String(32), nullable=False, server_default="api"),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("ip_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("request_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=True),
        sa.CheckConstraint("timestamp <= now() + interval '5 seconds'", name="ck_audit_logs_timestamp_not_future"),
    )
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("password_reset_tokens")
    op.drop_table("email_verifications")
    op.drop_table("refresh_tokens")
    op.drop_table("oauth_accounts")
    op.drop_table("user_preferences")
    op.drop_table("users")
    for enum_name in (
        "notification_frequency",
        "dashboard_chart_type",
        "waveform_player_size",
        "preference_theme",
        "usage_context",
        "subscription_tier",
        "user_role",
    ):
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
