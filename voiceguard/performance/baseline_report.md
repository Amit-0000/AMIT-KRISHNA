# VoiceGuard Baseline Load Test Report

Generated: 2026-08-06T10:48:05.163729+00:00

## Overall Performance

| Metric | Value |
| --- | --- |
| Virtual Users | 100 |
| Duration S | 59.3 |
| Total Requests | 4919 |
| Successful Requests | 4919 |
| Failed Requests | 0 |
| Requests Per Second | 82.93 |
| Avg Response Time Ms | 45.55 |
| Median Response Time Ms | 6.67 |
| Min Response Time Ms | 2.31 |
| Max Response Time Ms | 1298.29 |
| P90 Response Time Ms | 87.8 |
| P95 Response Time Ms | 241.69 |
| P99 Response Time Ms | 791.93 |
| Error Rate Pct | 0.0 |
| Success Rate Pct | 100.0 |
| Data Sent Bytes | 10211253 |
| Data Received Bytes | 6858033 |

## Endpoint Performance

| Endpoint | Method | Requests | Avg (ms) | P95 (ms) | P99 (ms) | Success % |
| --- | --- | --- | --- | --- | --- | --- |
| GET /api/v1/scans | GET | 2063 | 31.75 | 118.14 | 632.9 | 100.0 |
| GET /api/v1/scans/{id} | GET | 821 | 35.25 | 131.5 | 771.5 | 100.0 |
| GET /api/v1/user/profile | GET | 1460 | 33.27 | 143.21 | 740.78 | 100.0 |
| POST /api/v1/auth/login | POST | 100 | 261.47 | 406.21 | 464.93 | 100.0 |
| POST /api/v1/scans | POST | 475 | 115.55 | 536.98 | 1097.97 | 100.0 |

## HTTP Status Codes

| Status | Count | % |
| --- | --- | --- |
| 200 | 4444 | 90.34 |
| 201 | 475 | 9.66 |

## Response Time Distribution

| Range (ms) | Count |
| --- | --- |
| 0-50 | 4237 |
| 51-100 | 215 |
| 101-200 | 129 |
| 201-500 | 233 |
| 501-1000 | 82 |
| 1000+ | 11 |

## Resource Usage Summary

| Container | Avg CPU % | Max CPU % | Avg Mem (MB) | Max Mem (MB) |
| --- | --- | --- | --- | --- |
| voiceguard-backend-1 | 52.12 | 239.39 | 260.49 | 261.7 |
| voiceguard-postgres-1 | 9.73 | 66.73 | 82.34 | 85.04 |
| voiceguard-redis-1 | 0.43 | 0.57 | 10.17 | 10.98 |
| voiceguard-frontend-1 | 6.15 | 8.07 | 107.5 | 108.2 |
