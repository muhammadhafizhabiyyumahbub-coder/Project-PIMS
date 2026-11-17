"Market Scanner run and result models."
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ScannerRun(Base):
    __tablename__ = "scanner_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    execution_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(30), nullable=False)
    universe_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eligible_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    execution_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class ScannerResult(Base):
    __tablename__ = "scanner_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scanner_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scanner_runs.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(20), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = mapped_column(Numeric(20, 10), nullable=True)
    matched_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    metric_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    result_status: Mapped[str] = mapped_column(String(30), nullable=False)
    # Proposed additions to schema-spec 8.3: dashboard must show data status
    # and updated-at, which require freshness and the underlying data timestamp.
    freshness_status: Mapped[str] = mapped_column(String(30), nullable=False)
    data_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
