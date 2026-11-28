import logging
import os
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# Tara subagent
class FredFetcher:
    def __init__(self, api_key: str, transport: Optional[httpx.BaseTransport] = None, timeout: float = 30.0):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org"
        self.transport = transport
        self.timeout = timeout

    def fetch(self, series_id: str) -> List[Dict]:
        """Fetch FRED observations. Deterministic: mock transport for tests, no network.
        No key -> UNAVAILABLE (empty), never fabricated data (audit F7).
        HTTP error -> log + empty (api_key never in log/URL).
        """
        if not self.api_key or self.api_key == "test_key":
            logger.warning("FRED fetch skipped for %s: missing API key", series_id)
            return []
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json"
        }
        try:
            with httpx.Client(transport=self.transport, timeout=self.timeout) as client:
                resp = client.get(f"{self.base_url}/fred/series/observations", params=params)
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            # Never log/raise the request URL: it embeds the api_key (query
            # param). httpx's str(HTTPStatusError) includes the full URL, so
            # reduce to status code + a generic reason (audit §26 key-leak).
            status = getattr(getattr(exc, "response", None), "status_code", None)
            logger.warning(
                "FRED fetch failed for series %s: http status %s (api key redacted)",
                series_id, status,
            )
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

if __name__ == "__main__":
    key = os.getenv("PIMS_FRED_API_KEY")
    fetcher = FredFetcher(key)
    series = ["CPIAUCSL", "GDPC1", "UNRATE", "FEDFUNDS", "DGS10"]
    for s in series:
        data = fetcher.fetch(s)
        print(f"{s}: {len(data)} obs - Valid: {len(data) > 0}")
