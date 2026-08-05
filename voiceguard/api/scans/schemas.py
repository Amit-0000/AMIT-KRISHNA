from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from api.scans.models import Scan
from api.scans.state_machine import ScanStatus


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ScanStatus
    original_filename: str
    file_extension: str
    declared_mime_type: str | None
    file_size_bytes: int
    sha256_checksum: str
    duration_seconds: float | None
    scan_metadata: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    queued_at: datetime | None
    preprocessing_started_at: datetime | None
    ready_at: datetime | None
    completed_at: datetime | None
    failed_at: datetime | None
    cancelled_at: datetime | None
    expires_at: datetime | None

    @classmethod
    def from_scan(cls, scan: Scan) -> "ScanResponse":
        return cls.model_validate(scan)


class ScanStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ScanStatus
    error_code: str | None
    error_message: str | None
    updated_at: datetime

    @classmethod
    def from_scan(cls, scan: Scan) -> "ScanStatusResponse":
        return cls.model_validate(scan)


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
