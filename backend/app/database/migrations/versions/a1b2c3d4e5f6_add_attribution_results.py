"""add_attribution_results

Revision ID: a1b2c3d4e5f6
Revises: 9b4f1c6e2a80
Create Date: 2026-11-25

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9b4f1c6e2a80"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "attribution_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analytics_run_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("symbol", sa.String(length=60), nullable=False),
        sa.Column("contribution", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("active_contribution", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("result_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analytics_run_id"], ["analytics_runs.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
    )
    op.create_index(
        "ix_attribution_results_analytics_run_id",
        "attribution_results",
        ["analytics_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_attribution_results_analytics_run_id", table_name="attribution_results")
    op.drop_table("attribution_results")