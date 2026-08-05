# API Overview

Interactive, always-current documentation is served by FastAPI itself at `/docs` (Swagger UI) and
`/redoc` once the backend is running. This document is a stable, human-readable map of the same
surface — the authoritative list this was built from is
`automated_test/lib/endpoints.py`, the same list the DAST regression harness verifies access
control against.

All routes are under `/api/v1` unless noted. Access levels: **public** (no auth), **auth** (any
authenticated user), **auth\_owner** (authenticated + must own the resource), **admin**.

## Auth (`/auth`)
| Method | Path | Access |
|---|---|---|
| POST | `/auth/register` | public |
| POST | `/auth/login` | public |
| POST | `/auth/logout` | public |
| POST | `/auth/refresh` | public |
| POST | `/auth/verify-email` | public |
| POST | `/auth/resend-verification` | public |
| POST | `/auth/forgot-password` | public |
| POST | `/auth/reset-password` | public |
| GET | `/auth/oauth/google` | public |
| GET | `/auth/oauth/google/callback` | public |
| GET | `/auth/me` | auth |

## User (`/user`)
| Method | Path | Access |
|---|---|---|
| GET | `/user/profile` | auth |
| PATCH | `/user/profile` | auth |
| POST | `/user/change-password` | auth |

## Scans (`/scans`)
| Method | Path | Access |
|---|---|---|
| POST | `/scans` | auth |
| GET | `/scans` | auth |
| GET | `/scans/{scan_id}` | auth_owner |
| GET | `/scans/{scan_id}/status` | auth_owner |
| POST | `/scans/{scan_id}/cancel` | auth_owner |
| DELETE | `/scans/{scan_id}` | auth_owner |

## AI inference (`/scans/{scan_id}/*`, `/models`)
| Method | Path | Access |
|---|---|---|
| POST | `/scans/{scan_id}/process` | auth_owner |
| GET | `/scans/{scan_id}/result` | auth_owner |
| GET | `/scans/{scan_id}/technical` | auth_owner |
| GET | `/scans/{scan_id}/explanation` | auth_owner |
| GET | `/models` | auth |
| GET | `/models/current` | auth |

## Sharing (`/scans/{scan_id}/share`, `/scans/shared`)
| Method | Path | Access |
|---|---|---|
| POST | `/scans/{scan_id}/share` | auth_owner |
| DELETE | `/scans/{scan_id}/share` | auth_owner |
| GET | `/scans/shared/{token}` | public |

## Notifications (`/notifications`)
| Method | Path | Access |
|---|---|---|
| GET | `/notifications` | auth |
| GET | `/notifications/unread-count` | auth |
| PATCH | `/notifications/{notification_id}/read` | auth_owner |
| POST | `/notifications/mark-all-read` | auth |
| DELETE | `/notifications/{notification_id}` | auth_owner |

## Feedback (`/feedback`)
| Method | Path | Access |
|---|---|---|
| POST | `/feedback` | public |
| GET | `/feedback` | admin |

## Dashboard (`/dashboard`)
| Method | Path | Access |
|---|---|---|
| GET | `/dashboard` | auth |
| GET | `/dashboard/recent-scans` | auth |

## Legacy top-level endpoint (no `/api/v1` prefix)
| Method | Path | Access |
|---|---|---|
| POST | `/predict` | auth *(+ 30/hr/user rate limit)* |

Pre-dates the `/scans` pipeline; kept for single-shot inference without creating a scan record.
Previously had **no** authentication and **no** rate limiting — see the isolated
`fix(security): protect legacy /predict endpoint...` commit and
`Vulnerability Test Results/security_review.md` findings F-03/F-04.

## Response envelope

Every success response is wrapped as `{"data": <payload>}` (paginated list endpoints add a
sibling `"meta"` with pagination info — see `api/core/responses.py`). Every error response is
`{"error": {"code": "...", "message": "...", "field": "...", "details": [...]}}` — see
`api/core/exceptions.py`'s registered handlers for the full set of error codes.

## Rate limiting

Per-route limits (login, register, password reset/verification-resend, scan creation, `/predict`)
are enforced via Redis fixed-hour-bucket counters, keyed by IP for pre-auth routes and by user ID
for authenticated ones. Defaults live in `api/.env.example` (`RATE_LIMIT_*` variables) and are
overridable per deployment.
