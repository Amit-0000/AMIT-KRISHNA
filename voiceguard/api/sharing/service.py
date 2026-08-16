from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.audit import AuditEventType, AuditOutcome, write_audit_log
from api.core.config import get_settings
from api.core.exceptions import InvalidScanStateError, NotFoundError
from api.inference import repository as inference_repository
from api.inference.schemas import ScanResultResponse
from api.scans import repository as scans_repository
from api.scans.models import Scan
from api.sharing import repository
from api.sharing.models import ShareToken


class ShareNotFoundError(NotFoundError):
    code = "SHARE_NOT_FOUND"


async def create_share(db: AsyncSession, scan: Scan, *, ip_address: str | None, request_id: str | None) -> ShareToken:
    result = await inference_repository.get_result_by_scan_id(db, scan.id)
    if result is None:
        raise InvalidScanStateError(
            "Only a completed scan with a result can be shared.",
            details=[{"field": "scan_id", "message": "scan has no result yet"}],
        )

    existing = await repository.get_active_for_scan(db, scan.id)
    if existing is not None:
        return existing

    settings = get_settings()
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=settings.SHARE_TOKEN_EXPIRY_DAYS)
        if settings.SHARE_TOKEN_EXPIRY_DAYS > 0
        else None
    )
    share = await repository.create(db, scan_id=scan.id, user_id=scan.user_id, token=token, expires_at=expires_at)
    await write_audit_log(
        db,
        event_type=AuditEventType.SHARE_CREATED,
        outcome=AuditOutcome.SUCCESS,
        user_id=scan.user_id,
        ip_address=ip_address,
        request_id=request_id,
        details={"scan_id": str(scan.id), "share_id": str(share.id)},
    )
    return share


async def revoke_share(db: AsyncSession, scan: Scan, *, ip_address: str | None, request_id: str | None) -> None:
    existing = await repository.get_active_for_scan(db, scan.id)
    if existing is None:
        raise ShareNotFoundError("No active share link for this scan")
    await repository.revoke(db, existing)
    await write_audit_log(
        db,
        event_type=AuditEventType.SHARE_REVOKED,
        outcome=AuditOutcome.SUCCESS,
        user_id=scan.user_id,
        ip_address=ip_address,
        request_id=request_id,
        details={"scan_id": str(scan.id), "share_id": str(existing.id)},
    )


async def get_shared_result(db: AsyncSession, token: str) -> ScanResultResponse:
    share = await repository.get_by_token(db, token)
    # Same "don't distinguish missing vs. expired vs. revoked" enumeration
    # posture as api.scans.service.get_owned_scan_or_404 — a bare 404 either
    # way, never confirming a token ever existed.
    if share is None or not share.is_active:
        raise ShareNotFoundError("This shared result is not available")

    result = await inference_repository.get_result_by_scan_id(db, share.scan_id)
    if result is None:
        raise ShareNotFoundError("This shared result is not available")
    model_version = await inference_repository.get_model_version_by_id(db, result.model_version_id)
    if model_version is None:
        raise ShareNotFoundError("This shared result is not available")

    scan = await scans_repository.get_by_id(db, share.scan_id)
    malware_scan_status = scan.malware_scan_status if scan is not None else None
    return ScanResultResponse.from_result(result, model_version, malware_scan_status)
