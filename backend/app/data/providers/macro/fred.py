"""FRED macro data provider (M4 Macro Engine, Phase 1).

Fetches public US macro series from the St. Louis Fed FRED API. Uses the
already-installed httpx client; a `transport` can be injected so tests run
deterministically with no network (httpx.MockTransport).

HONEST: missing values (".") are dropped; any network/HTTP failure returns an
empty list so the engine reports UNAVAILABLE (never fabricates a 0).
License: FRED data is public-domain-ish (US government series); attribution per
https://fred.stlouisfed.org/legal/.
"""
import logging
from typing import Optional

import httpx

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

# Logical key -> FRED series id.
SERIES_MAP = {
    "CPI": "CPIAUCSL",   # CPI All Urban Consumers (monthly)
    "GDP": "GDPC1",      # Real GDP, chained 2017 USD (quarterly) — spec series
    "UNRATE": "UNRATE",  # Unemployment rate (monthly)
    "FEDFUNDS": "FEDFUNDS",  # Effective federal funds rate (monthly)
    "DFF": "DFF",        # Federal funds effective rate (daily)
    "10YUSTR": "DGS10",  # 10-Year Treasury constant maturity (daily)
}


class FREDAdapter:
    provider_code = "FRED"
    feed_type = "REST_PUBLIC"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        transport: Optional[httpx.BaseTransport] = None,
        timeout: float = 15.0,
    ) -> None:
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.fred_api_key
        self.base_url = (base_url or settings.fred_base_url).rstrip("/")
        self.transport = transport
        self.timeout = timeout

    def fetch_observations(
        self, series_id: str, observation_start: Optional[str] = None
    ) -> list[dict]:
        """Return [{'date': 'YYYY-MM-DD', 'value': float}] oldest-first.

        Empty list on missing key, HTTP error, or no observations -> UNAVAILABLE.
        """
        if not self.api_key:
            return []
        params = {"series_id": series_id, "api_key": self.api_key, "file_type": "json"}
        if observation_start:
            params["observation_start"] = observation_start
        try:
            with httpx.Client(transport=self.transport, timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/fred/series/observations", params=params)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            # Surface transient failures instead of silently returning empty.
            logger.warning("FRED fetch failed for %s: %s", series_id, exc)
            return []

        out = []
        for obs in resp.json().get("observations", []):
            raw = obs.get("value")
            if raw in (None, "", "."):
                continue
            try:
                out.append({"date": obs["date"], "value": float(raw)})
            except (KeyError, TypeError, ValueError):
                continue
        return out
