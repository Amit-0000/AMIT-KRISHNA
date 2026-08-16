from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from api.inference.models import ModelVersion, ScanResult


class ScanResultResponse(BaseModel):
    """User-facing result — GET /scans/{id}/result. Mirrors
    frontend/src/types/index.ts's pre-existing `ScanResult`/`Verdict` shape
    where the two overlap (verdict, confidence, inference_time_ms,
    model_version) — that type was scaffolded ahead of this slice
    specifically for it."""

    scan_id: uuid.UUID
    verdict: str
    confidence: float
    model_version: str
    processing_time_ms: int
    inference_time_ms: int
    created_at: datetime
    # "clean" | "malicious" | "unavailable" | "not_scanned" | null — carried
    # over from Scan.malware_scan_status, deliberately separate from `verdict`
    # (the AI's own opinion about the audio). A scan can only ever reach this
    # endpoint with "clean" or "not_scanned" here (MALICIOUS/UNAVAILABLE+
    # required both reject the upload before an AI result can exist) — see
    # api.scans.service.create_scan.
    malware_scan_status: str | None

    @classmethod
    def from_result(
        cls, result: ScanResult, model_version: ModelVersion, malware_scan_status: str | None
    ) -> "ScanResultResponse":
        return cls(
            scan_id=result.scan_id,
            verdict=result.verdict,
            confidence=result.confidence,
            model_version=f"{model_version.name}:{model_version.version}",
            processing_time_ms=result.processing_time_ms,
            inference_time_ms=result.inference_time_ms,
            created_at=result.created_at,
            malware_scan_status=malware_scan_status,
        )


class StageTimingEntry(BaseModel):
    stage: str
    attempt: int
    status: str
    duration_ms: int


class ScanTechnicalResponse(BaseModel):
    """Full technical detail — GET /scans/{id}/technical. Everything
    ScanResultResponse omits: raw scores, threshold, feature/model
    provenance, per-stage timing (Processing Metrics)."""

    scan_id: uuid.UUID
    label: str
    verdict: str
    confidence: float
    raw_bonafide_score: float
    raw_spoof_score: float
    threshold_used: float
    is_below_threshold: bool
    feature_extractor_name: str
    feature_extractor_version: str
    model_name: str
    model_version: str
    model_architecture: str
    processing_time_ms: int
    inference_time_ms: int
    stage_timings: list[StageTimingEntry]
    created_at: datetime

    @classmethod
    def from_result(
        cls, result: ScanResult, model_version: ModelVersion, stage_timings: list[StageTimingEntry]
    ) -> "ScanTechnicalResponse":
        return cls(
            scan_id=result.scan_id,
            label=result.label,
            verdict=result.verdict,
            confidence=result.confidence,
            raw_bonafide_score=result.raw_bonafide_score,
            raw_spoof_score=result.raw_spoof_score,
            threshold_used=result.threshold_used,
            is_below_threshold=result.is_below_threshold,
            feature_extractor_name=result.feature_extractor_name,
            feature_extractor_version=result.feature_extractor_version,
            model_name=model_version.name,
            model_version=model_version.version,
            model_architecture=model_version.architecture,
            processing_time_ms=result.processing_time_ms,
            inference_time_ms=result.inference_time_ms,
            stage_timings=stage_timings,
            created_at=result.created_at,
        )


class SalientRegionResponse(BaseModel):
    start_s: float
    end_s: float
    importance: float


class ScanExplanationResponse(BaseModel):
    scan_id: uuid.UUID
    salient_regions: list[SalientRegionResponse]
    notes: list[str]
    warnings: list[str]
    feature_extractor: str
    model_version: str

    @classmethod
    def from_result(cls, result: ScanResult) -> "ScanExplanationResponse":
        explanation = result.explanation or {}
        return cls(
            scan_id=result.scan_id,
            salient_regions=[SalientRegionResponse(**r) for r in explanation.get("salient_regions", [])],
            notes=explanation.get("notes", []),
            warnings=explanation.get("warnings", []),
            feature_extractor=explanation.get("feature_extractor", ""),
            model_version=explanation.get("model_version", ""),
        )


class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    version: str
    architecture: str
    status: str
    feature_extractor_name: str
    feature_extractor_version: str
    loaded_at: datetime | None
    created_at: datetime


class ProcessResponse(BaseModel):
    scan_id: uuid.UUID
    status: str
