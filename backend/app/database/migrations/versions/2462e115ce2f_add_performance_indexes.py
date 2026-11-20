"""add_performance_indexes

Revision ID: 2462e115ce2f
Revises: dcadf6176257
Create Date: 2026-11-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2462e115ce2f'
down_revision: Union[str, None] = 'dcadf6176257'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. assets: symbol, asset_type
    op.create_index('ix_assets_symbol_type', 'assets', ['symbol', 'asset_type'])
    
    # 2. market_candles: asset_id, timeframe, open_time
    op.create_index('ix_market_candles_asset_tf_time', 'market_candles', ['asset_id', 'timeframe', 'open_time'])
    
    # 3. analytics_runs: engine_type, started_at
    op.create_index('ix_analytics_runs_type_started', 'analytics_runs', ['engine_type', 'started_at'])
    
    # 4. performance_results: portfolio_id, period_start, period_end
    op.create_index('ix_perf_results_portfolio_period', 'performance_results', ['portfolio_id', 'period_start', 'period_end'])
    
    # 5. technical_results: asset_id, timeframe, observation_time
    op.create_index('ix_tech_results_asset_tf_time', 'technical_results', ['asset_id', 'timeframe', 'observation_time'])
    
    # 6. market_regime_results: asset_id, timeframe, observation_time
    op.create_index('ix_regime_results_asset_tf_time', 'market_regime_results', ['asset_id', 'timeframe', 'observation_time'])
    
    # 7. scanner_results: scanner_run_id, rank
    op.create_index('ix_scanner_results_run_rank', 'scanner_results', ['scanner_run_id', 'rank'])


def downgrade() -> None:
    op.drop_index('ix_scanner_results_run_rank', table_name='scanner_results')
    op.drop_index('ix_regime_results_asset_tf_time', table_name='market_regime_results')
    op.drop_index('ix_tech_results_asset_tf_time', table_name='technical_results')
    op.drop_index('ix_perf_results_portfolio_period', table_name='performance_results')
    op.drop_index('ix_analytics_runs_type_started', table_name='analytics_runs')
    op.drop_index('ix_market_candles_asset_tf_time', table_name='market_candles')
    op.drop_index('ix_assets_symbol_type', table_name='assets')
