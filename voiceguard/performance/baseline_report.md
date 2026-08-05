# VoiceGuard Baseline Load Test Report

Generated: 2026-08-05T20:19:34.858141+00:00

## Overall Performance

| Metric | Value |
| --- | --- |
| Virtual Users | 100 |
| Duration S | 59.2 |
| Total Requests | 4855 |
| Successful Requests | 4163 |
| Failed Requests | 692 |
| Requests Per Second | 81.98 |
| Avg Response Time Ms | 61.09 |
| Median Response Time Ms | 9.95 |
| Min Response Time Ms | 2.42 |
| Max Response Time Ms | 1403.85 |
| P90 Response Time Ms | 96.88 |
| P95 Response Time Ms | 270.99 |
| P99 Response Time Ms | 1035.91 |
| Error Rate Pct | 14.25 |
| Success Rate Pct | 85.75 |
| Data Sent Bytes | None |
| Data Received Bytes | None |

## Endpoint Performance

| Endpoint | Method | Requests | Avg (ms) | P95 (ms) | P99 (ms) | Success % |
| --- | --- | --- | --- | --- | --- | --- |
| GET /api/v1/scans | GET | 1986 | 50.49 | 221.16 | 1003.59 | 100.0 |
| GET /api/v1/scans/{id} | GET | 887 | 38.07 | 116.39 | 819.76 | 100.0 |
| GET /api/v1/user/profile | GET | 1190 | 47.34 | 209.84 | 1006.45 | 100.0 |
| POST /api/v1/auth/login | POST | 100 | 313.97 | 812.14 | 1102.85 | 100.0 |
| POST /api/v1/scans | POST | 692 | 108.13 | 522.6 | 1146.77 | 0.0 |

## HTTP Status Codes

| Status | Count | % |
| --- | --- | --- |
| 200 | 4163 | 85.75 |
| 409 | 583 | 12.01 |
| 429 | 109 | 2.25 |

## Response Time Distribution

| Range (ms) | Count |
| --- | --- |
| 0-50 | 4030 |
| 51-100 | 338 |
| 101-200 | 108 |
| 201-500 | 193 |
| 501-1000 | 114 |
| 1000+ | 60 |

## Resource Usage Summary

| Container | Avg CPU % | Max CPU % | Avg Mem (MB) | Max Mem (MB) |
| --- | --- | --- | --- | --- |
| voiceguard-backend-1 | 52.12 | 239.39 | 260.49 | 261.7 |
| voiceguard-postgres-1 | 9.73 | 66.73 | 82.34 | 85.04 |
| voiceguard-redis-1 | 0.43 | 0.57 | 10.17 | 10.98 |
| voiceguard-frontend-1 | 6.15 | 8.07 | 107.5 | 108.2 |
