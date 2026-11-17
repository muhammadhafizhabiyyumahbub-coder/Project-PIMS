"Market data models (normalized OHLCV candles)."
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

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
    open_price: Mapped[float] = mapped_column(Numeric(30, 12), nullable=False)
    high_price: Mapped[float] = mapped_column(Numeric(30, 12), nullable=False)
    low_price: Mapped[float] = mapped_column(Numeric(30, 12), nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(30, 12), nullable=False)
    volume: Mapped[float | None] = mapped_column(Numeric(30, 12), nullable=True)
    quote_volume: Mapped[float | None] = mapped_column(Numeric(30, 12), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    candle_status: Mapped[str] = mapped_column(String(20), nullable=False, default="CLOSED")
    source_timestamp: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
