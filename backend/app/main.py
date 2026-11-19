"FastAPI application entrypoint."
from alembic import command
from alembic.config import Config
from pathlib import Path

from fastapi import FastAPI

from app.api.rest import assets, dashboard, health, market_data, markets, portfolios, research, scanner, transactions, analytics as analytics_rest
from app.api.websocket.channels import router as ws_router
from app.api.websocket.market import router as market_ws_router
from app.config.settings import get_settings
from app.core.logging import configure_logging


def run_migrations() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(backend_root / "alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(alembic_cfg, "head")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="PIMS Backend", version="0.1.0")

    @app.on_event("startup")
    def startup() -> None:
        run_migrations()
        from app.core.db import get_session_factory
        from app.data.storage.universe import ensure_universe

        session = get_session_factory()()
        try:
            ensure_universe(session)
        finally:
            session.close()

    app.include_router(health.router)
    app.include_router(market_data.router, prefix="/api/v1")
    app.include_router(markets.router, prefix="/api/v1")
    app.include_router(scanner.router, prefix="/api/v1")
    app.include_router(dashboard.router, prefix="/api/v1")
    app.include_router(research.router, prefix="/api/v1")
    app.include_router(portfolios.router, prefix="/api/v1")
    app.include_router(analytics_rest.router, prefix="/api/v1")
    app.include_router(transactions.router, prefix="/api/v1")
    app.include_router(assets.router, prefix="/api/v1")
    app.include_router(market_ws_router)
    app.include_router(ws_router)
    return app


app = create_app()
