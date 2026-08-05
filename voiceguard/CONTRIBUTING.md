# Contributing to VoiceGuard

Thanks for considering a contribution. This document covers how to get a working dev
environment, what's expected of a change, and how to submit it.

## Getting set up

The fastest path is Docker Compose — see the main [README](README.md#docker-setup-recommended).
For working on a single component without the full stack:

- **Backend**: see [README → Backend only](README.md#running-locally). Tests run against an
  in-memory SQLite engine and a fake Redis double — no external services required.
- **Frontend**: `cd frontend && npm install && npm run dev`.
- **ML / training**: see [README → ML Models](README.md#ml-models) and `docs/` for the research
  write-up (dataset, architecture, training, evaluation, explainability, serving).

## Before opening a PR

- **Backend**: run `pytest` from `voiceguard/api/` and make sure it's green. If you're touching
  `api/core/security.py`, `api/core/rate_limit.py`, auth, or anything in the AI pipeline's model
  loading path, call that out explicitly in your PR description — those are the
  security-sensitive surfaces.
- **Frontend**: run `npm run lint` and `npm run build` (which also typechecks via `tsc -b`) from
  `voiceguard/frontend/`. There is currently no frontend automated test suite — see
  [Roadmap](README.md#roadmap); adding one is a welcome contribution.
- Both are also checked in CI on every PR (`.github/workflows/backend.yml`,
  `.github/workflows/frontend.yml`).

## Code style

- Backend: no enforced formatter yet. `ruff check` runs in CI in report-only mode (won't fail
  your PR) while a style baseline is established — please don't mass-reformat unrelated files in
  an unrelated PR.
- Frontend: ESLint config is enforced (`npm run lint` fails on violations).
- Match the surrounding code's conventions in whichever file you're editing, especially around
  comments: this codebase prefers comments that explain *why* a non-obvious decision was made
  over comments that restate *what* the code does.

## Security-sensitive changes

If you're fixing a vulnerability rather than adding a feature, please read `SECURITY.md` first —
don't open a public PR for an unreported, unfixed vulnerability.

## Commit messages

This repo uses [Conventional Commits](https://www.conventionalcommits.org/)
(`feat:`, `fix:`, `docs:`, `chore:`, `ci:`, `test:`, …). Keep unrelated changes in separate
commits/PRs.

## Database migrations

Schema changes go through Alembic (`api/alembic/versions/`). Generate a new revision with
`alembic -c api/alembic.ini revision --autogenerate -m "..."` run from `voiceguard/`, then review
the generated migration by hand before committing it — autogenerate is a starting point, not a
guarantee of correctness.

## Questions

Open an issue, or start a discussion if the repository has Discussions enabled.
