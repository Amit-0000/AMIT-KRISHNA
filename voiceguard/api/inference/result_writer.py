from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from api.inference import repository
from api.inference.confidence import ConfidenceResult
from api.inference.exceptions import ResultPersistenceError
from api.inference.explainability import ExplanationResult
from api.inference.inference import InferenceResult
from api.inference.models import ModelVersion, ScanResult
from api.scans.models import Scan


async def persist_result(
    db: AsyncSession,
    *,
    scan: Scan,
    model_version: ModelVersion,
    inference_result: InferenceResult,
    confidence_result: ConfidenceResult,
    explanation_result: ExplanationResult,
    feature_extractor_name: str,
    feature_extractor_version: str,
    processing_time_ms: int,
) -> ScanResult:
    """The SAVING_RESULTS stage's body — the single write that makes a
    scan's AI analysis durable and queryable (Result Persistence). Wraps
    repository failures in ResultPersistenceError so api.inference.jobs's
    generic per-stage retry wrapper retries a transient DB error the same
    way it retries every other stage."""
    try:
        result = await repository.create_scan_result(
            db,
            scan_id=scan.id,
            user_id=scan.user_id,
            model_version_id=model_version.id,
            label=inference_result.label,
            verdict=confidence_result.verdict,
            confidence=confidence_result.confidence,
            raw_bonafide_score=inference_result.bonafide_score,
            raw_spoof_score=inference_result.spoof_score,
            threshold_used=confidence_result.threshold_used,
            is_below_threshold=confidence_result.is_below_threshold,
            explanation={
                "salient_regions": [
                    {"start_s": r.start_s, "end_s": r.end_s, "importance": r.importance}
                    for r in explanation_result.salient_regions
                ],
                "notes": explanation_result.notes,
                "warnings": explanation_result.warnings,
                "feature_extractor": explanation_result.feature_extractor,
                "model_version": explanation_result.model_version,
            },
            feature_extractor_name=feature_extractor_name,
            feature_extractor_version=feature_extractor_version,
            processing_time_ms=processing_time_ms,
            inference_time_ms=inference_result.inference_time_ms,
        )
    except Exception as exc:  # noqa: BLE001 - any DB-layer failure writing the result row
        raise ResultPersistenceError(f"Failed to persist scan result: {exc}") from exc
    return result
