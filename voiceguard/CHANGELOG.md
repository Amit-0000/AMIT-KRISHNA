# Changelog

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project does not
yet use semantic version tags — entries are grouped by release milestone.

## [Unreleased] — Public release hardening

Preparation for the first public GitHub release. No product functionality, API behavior, or
model behavior changed in this pass — every change below is documentation, CI/security-hardening,
or repository cleanup.

### Added
- Rewrote `README.md` to document the actual VoiceGuard platform (it previously described the
  original upstream research project this repo was forked from).
- Three GitHub Actions workflows at the correct repository root (`.github/workflows/`):
  `backend.yml` (lint + pytest + coverage), `frontend.yml` (lint + typecheck + build), `docker.yml`
  (build sanity check for `api/Dockerfile.ml`).
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `DEPLOYMENT.md`, `API_OVERVIEW.md`,
  this `CHANGELOG.md`.
- Root-level `.gitignore` (previously only `voiceguard/` and `automated_test/` had one).

### Changed
- `app.py` / `demo/app.py` no longer hardcode a third-party HuggingFace Hub repo as the model
  source. They now prefer a local checkpoint (`checkpoints/best.pt`, same file the API uses) and
  fall back to an optional `HF_MODEL_REPO` environment variable.

### Fixed
- **Security**: every `torch.load()` call in the repository now uses `weights_only=True`
  (previously present in the newer `api/inference/` adapter code, but missing from the original
  vendored `src/inference/predict.py` and several training/evaluation scripts — see
  `Release_Readiness_Report.md` for the full list and verification method). This closes finding
  F-01 in `Vulnerability Test Results/security_review.md`.

### Removed
- Internal planning/audit documents that don't belong in a public release: `fork_rebrand_guide.txt`,
  `NEXT_STEPS.md`, `REPOSITORY_AUDIT_REPORT.txt`, the `BATCH_0*_*.txt` architecture specs,
  `VOICEGUARD_PRODUCT_ARCHITECTURE.md`, `audio_deepfake_detector.md`.
- The broken `sync_to_hf.yml` GitHub Actions workflow (it also lived at the wrong path —
  `voiceguard/.github/workflows/` — so it had never actually been runnable by GitHub Actions in
  this repository's layout).
- `.DS_Store` (tracked by accident).

---

## Platform build (this repository's git history)

The commits below represent the actual application build, in the order they landed. Grouped here
for readability; see `git log` for the authoritative record.

### Backend platform
- Repository hygiene: stopped tracking `node_modules`, expanded `.gitignore`
- Backend foundation: core infrastructure, authentication, user profiles
- Scan upload and lifecycle management
- AI processing pipeline with pluggable multi-model inference (LCNN + a second architecture)
- Notifications, feedback (submission + admin review), result sharing via public tokens,
  usage dashboard
- Full FastAPI router wiring

### Frontend
- Authentication pages (login, signup, password reset, email verification)
- Scan, dashboard, notifications, feedback, and sharing UI

### ML / training
- Fixed a train/serve preprocessing mismatch (training previously skipped a peak-normalize +
  silence-trim step the live API applies)
- LCNN reproducibility improvements: seeding, resume, mixed precision, experiment tracking
- ASVspoof 2019 dataset integrity audit
- LCNN class-imbalance and data-augmentation ablation experiments
- AudioCNN trained and benchmarked against LCNN
- RawNet2 feasibility/readiness assessment (documentation only — not deployed)

### Performance & security
- Load-testing harness and a real before/after performance fix (root cause: synchronous bcrypt
  hashing blocking the event loop under load — see `performance/performance_fix_report.md` for
  the full writeup and measured impact)
- **Security fix**: the legacy `/predict` endpoint had no authentication and no rate limiting,
  allowing unlimited unauthenticated CPU-bound inference calls. Fixed to require authentication
  and enforce a per-user rate limit, verified with a 227-check DAST regression harness (0 findings)
