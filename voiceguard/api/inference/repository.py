from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.inference.models import FeatureVector, ModelVersion, ProcessingFailure, ProcessingMetric, ScanResult


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Model registry ───────────────────────────────────────────────────────────


async def get_model_version_by_name_version(db: AsyncSession, *, name: str, version: str) -> ModelVersion | None:
    result = await db.execute(select(ModelVersion).where(ModelVersion.name == name, ModelVersion.version == version))
    return result.scalar_one_or_none()


async def get_model_version_by_id(db: AsyncSession, model_version_id: uuid.UUID) -> ModelVersion | None:
    return await db.get(ModelVersion, model_version_id)


async def get_active_model_version(db: AsyncSession) -> ModelVersion | None:
    result = await db.execute(
        select(ModelVersion).where(ModelVersion.status == "active").order_by(ModelVersion.created_at.desc())
    )
    return result.scalars().first()


async def list_model_versions(db: AsyncSession) -> list[ModelVersion]:
    result = await db.execute(select(ModelVersion).order_by(ModelVersion.created_at.desc()))
    return list(result.scalars().all())


async def create_model_version(
    db: AsyncSession,
    *,
    name: str,
    version: str,
    architecture: str,
    checkpoint_path: str,
    sha256_checksum: str,
    feature_extractor_name: str,
    feature_extractor_version: str,
    status: str = "inactive",
    metadata: dict[str, Any] | None = None,
) -> ModelVersion:
    model_version = ModelVersion(
        name=name,
        version=version,
        architecture=architecture,
        checkpoint_path=checkpoint_path,
        sha256_checksum=sha256_checksum,
        feature_extractor_name=feature_extractor_name,
        feature_extractor_version=feature_extractor_version,
        status=status,
        model_metadata=metadata,
    )
    db.add(model_version)
    await db.flush()
    return model_version


async def mark_model_loaded(db: AsyncSession, model_version: ModelVersion) -> None:
    model_version.loaded_at = _utcnow()
    await db.flush()


async def set_model_status(db: AsyncSession, model_version: ModelVersion, status: str) -> None:
    model_version.status = status
    await db.flush()


# ── Feature vectors ──────────────────────────────────────────────────────────


async def create_feature_vector(
    db: AsyncSession,
    *,
    scan_id: uuid.UUID,
    extractor_name: str,
    extractor_version: str,
    shape: list[int],
    dtype: str,
    storage_key: str | None,
    summary_stats: dict[str, float] | None,
) -> FeatureVector:
    vector = FeatureVector(
        scan_id=scan_id,
        extractor_name=extractor_name,
        extractor_version=extractor_version,
        shape=shape,
        dtype=dtype,
        storage_key=storage_key,
        summary_stats=summary_stats,
    )
    db.add(vector)
    await db.flush()
    return vector


async def get_feature_vector(
    db: AsyncSession, *, scan_id: uuid.UUID, extractor_name: str, extractor_version: str
) -> FeatureVector | None:
    result = await db.execute(
        select(FeatureVector).where(
            FeatureVector.scan_id == scan_id,
            FeatureVector.extractor_name == extractor_name,
            FeatureVector.extractor_version == extractor_version,
        )
    )
    return result.scalar_one_or_none()


# ── Processing metrics / failures ───────────────────────────────────────────


async def record_metric(
    db: AsyncSession, *, scan_id: uuid.UUID, stage: str, attempt: int, status: str, duration_ms: int
) -> ProcessingMetric:
    metric = ProcessingMetric(scan_id=scan_id, stage=stage, attempt=attempt, status=status, duration_ms=duration_ms)
    db.add(metric)
    await db.flush()
    return metric


async def record_failure(
    db: AsyncSession,
    *,
    scan_id: uuid.UUID,
    stage: str,
    attempt: int,
    error_code: str,
    error_type: str,
    error_message: str,
    retryable: bool,
) -> ProcessingFailure:
    failure = ProcessingFailure(
        scan_id=scan_id,
        stage=stage,
        attempt=attempt,
        error_code=error_code,
        error_type=error_type,
        error_message=error_message[:1024],
        retryable=retryable,
    )
    db.add(failure)
    await db.flush()
    return failure


async def list_metrics_for_scan(db: AsyncSession, scan_id: uuid.UUID) -> list[ProcessingMetric]:
    result = await db.execute(
        select(ProcessingMetric).where(ProcessingMetric.scan_id == scan_id).order_by(ProcessingMetric.created_at)
    )
    return list(result.scalars().all())


async def list_failures_for_scan(db: AsyncSession, scan_id: uuid.UUID) -> list[ProcessingFailure]:
    result = await db.execute(
        select(ProcessingFailure).where(ProcessingFailure.scan_id == scan_id).order_by(ProcessingFailure.occurred_at)
    )
    return list(result.scalars().all())


# ── Scan results ─────────────────────────────────────────────────────────────


async def create_scan_result(
    db: AsyncSession,
    *,
    scan_id: uuid.UUID,
    user_id: uuid.UUID,
    model_version_id: uuid.UUID,
    label: str,
    verdict: str,
    confidence: float,
    raw_bonafide_score: float,
    raw_spoof_score: float,
    threshold_used: float,
    is_below_threshold: bool,
    explanation: dict[str, Any] | None,
    feature_extractor_name: str,
    feature_extractor_version: str,
    processing_time_ms: int,
    inference_time_ms: int,
) -> ScanResult:
    result = ScanResult(
        scan_id=scan_id,
        user_id=user_id,
        model_version_id=model_version_id,
        label=label,
        verdict=verdict,
        confidence=confidence,
        raw_bonafide_score=raw_bonafide_score,
        raw_spoof_score=raw_spoof_score,
        threshold_used=threshold_used,
        is_below_threshold=is_below_threshold,
        explanation=explanation,
        feature_extractor_name=feature_extractor_name,
        feature_extractor_version=feature_extractor_version,
        processing_time_ms=processing_time_ms,
        inference_time_ms=inference_time_ms,
    )
    db.add(result)
    await db.flush()
    return result


async def get_result_by_scan_id(db: AsyncSession, scan_id: uuid.UUID) -> ScanResult | None:
    result = await db.execute(select(ScanResult).where(ScanResult.scan_id == scan_id))
    return result.scalar_one_or_none()
