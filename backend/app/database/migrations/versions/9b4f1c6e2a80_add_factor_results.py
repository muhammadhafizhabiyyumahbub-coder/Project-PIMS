"""add_factor_results

Revision ID: 9b4f1c6e2a80
Revises: 5c7e2a90b3d1
Create Date: 2026-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9b4f1c6e2a80"
down_revision: Union[str, None] = "5c7e2a90b3d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "factor_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analytics_run_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=60), nullable=False),
        sa.Column("raw_factors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("z_factors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("composite_score", sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column("excluded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("result_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analytics_run_id"], ["analytics_runs.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
    )
    op.create_index(
        "ix_factor_results_analytics_run_id",
        "factor_results",
        ["analytics_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_factor_results_analytics_run_id", table_name="factor_results")
    op.drop_table("factor_results")
