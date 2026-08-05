"""Add the AI Processing Pipeline's ScanStatus values to the Postgres
`scan_status` enum type.

Migration 0003 added the AI slice's new tables but never extended the
`scan_status` enum TYPE itself with the 14 new states api.scans.state_machine
gained in that same slice (PREPARING_MODEL .. RESULT_PERSISTENCE_FAILED).
SQLite (used by the test suite) doesn't enforce enum membership at the
database level the way Postgres does, so `Base.metadata.create_all()` in
tests never caught this — every write of a new status value against a real
Postgres database fails with `invalid input value for enum scan_status`
until this migration runs. Discovered during manual end-to-end testing
against the dockerized Postgres instance.

Revision ID: 0004_scan_status_enum_values
Revises: 0003_ai_processing_pipeline
Create Date: 2026-07-29

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004_scan_status_enum_values"
down_revision: Union[str, None] = "0003_ai_processing_pipeline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Must match ScanStatus's .value strings exactly (api.scans.state_machine),
# in the same order they appear there.
_NEW_VALUES = (
    "preparing_model",
    "loading_model",
    "ai_preprocessing",
    "feature_extraction",
    "running_inference",
    "postprocessing",
    "generating_explanation",
    "saving_results",
    "model_load_failed",
    "ai_preprocessing_failed",
    "feature_extraction_failed",
    "inference_failed",
    "postprocessing_failed",
    "result_persistence_failed",
)


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside the same transaction as a
    # statement that *uses* the new value (PG restriction), but running one
    # ADD VALUE per statement, each in its own implicit transaction, is safe
    # on Postgres 12+ (this stack runs postgres:16-alpine). IF NOT EXISTS
    # makes this migration safe to re-run against a partially-migrated DB.
    with op.get_context().autocommit_block():
        for value in _NEW_VALUES:
            op.execute(f"ALTER TYPE scan_status ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enum types — removing a value requires
    # rebuilding the type (create a new type, cast every dependent column,
    # drop the old type) and rejecting it outright if any row still uses one
    # of these values. Not implemented: no code path in this slice needs to
    # downgrade past 0003 in a database that has ever run the AI pipeline.
    raise NotImplementedError(
        "Cannot downgrade: Postgres does not support removing enum values. "
        "Rebuilding the scan_status type would require rewriting api/inference/**"
        "and every row currently in one of the new states."
    )
