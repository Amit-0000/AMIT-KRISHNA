from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.audit import AuditEventType, AuditOutcome, write_audit_log
from api.feedback import repository
from api.feedback.models import Feedback, priority_for_category
from api.feedback.schemas import FeedbackSubmitRequest
from api.user.models import User


async def submit_feedback(
    db: AsyncSession,
    *,
    user: User | None,
    payload: FeedbackSubmitRequest,
    browser: str | None,
    ip_address: str | None,
    request_id: str | None,
) -> Feedback:
    feedback = await repository.create(
        db,
        user_id=user.id if user else None,
        category=payload.category,
        message=payload.message,
        scan_id=payload.scan_id,
        email=payload.email or (user.email if user else None),
        browser=browser[:256] if browser else None,
        application_version=None,
        priority=priority_for_category(payload.category),
    )
    await write_audit_log(
        db,
        event_type=AuditEventType.FEEDBACK_SUBMITTED,
        outcome=AuditOutcome.SUCCESS,
        user_id=user.id if user else None,
        ip_address=ip_address,
        request_id=request_id,
        details={"feedback_id": str(feedback.id), "category": payload.category},
    )
    return feedback


async def list_feedback(db: AsyncSession, *, page: int, page_size: int) -> tuple[list[Feedback], int]:
    return await repository.list_paginated(db, page=page, page_size=page_size)
