"""add_macro_results table

Revision ID: e8a9b0c1d2e3
Revises: d6e7f8a9b0c1 (sentiment)
Create Date: 2026-11-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e8a9b0c1d2e3"
down_revision: Union[str, None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "macro_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analytics_run_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_type", sa.String(length=30), nullable=False),
        sa.Column("series_id", sa.String(length=30), nullable=False),
        sa.Column("value", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("period", sa.String(length=20), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analytics_run_id"], ["analytics_runs.id"]),
    )
    op.create_index(
        "ix_macro_results_analytics_run_id",
        "macro_results",
        ["analytics_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_macro_results_analytics_run_id", table_name="macro_results")
    op.drop_table("macro_results")
