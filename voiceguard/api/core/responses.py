from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


def success_envelope(data: Any, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    envelope: dict[str, Any] = {"data": data}
    if meta is not None:
        envelope["meta"] = meta
    return envelope


def error_envelope(
    *,
    code: str,
    message: str,
    request_id: str,
    details: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message, "request_id": request_id}
    if details:
        error["details"] = details
    return {"error": error}


def json_success(
    data: Any,
    *,
    status_code: int = 200,
    meta: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(status_code=status_code, content=success_envelope(data, meta=meta), headers=headers)
