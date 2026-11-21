"""Application configuration via environment variables."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate .env at repo root (parent of backend/)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_PATH = _REPO_ROOT / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PIMS_",
        env_file=str(_ENV_PATH) if _ENV_PATH.exists() else None,
        extra="ignore"
    )

    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://postgres@localhost:5432/pims"

    bybit_base_url: str = "https://api.bybit.com"
    bybit_api_key: str = ""
    bybit_api_secret: str = ""
    # Crypto data provider: BYBIT or YAHOO. YAHOO default because several ISPs
    # block exchange API domains; both adapters share the same interface.
    crypto_provider: str = "YAHOO"
    yahoo_base_url: str = "https://query1.finance.yahoo.com"

    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # Research orchestration policy (AGENTS.md: scheduled trigger disabled by default)
    research_cooldown_seconds: int = 900
    research_max_retries: int = 2
    research_stale_after_seconds: int = 3600
    scanner_stale_after_seconds: int = 1800
    scanner_schedule_enabled: bool = False
    research_schedule_enabled: bool = False
    # Scanner-based AI trigger is disabled by default (task rule: no automatic
    # research per scanner result until explicitly enabled).
    research_scanner_trigger_enabled: bool = False
    research_min_scanner_score: float = 80.0

@lru_cache
def get_settings() -> Settings:
    return Settings()