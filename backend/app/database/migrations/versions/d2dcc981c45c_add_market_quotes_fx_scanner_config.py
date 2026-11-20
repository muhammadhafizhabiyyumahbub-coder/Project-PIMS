"""add_market_quotes_fx_scanner_config

Revision ID: d2dcc981c45c
Revises: 2462e115ce2f
Create Date: 2026-11-20 09:24:00.180342

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd2dcc981c45c'
down_revision: Union[str, None] = '2462e115ce2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'market_quotes',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('asset_id', sa.UUID(), nullable=False),
        sa.Column('provider_id', sa.UUID(), nullable=False),
        sa.Column('provider_instrument_id', sa.UUID(), nullable=True),
        sa.Column('feed_type', sa.String(length=50), nullable=True),
        sa.Column('bid_price', sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column('ask_price', sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column('last_price', sa.Numeric(precision=30, scale=12), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('source_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('freshness_status', sa.String(length=30), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id'], ),
        sa.ForeignKeyConstraint(['provider_id'], ['data_providers.id'], ),
        sa.ForeignKeyConstraint(['provider_instrument_id'], ['provider_instruments.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_market_quotes_asset_received', 'market_quotes', ['asset_id', 'received_at'], unique=False)

    op.create_table(
        'fx_rates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('base_currency', sa.String(length=10), nullable=False),
        sa.Column('quote_currency', sa.String(length=10), nullable=False),
        sa.Column('rate', sa.Numeric(precision=30, scale=12), nullable=False),
        sa.Column('provider_id', sa.UUID(), nullable=False),
        sa.Column('source_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('freshness_status', sa.String(length=30), nullable=False),
        sa.CheckConstraint('rate > 0', name='ck_fx_rates_rate_positive'),
        sa.CheckConstraint('base_currency <> quote_currency', name='ck_fx_rates_currencies_distinct'),
        sa.ForeignKeyConstraint(['provider_id'], ['data_providers.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('base_currency', 'quote_currency', 'source_timestamp', name='uq_fx_pair_timestamp')
    )
    op.create_index('ix_fx_rates_base_quote_source', 'fx_rates', ['base_currency', 'quote_currency', 'source_timestamp'], unique=False)

    op.create_table(
        'scanner_configurations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('universe_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('filter_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ranking_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timeframe', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('scanner_configurations')
    op.drop_index('ix_fx_rates_base_quote_source', table_name='fx_rates')
    op.drop_table('fx_rates')
    op.drop_index('ix_market_quotes_asset_received', table_name='market_quotes')
    op.drop_table('market_quotes')
