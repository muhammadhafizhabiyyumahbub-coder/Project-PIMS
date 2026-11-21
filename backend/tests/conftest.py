"Shared fixtures: test database, universe, synthetic candles, analyzed pipeline."
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

if "PIMS_DATABASE_URL" not in os.environ:
    raise RuntimeError(
        "PIMS_DATABASE_URL environment variable is not set. "
        "Please create a .env file with your test database URL. "
        "See .env.example for format."
    )

import pytest

from app.config.settings import get_settings

get_settings.cache_clear()

from app.core import db as db_module  # noqa: E402

db_module._engine = None
db_module._session_factory = None

from app.core.db import Base, get_engine, get_session_factory  # noqa: E402
from app.database import models  # noqa: F401, E402
from app.database.models import Asset  # noqa: E402
from app.data.storage.universe import ensure_universe  # noqa: E402
from app.engines.runner import load_candles, run_instrument_engines  # noqa: E402
from app.engines.scanner.service import run_scanner  # noqa: E402
from app.data.storage.candles import upsert_candles  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402

TRUNCATE_TABLES = [
    "performance_results",
    "allocation_results",
    "portfolio_snapshots",
    "holdings",
    "cash_ledger",
    "transactions",
    "portfolios",
    "research_jobs",
    "research_reports",
    "research_requests",
    "scanner_results",
    "scanner_runs",
    "technical_results",
    "market_regime_results",
    "risk_results",
    "analytics_runs",
    "market_candles",
    "provider_instruments",
    "assets",
    "markets",
    "data_providers",
]


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(get_engine())
    # Stamp migration head so app startup (alembic upgrade) is a no-op in tests.
    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config(Path(__file__).resolve().parents[1] / "alembic.ini")
    alembic_cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "app" / "database" / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.stamp(alembic_cfg, "head")
    yield
    Base.metadata.drop_all(get_engine())


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def db_session():
    session = get_session_factory()()
    yield session
    session.rollback()
    for table in TRUNCATE_TABLES:
        session.execute(
            __import__("sqlalchemy").text(f"TRUNCATE TABLE {table} CASCADE")
        )
    session.commit()
    session.close()


def synthetic_candles(count: int = 120, base_price: float = 100.0, drift: float = 0.0) -> list[dict]:
    """Deterministic OHLCV series in engine format (labeled synthetic; tests only)."""
    start = datetime.now(timezone.utc) - timedelta(hours=count) - timedelta(minutes=15)
    candles = []
    price = base_price
    for i in range(count):
        open_ = price
        price = price * (1 + drift) + (i % 5 - 2) * 0.1
        close = price
        candles.append(
            {
                "open_time": start + timedelta(hours=i),
                "close_time": start + timedelta(hours=i + 1),
                "open": open_,
                "high": max(open_, close) + 0.5,
                "low": min(open_, close) - 0.5,
                "close": close,
                "volume": 1000.0,
                "quote_volume": (open_ + close) / 2 * 1000.0,
            }
        )
    return candles


def to_storage(candles: list[dict]) -> list[dict]:
    """Map engine-format candles to storage column names."""
    return [
        {
            "open_time": c["open_time"],
            "close_time": c["close_time"],
            "open_price": c["open"],
            "high_price": c["high"],
            "low_price": c["low"],
            "close_price": c["close"],
            "volume": c["volume"],
            "quote_volume": c["quote_volume"],
            "candle_status": "CLOSED",
        }
        for c in candles
    ]


@pytest.fixture()
def seeded_universe(db_session):
    return ensure_universe(db_session)


@pytest.fixture()
def analyzed_universe(db_session, seeded_universe):
    """Universe with stored candles, engine results, and a scanner run."""
    provider = seeded_universe["providers"][1]  # YAHOO
    for symbol, asset in seeded_universe["assets"].items():
        upsert_candles(
            db_session,
            asset_id=asset.id,
            provider_id=provider.id,
            timeframe="1h",
            normalized=to_storage(synthetic_candles(drift=0.002)),
            currency="USD",
            feed_type="REST_PUBLIC",
        )
    for asset in seeded_universe["assets"].values():
        run_instrument_engines(db_session, asset, "1h")
    run = run_scanner(db_session, "1h")
    return {**seeded_universe, "scanner_run": run}


@pytest.fixture()
def btc_asset(db_session, analyzed_universe) -> Asset:
    return analyzed_universe["assets"]["BTCUSDT"]
