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
    # Joined to Scan and filtered on Scan.deleted_at to match
    # count_all_for_user()'s population (api/scans/repository.py) — without
    # this join, a ScanResult whose parent Scan was soft-deleted from History
    # kept counting toward verdict totals forever while count_all_for_user()
    # correctly stopped counting it, letting AI Detected / Human Verified
    # percentages exceed 100% of Total Analyses.
    result = await db.execute(
        select(ScanResult.verdict, func.count())
        .join(Scan, Scan.id == ScanResult.scan_id)
        .where(ScanResult.user_id == user_id, Scan.deleted_at.is_(None))
        .group_by(ScanResult.verdict)
    )
    return {verdict: count for verdict, count in result.all()}


async def avg_processing_time_ms(db: AsyncSession, user_id: uuid.UUID) -> float | None:
    # Same deleted-scan exclusion as verdict_counts() above, for the same
    # reason: this feeds the "Avg Processing" dashboard stat, which should
    # describe the same population of scans as "Total Analyses".
    result = await db.execute(
        select(func.avg(ScanResult.processing_time_ms))
        .join(Scan, Scan.id == ScanResult.scan_id)
        .where(ScanResult.user_id == user_id, Scan.deleted_at.is_(None))
    )
    return result.scalar_one()


async def results_since(db: AsyncSession, user_id: uuid.UUID, since: datetime) -> list[ScanResult]:
    # Feeds the Detection Trend chart — excluded the same way as
    # verdict_counts() so a deleted scan doesn't keep inflating past days'
    # trend bars after it no longer counts anywhere else on the dashboard.
    result = await db.execute(
        select(ScanResult)
        .join(Scan, Scan.id == ScanResult.scan_id)
        .where(ScanResult.user_id == user_id, ScanResult.created_at >= since, Scan.deleted_at.is_(None))
    )
    return list(result.scalars().all())


async def all_confidences(db: AsyncSession, user_id: uuid.UUID) -> list[float]:
    # Feeds the Confidence Distribution chart — same exclusion as above.
    result = await db.execute(
        select(ScanResult.confidence)
        .join(Scan, Scan.id == ScanResult.scan_id)
        .where(ScanResult.user_id == user_id, Scan.deleted_at.is_(None))
    )
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
