# VoiceGuard Baseline Load Test Report

Generated: 2026-07-31T08:26:50.175549+00:00

## Overall Performance

| Metric | Value |
| --- | --- |
| Virtual Users | 100 |
| Duration S | 59.2 |
| Total Requests | 4358 |
| Successful Requests | 3756 |
| Failed Requests | 602 |
| Requests Per Second | 73.58 |
| Avg Response Time Ms | 176.68 |
| Median Response Time Ms | 17.9 |
| Min Response Time Ms | 2.17 |
| Max Response Time Ms | 2091.72 |
| P90 Response Time Ms | 744.93 |
| P95 Response Time Ms | 1276.14 |
| P99 Response Time Ms | 1628.81 |
| Error Rate Pct | 13.81 |
| Success Rate Pct | 86.19 |
| Data Sent Bytes | 13067619 |
| Data Received Bytes | 7246798 |

## Endpoint Performance

| Endpoint | Method | Requests | Avg (ms) | P95 (ms) | P99 (ms) | Success % |
| --- | --- | --- | --- | --- | --- | --- |
| GET /api/v1/scans | GET | 1779 | 153.65 | 1183.58 | 1520.47 | 100.0 |
| GET /api/v1/scans/{id} | GET | 726 | 160.11 | 1277.42 | 1586.91 | 100.0 |
| GET /api/v1/user/profile | GET | 1087 | 143.98 | 1106.31 | 1523.31 | 100.0 |
| POST /api/v1/auth/login | POST | 100 | 323.53 | 399.91 | 454.99 | 100.0 |
| POST /api/v1/scans | POST | 666 | 287.57 | 1629.63 | 1877.84 | 9.61 |

## HTTP Status Codes

| Status | Count | % |
| --- | --- | --- |
| 200 | 3692 | 84.72 |
| 201 | 64 | 1.47 |
| 409 | 602 | 13.81 |

## Response Time Distribution

| Range (ms) | Count |
| --- | --- |
| 0-50 | 3156 |
| 51-100 | 296 |
| 101-200 | 141 |
| 201-500 | 201 |
| 501-1000 | 227 |
| 1000+ | 319 |

## Resource Usage Summary

| Container | Avg CPU % | Max CPU % | Avg Mem (MB) | Max Mem (MB) |
| --- | --- | --- | --- | --- |
| voiceguard-backend-1 | 78.19 | 327.7 | 83.3 | 87.27 |
| voiceguard-postgres-1 | 25.55 | 136.46 | 85.73 | 183.0 |
| voiceguard-redis-1 | 0.72 | 3.12 | 11.17 | 11.44 |
| voiceguard-frontend-1 | 9.3 | 12.56 | 107.83 | 108.4 |
