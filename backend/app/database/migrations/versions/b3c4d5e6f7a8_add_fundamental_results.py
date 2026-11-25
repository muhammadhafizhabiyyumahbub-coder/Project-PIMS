"""add_fundamental_results table

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fundamental_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analytics_run_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("symbol", sa.String(length=60), nullable=False),
        sa.Column("pe", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("roe", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("revenue_growth", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("composite_score", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
        sa.Column("result_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analytics_run_id"], ["analytics_runs.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
    )
    op.create_index(
        "ix_fundamental_results_analytics_run_id",
        "fundamental_results",
        ["analytics_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_fundamental_results_analytics_run_id", table_name="fundamental_results")
    op.drop_table("fundamental_results")
