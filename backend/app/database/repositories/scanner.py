"Scanner configuration repositories."
import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import ScannerConfiguration
from app.database.models.core import utc_now


def create_scanner_config(
    session: Session,
    name: str,
    category: str,
    universe_config: dict,
    filter_config: dict,
    description: str | None = None,
    ranking_config: dict | None = None,
    timeframe: str | None = None,
) -> ScannerConfiguration:
    config = ScannerConfiguration(
        name=name,
        description=description,
        category=category,
        universe_config=universe_config,
        filter_config=filter_config,
        ranking_config=ranking_config,
        timeframe=timeframe,
        is_active=True,
    )
    session.add(config)
    session.flush()
    return config


def get_scanner_config(session: Session, config_id: uuid.UUID) -> ScannerConfiguration | None:
    return session.get(ScannerConfiguration, config_id)


def list_scanner_configs(session: Session) -> list[ScannerConfiguration]:
    return list(
        session.scalars(
            select(ScannerConfiguration).where(ScannerConfiguration.is_active.is_(True))
        )
    )


def update_scanner_config(
    session: Session,
    config: ScannerConfiguration,
    **values,
) -> ScannerConfiguration:
    for field, value in values.items():
        if value is not None:
            setattr(config, field, value)
    config.updated_at = utc_now()
    session.flush()
    return config


def delete_scanner_config(session: Session, config: ScannerConfiguration) -> None:
    session.delete(config)
    session.flush()