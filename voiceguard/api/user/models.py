from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.core.database import Base, enum_values


class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class UsageContext(str, Enum):
    PERSONAL = "personal"
    JOURNALIST = "journalist"
    HR = "hr"
    CYBERSECURITY = "cybersecurity"
    CREATOR = "creator"
    DEVELOPER = "developer"
    UNKNOWN = "unknown"


class Theme(str, Enum):
    SYSTEM = "system"
    LIGHT = "light"
    DARK = "dark"


class WaveformPlayerSize(str, Enum):
    COMPACT = "compact"
    FULL = "full"


class DashboardChartType(str, Enum):
    BAR = "bar"
    DONUT = "donut"
    HIDDEN = "hidden"


class NotificationFrequency(str, Enum):
    REALTIME = "realtime"
    DAILY = "daily"
    WEEKLY = "weekly"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(sa.String(254), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(sa.String(60), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole, name="user_role", values_callable=enum_values), nullable=False, default=UserRole.USER
    )
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        sa.Enum(SubscriptionTier, name="subscription_tier", values_callable=enum_values),
        nullable=False,
        default=SubscriptionTier.FREE,
    )
    email_verified: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    # Onboarding wizard (S06) is a future slice; default true so the existing
    # frontend OnboardingGuard is a no-op until that slice lands.
    onboarding_completed: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    display_name: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    usage_context: Mapped[UsageContext | None] = mapped_column(
        sa.Enum(UsageContext, name="usage_context", values_callable=enum_values), nullable=True
    )
    deletion_scheduled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    deletion_purge_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    preferences: Mapped["UserPreferences | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (sa.CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),)


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    theme: Mapped[Theme] = mapped_column(
        sa.Enum(Theme, name="preference_theme", values_callable=enum_values),
        nullable=False,
        default=Theme.SYSTEM,
    )
    language: Mapped[str] = mapped_column(sa.String(10), nullable=False, default="en")
    show_gradcam: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    expanded_technical_details: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    waveform_player_size: Mapped[WaveformPlayerSize] = mapped_column(
        sa.Enum(WaveformPlayerSize, name="waveform_player_size", values_callable=enum_values),
        nullable=False,
        default=WaveformPlayerSize.COMPACT,
    )
    show_quick_stats: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    dashboard_chart_type: Mapped[DashboardChartType] = mapped_column(
        sa.Enum(DashboardChartType, name="dashboard_chart_type", values_callable=enum_values),
        nullable=False,
        default=DashboardChartType.DONUT,
    )
    email_scan_complete: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    email_model_updates: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    email_product_news: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    inapp_scan_complete: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    inapp_model_updates: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)
    notification_frequency: Mapped[NotificationFrequency] = mapped_column(
        sa.Enum(NotificationFrequency, name="notification_frequency", values_callable=enum_values),
        nullable=False,
        default=NotificationFrequency.REALTIME,
    )
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    user: Mapped[User] = relationship(back_populates="preferences")
