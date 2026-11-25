"""add_sentiment_results table

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-11-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sentiment_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analytics_run_id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("symbol", sa.String(length=60), nullable=False),
        sa.Column("sentiment_score", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("label", sa.String(length=20), nullable=True),
        sa.Column("confidence", sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column("headline_count", sa.Integer(), nullable=True),
        sa.Column("result_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["analytics_run_id"], ["analytics_runs.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
    )
    op.create_index(
        "ix_sentiment_results_analytics_run_id",
        "sentiment_results",
        ["analytics_run_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_sentiment_results_analytics_run_id", table_name="sentiment_results")
    op.drop_table("sentiment_results")
