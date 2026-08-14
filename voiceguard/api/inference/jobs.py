from __future__ import annotations

import asyncio
import io
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from api.core.audit import AuditEventType, AuditOutcome, write_audit_log
from api.core.config import get_settings
from api.core.database import get_engine
from api.core.storage import get_storage_backend
from api.inference import confidence, explainability, feature_extraction, inference, model_loader, model_registry
from api.inference import preprocessing as preprocessing_stage
from api.inference import repository as inference_repository
from api.inference import result_writer
from api.inference.adapters import registry as adapter_registry
from api.inference.adapters.base import ModelAdapter
from api.inference.exceptions import AIPipelineError, AIStageTimeoutError
from api.inference.feature_extraction import ExtractedFeature
from api.inference.model_loader import LoadedModel
from api.inference.models import ModelVersion
from api.inference.service import AI_JOB_TYPE
from api.scans import repository as scans_repository
from api.scans.models import Scan
from api.scans.service import transition
from api.scans.state_machine import AI_STAGE_FAILURE_TARGET, ScanStatus, can_transition

logger = logging.getLogger("voiceguard.inference")

T = TypeVar("T")


class _PipelineAborted(Exception):
    """Internal control-flow signal only: raised once a stage has already
    transitioned the scan to its terminal failure state (or the scan was
    cancelled out from under the job) and committed — run_ai_pipeline_job
    catches it and simply returns, mirroring how api.scans.jobs.run_preprocessing_job
    returns early on its own initial status guard."""


# ── Generic per-stage runner ─────────────────────────────────────────────────
# Every macro-stage in AI_PIPELINE_STAGES goes through this one function —
# retry count, timeout, ProcessingMetric/ProcessingFailure logging, and the
# terminal-failure transition are handled exactly once here rather than
# repeated per stage. Stage bodies (run_once) stay simple and focused; this
# is what "every stage independently replaceable, no giant processing
# function" means in practice for the orchestration layer.


async def _run_stage(
    db: AsyncSession,
    scan: Scan,
    job,
    *,
    stage: ScanStatus,
    run_once: Callable[[], Awaitable[T]],
    max_attempts: int,
    timeout_s: float,
    correlation_id: str,
) -> T:
    last_exc: BaseException | None = None
    attempt = 0

    for attempt in range(1, max_attempts + 1):
        # Cheap re-check before every attempt: a concurrent
        # POST /scans/{id}/cancel (a separate request, separate DB session)
        # may have committed CANCELLED while this job was mid-stage. This
        # doesn't close every window in the race (nothing stops it mid a
        # single blocking attempt) but catches it between attempts/stages,
        # which is most of them — see the Known Limitations note on this in
        # the slice's design doc for the remainder.
        await db.refresh(scan)
        if scan.status is ScanStatus.CANCELLED:
            logger.info(
                "ai_pipeline_cancelled",
                extra={"scan_id": str(scan.id), "stage": stage.value, "correlation_id": correlation_id},
            )
            raise _PipelineAborted()

        started = time.perf_counter()
        if job is not None:
            job.attempts = (job.attempts or 0) + 1
            await db.flush()
        try:
            result = await asyncio.wait_for(run_once(), timeout=timeout_s)
        except asyncio.TimeoutError:
            last_exc = AIStageTimeoutError(f"{stage.value} exceeded {timeout_s}s")
        except AIPipelineError as exc:
            last_exc = exc
        else:
            duration_ms = int((time.perf_counter() - started) * 1000)
            await inference_repository.record_metric(
                db, scan_id=scan.id, stage=stage.value, attempt=attempt, status="succeeded", duration_ms=duration_ms
            )
            await db.commit()
            return result

        duration_ms = int((time.perf_counter() - started) * 1000)
        error_code = getattr(last_exc, "code", "AI_PROCESSING_ERROR")
        error_message = str(getattr(last_exc, "message", last_exc))
        retryable = getattr(last_exc, "retryable", True)

        await inference_repository.record_metric(
            db, scan_id=scan.id, stage=stage.value, attempt=attempt, status="failed", duration_ms=duration_ms
        )
        await inference_repository.record_failure(
            db,
            scan_id=scan.id,
            stage=stage.value,
            attempt=attempt,
            error_code=error_code,
            error_type=type(last_exc).__name__,
            error_message=error_message,
            retryable=retryable,
        )
        await db.commit()
        logger.warning(
            "ai_stage_attempt_failed",
            extra={
                "scan_id": str(scan.id),
                "stage": stage.value,
                "attempt": attempt,
                "correlation_id": correlation_id,
                "error_code": error_code,
                "retryable": retryable,
            },
        )
        if not retryable:
            break

    failure_target = AI_STAGE_FAILURE_TARGET[stage]
    scan.error_code = getattr(last_exc, "code", "AI_PROCESSING_ERROR")
    scan.error_message = str(getattr(last_exc, "message", last_exc))[:512]
    scan.retry_count = attempt
    if job is not None:
        job.status = "failed"
        job.last_error = str(getattr(last_exc, "message", last_exc))[:1024]
        job.finished_at = datetime.now(timezone.utc)
        await db.flush()
    await transition(db, scan, failure_target, actor="system", reason=str(getattr(last_exc, "message", last_exc)))
    await write_audit_log(
        db,
        event_type=AuditEventType.SCAN_PROCESSING_FAILED,
        outcome=AuditOutcome.FAILURE,
        user_id=scan.user_id,
        details={"scan_id": str(scan.id), "stage": stage.value, "error_code": scan.error_code},
    )
    await db.commit()
    raise _PipelineAborted()


# ── Stage bodies (async glue around the synchronous, storage/DB-agnostic
#    implementations in api.inference.{preprocessing,feature_extraction,
#    inference,confidence,explainability}) ─────────────────────────────────


async def _stage_prepare_model(db: AsyncSession) -> ModelVersion:
    return await model_registry.get_active_model_version(db)


async def _stage_load_model(model_version: ModelVersion) -> LoadedModel:
    return await asyncio.to_thread(
        model_loader.load_model, model_version, device_preference=get_settings().MODEL_DEVICE
    )


async def _stage_preprocess(scan: Scan) -> preprocessing_stage.PreprocessResult:
    storage = get_storage_backend()
    return await asyncio.to_thread(preprocessing_stage.run_preprocessing, scan, storage)


async def _stage_extract_features(waveform, *, extractor_name: str, extractor_version: str) -> ExtractedFeature:
    return await asyncio.to_thread(
        feature_extraction.extract_features, waveform, extractor_name=extractor_name, extractor_version=extractor_version
    )


async def _persist_feature_vector(db: AsyncSession, scan: Scan, feature: ExtractedFeature) -> None:
    settings = get_settings()
    summary = feature_extraction.summarize(feature)
    storage_key = None
    if settings.FEATURE_VECTOR_STORAGE_ENABLED:
        # Serialization (numpy, CPU-bound) runs off the event loop; the
        # actual write goes through StorageBackend.save_stream directly —
        # that's already async and owns its own I/O efficiency, so there's
        # no need to also wrap it in asyncio.to_thread.
        key = f"features/{scan.id}_{feature.name}_{feature.version}.npy"
        data = await asyncio.to_thread(_serialize_feature_array, feature)

        async def _chunks():
            yield data

        storage = get_storage_backend()
        await storage.save_stream(key, _chunks())
        storage_key = key
    await inference_repository.create_feature_vector(
        db,
        scan_id=scan.id,
        extractor_name=feature.name,
        extractor_version=feature.version,
        shape=feature.shape,
        dtype=feature.dtype,
        storage_key=storage_key,
        summary_stats=summary,
    )
    await db.commit()


def _serialize_feature_array(feature: ExtractedFeature) -> bytes:
    """Synchronous — see api.inference.preprocessing.run_preprocessing for
    why (called via asyncio.to_thread). Serializes through the same
    StorageBackend.save_stream contract the original upload uses (see
    api.inference.models.FeatureVector's docstring for why the array lives
    in storage rather than inline in Postgres)."""
    import numpy as np

    buf = io.BytesIO()
    np.save(buf, feature.tensor.detach().cpu().numpy())
    return buf.getvalue()


async def _stage_infer(
    adapter: ModelAdapter, loaded_model: LoadedModel, feature: ExtractedFeature
) -> inference.InferenceResult:
    """Dispatches through the model's adapter rather than calling
    api.inference.inference.run_inference directly — that function is still
    what LCNNAdapter.predict() calls internally (see
    api.inference.adapters.lcnn_adapter), so LCNN's behavior here is
    unchanged; this stage just no longer has to know that's what's
    happening. Adding a third architecture never touches this function."""
    raw = await asyncio.to_thread(adapter.predict, loaded_model, feature)
    return await asyncio.to_thread(adapter.convert_prediction, raw)


async def _stage_postprocess(inference_result: inference.InferenceResult, *, threshold: float):
    return await asyncio.to_thread(confidence.calibrate_and_decide, inference_result, threshold=threshold)


async def _stage_explain(
    adapter: ModelAdapter,
    loaded_model: LoadedModel,
    feature: ExtractedFeature,
    inference_result: inference.InferenceResult,
    confidence_result: confidence.ConfidenceResult,
    *,
    silence_ratio: float,
    model_version_label: str,
) -> explainability.ExplanationResult:
    """Calls adapter.generate_explanation() unconditionally for every
    architecture — architectures that don't support explainability (see
    ModelAdapter.supports_explainability) return the "unavailable" result
    from their own generate_explanation() rather than this stage branching
    on support itself. LCNNAdapter delegates to the existing
    api.inference.explainability.generate_explanation (unchanged, still
    real Grad-CAM); other adapters may not."""
    return await asyncio.to_thread(
        adapter.generate_explanation,
        loaded_model,
        feature,
        inference_result,
        confidence_result,
        silence_ratio=silence_ratio,
        model_version_label=model_version_label,
    )


# ── Orchestrator ──────────────────────────────────────────────────────────────


async def run_ai_pipeline_job(scan_id: uuid.UUID, bind: AsyncEngine | None = None) -> None:
    """Invoked as a FastAPI BackgroundTask right after POST /scans/{id}/process
    responds — passed the same engine the request's session was bound to,
    same reasoning as api.scans.jobs.run_preprocessing_job (see that
    docstring). Drives READY_FOR_AI's PREPARING_MODEL entry point all the way
    through AI_PIPELINE_STAGES to COMPLETED, or into the failing stage's
    dedicated *_FAILED terminal state after AI_STAGE_MAX_ATTEMPTS."""
    engine = bind if bind is not None else get_engine()
    async with AsyncSession(bind=engine, expire_on_commit=False) as db:
        scan = await scans_repository.get_by_id(db, scan_id)
        if scan is None or scan.status != ScanStatus.PREPARING_MODEL:
            return  # cancelled/deleted/expired before we got here

        job = await scans_repository.get_latest_job(db, scan.id, job_type=AI_JOB_TYPE)
        if job is not None:
            job.status = "running"
            await db.commit()

        settings = get_settings()
        correlation_id = str(uuid.uuid4())
        stage_kwargs = {
            "max_attempts": settings.AI_STAGE_MAX_ATTEMPTS,
            "timeout_s": settings.AI_STAGE_TIMEOUT_S,
            "correlation_id": correlation_id,
        }
        pipeline_started = time.perf_counter()
        logger.info("ai_pipeline_started", extra={"scan_id": str(scan.id), "correlation_id": correlation_id})

        try:
            model_version = await _run_stage(
                db, scan, job, stage=ScanStatus.PREPARING_MODEL, run_once=lambda: _stage_prepare_model(db), **stage_kwargs
            )
            # Resolved once per job run — the single dispatch point that
            # makes every stage below architecture-agnostic. A future third
            # architecture only needs a new adapter registered under its own
            # name; nothing from here on changes.
            adapter = adapter_registry.get_adapter(model_version.architecture)

            await transition(db, scan, ScanStatus.LOADING_MODEL, actor="system")
            await db.commit()
            loaded_model = await _run_stage(
                db,
                scan,
                job,
                stage=ScanStatus.LOADING_MODEL,
                run_once=lambda: _stage_load_model(model_version),
                **stage_kwargs,
            )

            await transition(db, scan, ScanStatus.AI_PREPROCESSING, actor="system")
            await db.commit()
            preprocess_result = await _run_stage(
                db,
                scan,
                job,
                stage=ScanStatus.AI_PREPROCESSING,
                run_once=lambda: _stage_preprocess(scan),
                **stage_kwargs,
            )

            await transition(db, scan, ScanStatus.FEATURE_EXTRACTION, actor="system")
            await db.commit()
            feature = await _run_stage(
                db,
                scan,
                job,
                stage=ScanStatus.FEATURE_EXTRACTION,
                run_once=lambda: _stage_extract_features(
                    preprocess_result.waveform,
                    extractor_name=model_version.feature_extractor_name,
                    extractor_version=model_version.feature_extractor_version,
                ),
                **stage_kwargs,
            )
            await _persist_feature_vector(db, scan, feature)

            await transition(db, scan, ScanStatus.RUNNING_INFERENCE, actor="system")
            await db.commit()
            inference_result = await _run_stage(
                db,
                scan,
                job,
                stage=ScanStatus.RUNNING_INFERENCE,
                run_once=lambda: _stage_infer(adapter, loaded_model, feature),
                **stage_kwargs,
            )

            await transition(db, scan, ScanStatus.POSTPROCESSING, actor="system")
            await db.commit()
            _, confidence_result = await _run_stage(
                db,
                scan,
                job,
                stage=ScanStatus.POSTPROCESSING,
                run_once=lambda: _stage_postprocess(inference_result, threshold=settings.AI_CONFIDENCE_THRESHOLD),
                **stage_kwargs,
            )

            await transition(db, scan, ScanStatus.GENERATING_EXPLANATION, actor="system")
            await db.commit()
            explanation_result = await _run_stage(
                db,
                scan,
                job,
                stage=ScanStatus.GENERATING_EXPLANATION,
                run_once=lambda: _stage_explain(
                    adapter,
                    loaded_model,
                    feature,
                    inference_result,
                    confidence_result,
                    silence_ratio=preprocess_result.silence.silence_ratio,
                    model_version_label=f"{model_version.name}:{model_version.version}",
                ),
                # Explanation degrades internally on failure (see
                # api.inference.explainability) rather than raising, so
                # there is nothing meaningful to retry — one attempt only.
                max_attempts=1,
                timeout_s=settings.AI_STAGE_TIMEOUT_S,
                correlation_id=correlation_id,
            )

            await transition(db, scan, ScanStatus.SAVING_RESULTS, actor="system")
            await db.commit()
            processing_time_ms = int((time.perf_counter() - pipeline_started) * 1000)
            await _run_stage(
                db,
                scan,
                job,
                stage=ScanStatus.SAVING_RESULTS,
                run_once=lambda: result_writer.persist_result(
                    db,
                    scan=scan,
                    model_version=model_version,
                    inference_result=inference_result,
                    confidence_result=confidence_result,
                    explanation_result=explanation_result,
                    feature_extractor_name=feature.name,
                    feature_extractor_version=feature.version,
                    processing_time_ms=processing_time_ms,
                ),
                **stage_kwargs,
            )

            await transition(db, scan, ScanStatus.COMPLETED, actor="system")
            if job is not None:
                job.status = "succeeded"
                job.finished_at = datetime.now(timezone.utc)
                await db.flush()
            await write_audit_log(
                db,
                event_type=AuditEventType.SCAN_PROCESSING_COMPLETED,
                outcome=AuditOutcome.SUCCESS,
                user_id=scan.user_id,
                details={
                    "scan_id": str(scan.id),
                    "verdict": confidence_result.verdict,
                    "processing_time_ms": processing_time_ms,
                },
            )
            await db.commit()
            logger.info(
                "ai_pipeline_completed",
                extra={
                    "scan_id": str(scan.id),
                    "correlation_id": correlation_id,
                    "verdict": confidence_result.verdict,
                    "processing_time_ms": processing_time_ms,
                },
            )
        except _PipelineAborted:
            return
        except Exception:
            # Last-resort safety net. Every *expected* failure mode already
            # exits through _run_stage's own except AIPipelineError/
            # asyncio.TimeoutError branch above (which records a
            # processing_failure row, retries, and on exhaustion transitions
            # the scan to its dedicated *_FAILED state) — this only fires for
            # a genuinely unanticipated exception type escaping a stage body
            # (e.g. api/inference/model_loader.py's now-fixed unguarded
            # `import torch`, or the next thing like it nobody's written yet).
            # Before this handler existed, that class of bug left the scan
            # (and its processing_jobs row) wedged at whatever status it was
            # last transitioned to — forever, since a FastAPI BackgroundTask
            # exception is never logged or retried by the framework and the
            # frontend has nothing to poll toward but a status that will
            # never change again. Catching Exception here is deliberately
            # broad: the goal isn't to handle any specific error, it's to
            # guarantee every scan reaches a terminal state and every failure
            # is visible in the logs, no matter what goes wrong inside a
            # stage body.
            #
            # rollback() must run *before* anything below touches `scan` or
            # `job` — whatever raised may have already left `db`'s
            # transaction DEACTIVE (e.g. a failed flush deeper in a stage),
            # and any ORM attribute access against a DEACTIVE transaction
            # (even a plain read of an already-loaded column, if the
            # instance's attributes were expired by an earlier operation)
            # raises sqlalchemy.exc.PendingRollbackError. That secondary
            # exception used to escape from *inside* this safety net itself,
            # defeating its one job: reproduced live via
            # test_pipeline_stage_timeout_is_recorded_and_retried, whose
            # traceback showed exactly this — a PendingRollbackError raised
            # out of the `extra={"scan_id": str(scan.id), ...}` logging call
            # below, before rollback() had run. `scan_id` (this function's
            # plain uuid.UUID argument, not the ORM-backed `scan.id`) is used
            # for every log line in this handler so nothing here ever depends
            # on session/transaction health before the rollback below.
            await db.rollback()
            logger.exception(
                "ai_pipeline_unhandled_exception",
                extra={"scan_id": str(scan_id), "correlation_id": correlation_id},
            )
            try:
                await db.refresh(scan)
            except Exception:
                # The row itself is unreachable post-rollback (e.g. deleted
                # concurrently) — nothing further here can safely touch
                # `scan`. The original failure is already logged above by
                # logger.exception (its traceback is preserved via
                # sys.exc_info(), untouched by the rollback/refresh attempts
                # in between); this is a distinct, secondary condition, and
                # is logged as its own event rather than allowed to propagate
                # and mask the original one.
                logger.error(
                    "ai_pipeline_could_not_refresh_scan_after_rollback",
                    extra={"scan_id": str(scan_id), "correlation_id": correlation_id},
                )
                return
            if job is not None:
                job.status = "failed"
                job.last_error = f"Unhandled exception — see server logs for correlation_id={correlation_id}"[:1024]
                job.finished_at = datetime.now(timezone.utc)
                await db.flush()
            failure_target = AI_STAGE_FAILURE_TARGET.get(scan.status)
            if failure_target is not None and can_transition(scan.status, failure_target):
                scan.error_code = "AI_PROCESSING_ERROR"
                scan.error_message = "An unexpected error occurred during analysis. Please try again."
                await transition(db, scan, failure_target, actor="system", reason="unhandled_exception")
            else:
                logger.error(
                    "ai_pipeline_could_not_auto_fail_scan",
                    extra={"scan_id": str(scan.id), "correlation_id": correlation_id, "status": scan.status.value},
                )
            await write_audit_log(
                db,
                event_type=AuditEventType.SCAN_PROCESSING_FAILED,
                outcome=AuditOutcome.FAILURE,
                user_id=scan.user_id,
                details={"scan_id": str(scan.id), "error_code": "AI_PROCESSING_ERROR", "unhandled": True},
            )
            await db.commit()
