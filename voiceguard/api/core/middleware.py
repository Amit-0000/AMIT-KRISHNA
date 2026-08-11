from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from api.core.config import get_settings

logger = logging.getLogger("voiceguard.request")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request_id (reusing an inbound X-Request-ID if present),
    stores it on request.state for exception handlers and audit logging, and
    emits one structured log line per request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds standard security response headers (security-review.md F-20 —
    confirmed live that none of these were present on any response). CSP is
    deliberately minimal/permissive-by-default here since this middleware
    protects the JSON API responses themselves (clickjacking/MIME-sniffing/
    protocol-downgrade), not a server-rendered HTML surface with inline
    scripts/styles to fingerprint — the SPA frontend is a separate app and
    should carry its own, tighter CSP suited to its actual asset origins."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        if get_settings().is_production:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


def client_ip(request: Request) -> str:
    """Trusts X-Forwarded-For only when the immediate TCP peer is in
    Settings.TRUSTED_PROXY_IPS; falls back to the raw peer address otherwise
    (BATCH_04 S11.6 IP extraction rules).

    Previously this trusted the header from *any* caller, which let a client
    spoof a fresh rate-limit bucket on every request by sending a different
    X-Forwarded-For value — confirmed via live exploitation in
    security-review.md F-14 (15/15 spoofed-IP login attempts bypassed the
    10/hour limit that correctly blocks a real single IP). TRUSTED_PROXY_IPS
    is empty by default (no reverse proxy in front of this app in the
    current docker-compose topology), so the header is never trusted unless
    a real deployment explicitly lists its actual proxy IP(s)."""
    peer = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and peer in get_settings().trusted_proxy_ips_list:
        return forwarded.split(",")[0].strip()
    return peer
