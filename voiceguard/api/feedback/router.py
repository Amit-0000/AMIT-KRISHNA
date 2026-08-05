from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import get_current_user_optional, require_admin
from api.core.middleware import client_ip
from api.core.responses import success_envelope
from api.feedback import service
from api.feedback.schemas import FeedbackResponse, FeedbackSubmitRequest
from api.scans.schemas import PaginationMeta
from api.user.models import User

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackSubmitRequest,
    request: Request,
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    feedback = await service.submit_feedback(
        db,
        user=user,
        payload=payload,
        browser=request.headers.get("user-agent"),
        ip_address=client_ip(request),
        request_id=getattr(request.state, "request_id", None),
    )
    await db.commit()
    return success_envelope({"feedback": FeedbackResponse.from_feedback(feedback).model_dump(mode="json")})


@router.get("")
async def list_feedback(
    page: int = 1,
    page_size: int = 20,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    items, total = await service.list_feedback(db, page=page, page_size=page_size)
    meta = PaginationMeta(
        page=page, page_size=page_size, total=total, total_pages=max(1, math.ceil(total / page_size))
    ).model_dump()
    return success_envelope(
        {"feedback": [FeedbackResponse.from_feedback(f).model_dump(mode="json") for f in items]}, meta=meta
    )
