# Security Policy

## Reporting a vulnerability

Please **do not** open a public GitHub issue for a security vulnerability.

Use GitHub's private vulnerability reporting instead: go to this repository's **Security** tab →
**Report a vulnerability**. This opens a private advisory visible only to the maintainer until a
fix is ready.

If private reporting isn't available for this repository, open an issue asking the maintainer to
enable it, without describing the vulnerability itself.

Please include:
- A description of the issue and its potential impact
- Steps to reproduce (a minimal example is ideal)
- Any suggested fix, if you have one

## What's already been reviewed

This project has an internal security review (`Vulnerability Test Results/security_review.md`)
and an automated DAST regression harness (`automated_test/`, 227 checks across authentication
bypass, RBAC, IDOR, token tampering, injection, rate limiting, and hardcoded-credential
scanning — currently 0 findings). Known, tracked limitations that are **not** considered
vulnerabilities (already documented, with rationale) are listed in
`Release_Readiness_Report.md`.

## Scope

In scope:
- The FastAPI backend (`api/`)
- The React frontend (`frontend/`)
- The model-loading and inference pipeline (`src/`, `api/inference/`)
- Docker/Compose configuration

Out of scope:
- Third-party dependencies (report upstream) — though we do want to know if a dependency is
  pinned to a version with a known CVE; that's fair to report here.
- The training/evaluation scripts under `scripts/`, when run against your own local data —
  these aren't network-facing.

## Supported versions

This project does not yet have a formal release/support cadence — security fixes land on `main`.
See `CHANGELOG.md` for what's shipped.

## Disclosure

We'll acknowledge reports within a reasonable timeframe, work with you on a fix, and credit you
in the fix's changelog entry (unless you'd prefer to stay anonymous).
