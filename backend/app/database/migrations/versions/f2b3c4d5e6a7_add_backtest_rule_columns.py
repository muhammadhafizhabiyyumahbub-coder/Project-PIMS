"""add backtest_metrics rule-based columns

Revision ID: f2b3c4d5e6a7
Revises: e8a9b0c1d2e3 (macro_results)
Create Date: 2026-11-28

Phase 2 (rule-based backtesting): run-level strategy/rule summary stored
alongside the long-format metric rows.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f2b3c4d5e6a7"
down_revision: Union[str, None] = "e8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "backtest_metrics",
        sa.Column("strategy_type", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "backtest_metrics",
        sa.Column("entry_rule", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "backtest_metrics",
        sa.Column("exit_rule", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "backtest_metrics",
        sa.Column("trade_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "backtest_metrics",
        sa.Column("win_rate", sa.Numeric(precision=20, scale=10), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("backtest_metrics", "win_rate")
    op.drop_column("backtest_metrics", "trade_count")
    op.drop_column("backtest_metrics", "exit_rule")
    op.drop_column("backtest_metrics", "entry_rule")
    op.drop_column("backtest_metrics", "strategy_type")
