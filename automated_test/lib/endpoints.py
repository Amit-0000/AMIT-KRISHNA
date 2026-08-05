"""Registry of every discovered VoiceGuard API endpoint, with its expected
access rule, used by every test category script. `/health` is excluded per
the DAST scope instructions.

access values:
  public      - no auth required, any caller
  auth        - any authenticated user (any role)
  auth_owner  - authenticated + must own the referenced resource (scan_id / notification_id)
  admin       - UserRole.ADMIN only
"""
from __future__ import annotations

ENDPOINTS = [
    # -- auth --
    {"method": "POST", "path": "/api/v1/auth/register", "access": "public"},
    {"method": "POST", "path": "/api/v1/auth/login", "access": "public"},
    {"method": "POST", "path": "/api/v1/auth/logout", "access": "public"},
    {"method": "POST", "path": "/api/v1/auth/refresh", "access": "public"},
    {"method": "POST", "path": "/api/v1/auth/verify-email", "access": "public"},
    {"method": "POST", "path": "/api/v1/auth/resend-verification", "access": "public"},
    {"method": "POST", "path": "/api/v1/auth/forgot-password", "access": "public"},
    {"method": "POST", "path": "/api/v1/auth/reset-password", "access": "public"},
    {"method": "GET", "path": "/api/v1/auth/oauth/google", "access": "public"},
    {"method": "GET", "path": "/api/v1/auth/oauth/google/callback", "access": "public"},
    {"method": "GET", "path": "/api/v1/auth/me", "access": "auth"},
    # -- user --
    {"method": "GET", "path": "/api/v1/user/profile", "access": "auth"},
    {"method": "PATCH", "path": "/api/v1/user/profile", "access": "auth"},
    {"method": "POST", "path": "/api/v1/user/change-password", "access": "auth"},
    # -- scans --
    {"method": "POST", "path": "/api/v1/scans", "access": "auth"},
    {"method": "GET", "path": "/api/v1/scans", "access": "auth"},
    {"method": "GET", "path": "/api/v1/scans/{scan_id}", "access": "auth_owner", "needs": "scan_id"},
    {"method": "GET", "path": "/api/v1/scans/{scan_id}/status", "access": "auth_owner", "needs": "scan_id"},
    {"method": "POST", "path": "/api/v1/scans/{scan_id}/cancel", "access": "auth_owner", "needs": "scan_id"},
    {"method": "DELETE", "path": "/api/v1/scans/{scan_id}", "access": "auth_owner", "needs": "scan_id"},
    # -- inference --
    {"method": "POST", "path": "/api/v1/scans/{scan_id}/process", "access": "auth_owner", "needs": "scan_id"},
    {"method": "GET", "path": "/api/v1/scans/{scan_id}/result", "access": "auth_owner", "needs": "scan_id"},
    {"method": "GET", "path": "/api/v1/scans/{scan_id}/technical", "access": "auth_owner", "needs": "scan_id"},
    {"method": "GET", "path": "/api/v1/scans/{scan_id}/explanation", "access": "auth_owner", "needs": "scan_id"},
    {"method": "GET", "path": "/api/v1/models", "access": "auth"},
    {"method": "GET", "path": "/api/v1/models/current", "access": "auth"},
    # -- sharing --
    {"method": "POST", "path": "/api/v1/scans/{scan_id}/share", "access": "auth_owner", "needs": "scan_id"},
    {"method": "DELETE", "path": "/api/v1/scans/{scan_id}/share", "access": "auth_owner", "needs": "scan_id"},
    {"method": "GET", "path": "/api/v1/scans/shared/{token}", "access": "public", "needs": "share_token"},
    # -- notifications --
    {"method": "GET", "path": "/api/v1/notifications", "access": "auth"},
    {"method": "GET", "path": "/api/v1/notifications/unread-count", "access": "auth"},
    {"method": "PATCH", "path": "/api/v1/notifications/{notification_id}/read", "access": "auth_owner", "needs": "notification_id"},
    {"method": "POST", "path": "/api/v1/notifications/mark-all-read", "access": "auth"},
    {"method": "DELETE", "path": "/api/v1/notifications/{notification_id}", "access": "auth_owner", "needs": "notification_id"},
    # -- feedback --
    {"method": "POST", "path": "/api/v1/feedback", "access": "public"},
    {"method": "GET", "path": "/api/v1/feedback", "access": "admin"},
    # -- dashboard --
    {"method": "GET", "path": "/api/v1/dashboard", "access": "auth"},
    {"method": "GET", "path": "/api/v1/dashboard/recent-scans", "access": "auth"},
    # -- top-level legacy inference endpoint (no /api/v1 prefix) --
    # Was "public" with zero rate limit (HIGH finding, cost-abuse/DoS) until
    # fixed in api/main.py: now requires auth + a dedicated 30/hr/user limit.
    {"method": "POST", "path": "/predict", "access": "auth"},
]


def fill_path(path: str, *, scan_id=None, notification_id=None, share_token=None) -> str:
    p = path
    if scan_id is not None:
        p = p.replace("{scan_id}", str(scan_id))
    if notification_id is not None:
        p = p.replace("{notification_id}", str(notification_id))
    if share_token is not None:
        p = p.replace("{token}", str(share_token))
    return p
