# VoiceGuard Baseline Load Test Report

Generated: 2026-07-31T03:40:52.047031+00:00

## Overall Performance

| Metric | Value |
| --- | --- |
| Virtual Users | 100 |
| Duration S | 60.8 |
| Total Requests | 1517 |
| Successful Requests | 19 |
| Failed Requests | 1498 |
| Requests Per Second | 24.95 |
| Avg Response Time Ms | 1736.9 |
| Median Response Time Ms | 1.74 |
| Min Response Time Ms | 0.75 |
| Max Response Time Ms | 59997.99 |
| P90 Response Time Ms | 60.76 |
| P95 Response Time Ms | 30006.9 |
| P99 Response Time Ms | 32340.68 |
| Error Rate Pct | 98.75 |
| Success Rate Pct | 1.25 |
| Data Sent Bytes | 3670929 |
| Data Received Bytes | 478960 |

## Endpoint Performance

| Endpoint | Method | Requests | Avg (ms) | P95 (ms) | P99 (ms) | Success % |
| --- | --- | --- | --- | --- | --- | --- |
| GET /api/v1/scans | GET | 828 | 143.43 | 31.04 | 828.44 | 0.6 |
| GET /api/v1/scans/{id} | GET | 22 | 33.39 | 254.45 | 396.86 | 0.0 |
| GET /api/v1/user/profile | GET | 371 | 102.62 | 52.36 | 579.09 | 0.27 |
| POST /api/v1/auth/login | POST | 84 | 29076.37 | 35172.63 | 59997.36 | 15.48 |
| POST /api/v1/scans | POST | 212 | 164.59 | 19.19 | 825.35 | 0.0 |

## HTTP Status Codes

| Status | Count | % |
| --- | --- | --- |
| 0 | 3 | 0.2 |
| 200 | 19 | 1.25 |
| 401 | 1424 | 93.87 |
| 500 | 71 | 4.68 |

## Response Time Distribution

| Range (ms) | Count |
| --- | --- |
| 0-50 | 1362 |
| 51-100 | 8 |
| 101-200 | 12 |
| 201-500 | 15 |
| 501-1000 | 26 |
| 1000+ | 94 |

## Resource Usage Summary

| Container | Avg CPU % | Max CPU % | Avg Mem (MB) | Max Mem (MB) |
| --- | --- | --- | --- | --- |
| voiceguard-backend-1 | 19.81 | 99.46 | 84.05 | 85.17 |
| voiceguard-postgres-1 | 1.23 | 15.31 | 87.06 | 99.55 |
| voiceguard-redis-1 | 0.47 | 0.58 | 10.29 | 10.91 |
| voiceguard-frontend-1 | 8.05 | 9.45 | 53.55 | 54.16 |
