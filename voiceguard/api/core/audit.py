from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from api.core.database import Base
from api.core.security import hash_ip


class AuditEventType(str, Enum):
    USER_REGISTERED = "USER_REGISTERED"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILURE = "LOGIN_FAILURE"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    PASSWORD_RESET_COMPLETED = "PASSWORD_RESET_COMPLETED"
    EMAIL_CHANGE_INITIATED = "EMAIL_CHANGE_INITIATED"
    EMAIL_CHANGE_COMPLETED = "EMAIL_CHANGE_COMPLETED"
    OAUTH_ACCOUNT_LINKED = "OAUTH_ACCOUNT_LINKED"
    OAUTH_LOGIN = "OAUTH_LOGIN"
    ACCOUNT_DELETION_INITIATED = "ACCOUNT_DELETION_INITIATED"
    ACCOUNT_DELETION_CANCELLED = "ACCOUNT_DELETION_CANCELLED"
    ACCOUNT_PURGED = "ACCOUNT_PURGED"
    REFRESH_TOKEN_ISSUED = "REFRESH_TOKEN_ISSUED"
    REFRESH_TOKEN_ROTATED = "REFRESH_TOKEN_ROTATED"
    REFRESH_TOKEN_REVOKED = "REFRESH_TOKEN_REVOKED"
    REFRESH_TOKEN_REUSE_DETECTED = "REFRESH_TOKEN_REUSE_DETECTED"
    API_KEY_CREATED = "API_KEY_CREATED"
    API_KEY_REVOKED = "API_KEY_REVOKED"
    SCAN_SUBMITTED = "SCAN_SUBMITTED"
    SCAN_CANCELLED = "SCAN_CANCELLED"
    SCAN_DELETED = "SCAN_DELETED"
    SCAN_BULK_DELETED = "SCAN_BULK_DELETED"
    SCAN_PROCESSING_STARTED = "SCAN_PROCESSING_STARTED"
    SCAN_PROCESSING_COMPLETED = "SCAN_PROCESSING_COMPLETED"
    SCAN_PROCESSING_FAILED = "SCAN_PROCESSING_FAILED"
    FEEDBACK_SUBMITTED = "FEEDBACK_SUBMITTED"
    SHARE_CREATED = "SHARE_CREATED"
    SHARE_REVOKED = "SHARE_REVOKED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    ADMIN_ACTION = "ADMIN_ACTION"
    GUEST_SESSION_EXPIRED = "GUEST_SESSION_EXPIRED"
    GUEST_SCANS_MIGRATED = "GUEST_SCANS_MIGRATED"


class AuditOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )
    outcome: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    service: Mapped[str] = mapped_column(sa.String(32), nullable=False, default="api")

    # Intentionally NOT a foreign key (BATCH_05 Data Domains §4.8): the subject
    # user may later be purged, but the audit trail must survive.
    user_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid(as_uuid=True), nullable=True, index=True)
    ip_hash: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(sa.Uuid(as_uuid=True), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON().with_variant(postgresql.JSONB, "postgresql"), nullable=True
    )


async def write_audit_log(
    db: AsyncSession,
    *,
    event_type: AuditEventType,
    outcome: AuditOutcome,
    user_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
    details: dict[str, Any] | None = None,
    service: str = "api",
) -> None:
    """Commits on its own session sharing `db`'s engine, independent of `db`'s
    transaction. Callers routinely write a failure event and then raise
    (e.g. LOGIN_FAILURE, REFRESH_TOKEN_REUSE_DETECTED) — api.core.database.get_db
    rolls `db` back when that exception propagates, which would silently
    discard a same-session flush. Committing separately here is what makes the
    audit trail durable across that rollback (BATCH_04 S14.7)."""
    log = AuditLog(
        event_type=event_type.value,
        outcome=outcome.value,
        service=service,
        user_id=user_id,
        ip_hash=hash_ip(ip_address) if ip_address else None,
        user_agent=user_agent[:512] if user_agent else None,
        request_id=uuid.UUID(request_id) if request_id else None,
        details=details,
    )
    async with AsyncSession(bind=db.bind, expire_on_commit=False) as audit_session:
        audit_session.add(log)
        await audit_session.commit()
