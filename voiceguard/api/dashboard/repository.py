from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.inference.models import ModelVersion, ScanResult
from api.scans.models import Scan

# Read-only aggregation for the Dashboard slice. Deliberately queries
# api.scans/api.inference's own ORM models directly rather than adding
# dashboard-specific methods to their repositories — api.inference.router
# already establishes the pattern of one slice's router/service reading
# another slice's repository module directly (get_owned_scan_or_404), so a
# read-only cross-slice SELECT here is consistent with that, not a new
# pattern. No table in this file is owned by this slice.


async def verdict_counts(db: AsyncSession, user_id: uuid.UUID) -> dict[str, int]:
    result = await db.execute(
        select(ScanResult.verdict, func.count())
        .where(ScanResult.user_id == user_id)
        .group_by(ScanResult.verdict)
    )
    return {verdict: count for verdict, count in result.all()}


async def avg_processing_time_ms(db: AsyncSession, user_id: uuid.UUID) -> float | None:
    result = await db.execute(
        select(func.avg(ScanResult.processing_time_ms)).where(ScanResult.user_id == user_id)
    )
    return result.scalar_one()


async def results_since(db: AsyncSession, user_id: uuid.UUID, since: datetime) -> list[ScanResult]:
    result = await db.execute(
        select(ScanResult).where(ScanResult.user_id == user_id, ScanResult.created_at >= since)
    )
    return list(result.scalars().all())


async def all_confidences(db: AsyncSession, user_id: uuid.UUID) -> list[float]:
    result = await db.execute(select(ScanResult.confidence).where(ScanResult.user_id == user_id))
    return [row[0] for row in result.all()]


async def recent_results_with_scan(
    db: AsyncSession, user_id: uuid.UUID, *, limit: int
) -> list[tuple[Scan, ScanResult, ModelVersion]]:
    result = await db.execute(
        select(Scan, ScanResult, ModelVersion)
        .join(ScanResult, ScanResult.scan_id == Scan.id)
        .join(ModelVersion, ModelVersion.id == ScanResult.model_version_id)
        .where(Scan.user_id == user_id, Scan.deleted_at.is_(None))
        .order_by(ScanResult.created_at.desc())
        .limit(limit)
    )
    return [(row[0], row[1], row[2]) for row in result.all()]
