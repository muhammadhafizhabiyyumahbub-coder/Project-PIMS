"Market data models (quotes, FX rates, and candles)."
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, Boolean, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.core.db import Base
from app.database.models.core import utc_now


class MarketCandle(Base):
    __tablename__ = "market_candles"
    __table_args__ = (
        UniqueConstraint(
            "asset_id", "provider_id", "timeframe", "open_time", name="uq_candle_identity"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    provider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_providers.id"), nullable=False
    )
    feed_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    timeframe: Mapped[str] = mapped_column(String(20), nullable=False)
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    open_price: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 12), nullable=True)
    quote_volume: Mapped[Decimal | None] = mapped_column(Numeric(30, 12), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    candle_status: Mapped[str] = mapped_column(String(20), nullable=False, default="CLOSED")
    source_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class MarketQuote(Base):
    __tablename__ = "market_quotes"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    provider_instrument_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("provider_instruments.id"), nullable=True)
    feed_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bid_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 12), nullable=True)
    ask_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 12), nullable=True)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(30, 12), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    freshness_status: Mapped[str] = mapped_column(String(30), nullable=False)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

class FXRate(Base):
    __tablename__ = "fx_rates"
    __table_args__ = (
        CheckConstraint('rate > 0', name='ck_fx_rates_rate_positive'),
        CheckConstraint('base_currency <> quote_currency', name='ck_fx_rates_currencies_distinct'),
        UniqueConstraint('base_currency', 'quote_currency', 'source_timestamp', name='uq_fx_pair_timestamp'),
    )
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    base_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(30, 12), nullable=False)
    provider_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("data_providers.id"), nullable=False)
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    freshness_status: Mapped[str] = mapped_column(String(30), nullable=False)
