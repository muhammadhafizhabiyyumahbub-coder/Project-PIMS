"AI Research request/job/report models."
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ResearchRequest(Base):
    __tablename__ = "research_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    research_type: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True
    )
    timeframe: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    required_engines: Mapped[list] = mapped_column(JSONB, nullable=False)
    optional_engines: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    context_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    request_summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ResearchJob(Base):
    __tablename__ = "research_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_requests.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    engine_readiness: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    context_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_identifier: Mapped[str | None] = mapped_column(String(150), nullable=True)
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("research_reports.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_requests.id"), nullable=False
    )
    research_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    request_summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    report_content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ai_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model_identifier: Mapped[str] = mapped_column(String(150), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(30), nullable=False)
    observation_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observation_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
