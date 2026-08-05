from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from api.dashboard import repository
from api.dashboard.schemas import (
    ActivityItemResponse,
    ConfidenceBucketResponse,
    DashboardResponse,
    DashboardStatsResponse,
    ModelStatusResponse,
    RecentScanResponse,
    TrendPointResponse,
)
from api.inference import model_registry
from api.scans import repository as scans_repository
from api.sharing import repository as sharing_repository
from api.user.schemas import DEFAULT_SCAN_LIMIT_DAILY

TREND_WINDOW_DAYS = 30
RECENT_LIMIT = 50
ACTIVITY_LIMIT = 10

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

_BUCKET_EDGES = [(i * 10, (i + 1) * 10) for i in range(10)]


def _zone_for(bucket_min: int) -> str:
    if bucket_min >= 80:
        return "definitive"
    if bucket_min >= 60:
        return "borderline"
    return "uncertain"


def _format_date(d: datetime) -> str:
    return f"{_MONTHS[d.month - 1]} {d.day}"


async def _stats(db: AsyncSession, user_id: uuid.UUID) -> DashboardStatsResponse:
    total_scans = await scans_repository.count_all_for_user(db, user_id)
    verdicts = await repository.verdict_counts(db, user_id)
    avg_ms = await repository.avg_processing_time_ms(db, user_id)
    scans_today = await scans_repository.count_created_since(
        db, user_id=user_id, since=datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    )
    now = datetime.now(timezone.utc)
    next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    reset_in_hours = max(1, round((next_midnight - now).total_seconds() / 3600))

    return DashboardStatsResponse(
        total_scans=total_scans,
        ai_detected=verdicts.get("ai_generated", 0),
        human_verified=verdicts.get("human", 0),
        uncertain=verdicts.get("uncertain", 0),
        avg_processing_ms=round(avg_ms) if avg_ms is not None else 0,
        scans_today=scans_today,
        scan_limit_daily=DEFAULT_SCAN_LIMIT_DAILY,
        reset_in_hours=reset_in_hours,
    )


async def _trend(db: AsyncSession, user_id: uuid.UUID) -> list[TrendPointResponse]:
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(days=TREND_WINDOW_DAYS - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    results = await repository.results_since(db, user_id, window_start)

    buckets: dict[str, dict[str, int]] = {}
    for i in range(TREND_WINDOW_DAYS):
        day = window_start + timedelta(days=i)
        buckets[_format_date(day)] = {"total": 0, "ai_generated": 0, "human": 0, "uncertain": 0}

    for result in results:
        key = _format_date(result.created_at)
        if key not in buckets:
            continue
        buckets[key]["total"] += 1
        if result.verdict in buckets[key]:
            buckets[key][result.verdict] += 1

    return [
        TrendPointResponse(date=date, total=v["total"], ai_generated=v["ai_generated"], human=v["human"], uncertain=v["uncertain"])
        for date, v in buckets.items()
    ]


async def _confidence_distribution(db: AsyncSession, user_id: uuid.UUID) -> list[ConfidenceBucketResponse]:
    confidences = await repository.all_confidences(db, user_id)
    counts = [0] * 10
    for c in confidences:
        pct = min(99.999, max(0.0, c * 100))
        counts[int(pct // 10)] += 1

    return [
        ConfidenceBucketResponse(range=f"{lo}–{hi}%", min=lo, max=hi, count=counts[i], zone=_zone_for(lo))
        for i, (lo, hi) in enumerate(_BUCKET_EDGES)
    ]


async def _recent_activity(db: AsyncSession, user_id: uuid.UUID) -> list[ActivityItemResponse]:
    rows = await repository.recent_results_with_scan(db, user_id, limit=ACTIVITY_LIMIT)
    items: list[ActivityItemResponse] = []
    for scan, result, _model_version in rows:
        pct = round(result.confidence * 100, 1)
        verdict_label = {"human": "Human", "ai_generated": "AI Generated", "uncertain": "Uncertain"}.get(
            result.verdict, result.verdict
        )
        items.append(
            ActivityItemResponse(
                id=str(result.id),
                type="scan_complete",
                title="Scan complete",
                description=f"{scan.original_filename} — {verdict_label} · {pct}%",
                timestamp=result.created_at.isoformat(),
                verdict=result.verdict,
                scan_id=str(scan.id),
            )
        )
    return items


async def _model_status(db: AsyncSession) -> ModelStatusResponse:
    health = await model_registry.health_check(db)
    if not health.get("available"):
        return ModelStatusResponse(
            version="unavailable", health="down", avg_inference_ms=None, last_checked=datetime.now(timezone.utc)
        )
    loaded = bool(health.get("loaded_in_memory"))
    return ModelStatusResponse(
        version=f"{health['name']}:{health['version']}",
        health="healthy" if loaded else "degraded",
        avg_inference_ms=None,
        last_checked=datetime.now(timezone.utc),
    )


async def get_dashboard(db: AsyncSession, user_id: uuid.UUID) -> DashboardResponse:
    return DashboardResponse(
        stats=await _stats(db, user_id),
        trend=await _trend(db, user_id),
        confidence_distribution=await _confidence_distribution(db, user_id),
        recent_activity=await _recent_activity(db, user_id),
        model_status=await _model_status(db),
    )


async def get_recent_scans(db: AsyncSession, user_id: uuid.UUID) -> list[RecentScanResponse]:
    rows = await repository.recent_results_with_scan(db, user_id, limit=RECENT_LIMIT)
    out: list[RecentScanResponse] = []
    for scan, result, model_version in rows:
        confidence_pct = round(result.confidence * 100, 1)
        human_score = confidence_pct if result.verdict == "human" else round(100 - confidence_pct, 1)
        ai_score = confidence_pct if result.verdict == "ai_generated" else round(100 - confidence_pct, 1)
        active_share = await sharing_repository.get_active_for_scan(db, scan.id)
        out.append(
            RecentScanResponse(
                scan_id=str(scan.id),
                status="completed",
                verdict=result.verdict,
                confidence=confidence_pct,
                human_score=human_score,
                ai_score=ai_score,
                inference_time_ms=result.inference_time_ms,
                model_version=f"{model_version.name}:{model_version.version}",
                segment_count=max(1, round((scan.duration_seconds or 0) / 3)) if scan.duration_seconds else 1,
                frequency_heatmap=None,
                file_name=scan.original_filename,
                file_duration_seconds=scan.duration_seconds,
                created_at=result.created_at.isoformat(),
                share_token=active_share.token if active_share else None,
                user_verdict=None,
            )
        )
    return out
