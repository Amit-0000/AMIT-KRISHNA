from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from api.user.models import SubscriptionTier, User, UserRole

# scan_count_today / scan_limit_daily are placeholders until the scan module
# (a later vertical slice) tracks real usage. daily limit mirrors the FREE
# tier default from BATCH_04 §11.6 (50/day authenticated).
DEFAULT_SCAN_LIMIT_DAILY = 50


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    avatar_url: str | None
    role: UserRole
    subscription_tier: SubscriptionTier
    email_verified: bool
    onboarding_completed: bool
    created_at: datetime
    scan_count_today: int = 0
    scan_limit_daily: int = DEFAULT_SCAN_LIMIT_DAILY

    @field_serializer("created_at")
    def _serialize_created_at(self, value: datetime) -> str:
        return value.isoformat()

    @classmethod
    def from_user(cls, user: User, *, scan_count_today: int | None = None) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email,
            display_name=user.display_name or user.email.split("@")[0],
            avatar_url=user.avatar_url,
            role=user.role,
            subscription_tier=user.subscription_tier,
            email_verified=user.email_verified,
            onboarding_completed=user.onboarding_completed,
            created_at=user.created_at,
            scan_count_today=scan_count_today if scan_count_today is not None else 0,
            scan_limit_daily=DEFAULT_SCAN_LIMIT_DAILY,
        )


class UserEnvelope(BaseModel):
    user: UserResponse


class UpdateProfileRequest(BaseModel):
    display_name: str | None = None
    onboarding_completed: bool | None = None

    def validate_display_name(self) -> None:
        if self.display_name is None:
            return
        stripped = self.display_name.strip()
        if not (1 <= len(stripped) <= 64):
            raise ValueError("display_name must be 1-64 characters")
