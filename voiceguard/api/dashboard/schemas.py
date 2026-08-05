from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_serializer


class DashboardStatsResponse(BaseModel):
    total_scans: int
    ai_detected: int
    human_verified: int
    uncertain: int
    avg_processing_ms: int
    scans_today: int
    scan_limit_daily: int
    reset_in_hours: int


class TrendPointResponse(BaseModel):
    date: str
    total: int
    ai_generated: int
    human: int
    uncertain: int


class ConfidenceBucketResponse(BaseModel):
    range: str
    min: int
    max: int
    count: int
    zone: str


class ActivityItemResponse(BaseModel):
    id: str
    type: str
    title: str
    description: str
    timestamp: str
    verdict: str | None = None
    scan_id: str | None = None


class ModelStatusResponse(BaseModel):
    """Only fields backed by real, currently-tracked data are populated.
    eer_pct/uptime_pct/parameters have no real data source in this stack
    (EER is an offline evaluation metric, there is no uptime-monitoring
    subsystem, and counting parameters would mean loading model weights on
    every dashboard request) — they're left None rather than fabricated;
    see frontend/src/pages/Dashboard/components/ModelStatusCard.tsx, which
    was updated to skip rendering a stat row when its value is None."""

    version: str
    health: str
    avg_inference_ms: int | None
    last_checked: datetime
    eer_pct: float | None = None
    uptime_pct: float | None = None
    parameters: int | None = None

    @field_serializer("last_checked")
    def _serialize_last_checked(self, value: datetime) -> str:
        return value.isoformat()


class DashboardResponse(BaseModel):
    stats: DashboardStatsResponse
    trend: list[TrendPointResponse]
    confidence_distribution: list[ConfidenceBucketResponse]
    recent_activity: list[ActivityItemResponse]
    model_status: ModelStatusResponse


class RecentScanResponse(BaseModel):
    scan_id: str
    status: str
    verdict: str
    confidence: float
    human_score: float
    ai_score: float
    inference_time_ms: int
    model_version: str
    segment_count: int
    frequency_heatmap: str | None
    file_name: str
    file_duration_seconds: float | None
    created_at: str
    share_token: str | None
    user_verdict: str | None
