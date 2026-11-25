"""add_correlation_results

Revision ID: 8f3a2d91c4b5
Revises: d2dcc981c45c
Create Date: 2026-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8f3a2d91c4b5"
down_revision: Union[str, None] = "d2dcc981c45c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "correlation_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analytics_run_id", sa.Uuid(), nullable=False),
        sa.Column("asset_a_id", sa.Uuid(), nullable=False),
        sa.Column("asset_b_id", sa.Uuid(), nullable=False),
        sa.Column("correlation_value", sa.Numeric(precision=20, scale=10), nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=True),
        sa.Column("observation_period", sa.String(length=30), nullable=True),
        sa.Column("calculation_method", sa.String(length=50), nullable=True),
        sa.Column("result_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analytics_run_id"], ["analytics_runs.id"]),
        sa.ForeignKeyConstraint(["asset_a_id"], ["assets.id"]),
        sa.ForeignKeyConstraint(["asset_b_id"], ["assets.id"]),
    )
    op.create_index(
        "ix_correlation_results_analytics_run_id",
        "correlation_results",
        ["analytics_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_correlation_results_analytics_run_id", table_name="correlation_results")
    op.drop_table("correlation_results")
