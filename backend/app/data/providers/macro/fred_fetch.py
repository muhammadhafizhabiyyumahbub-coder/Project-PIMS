import logging
import os
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


# Tara subagent
class FredFetcher:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.stlouisfed.org/fred/series/observations"

    def fetch(self, series_id: str) -> List[Dict]:
        # No key -> UNAVAILABLE (empty), never fabricated data (audit F7).
        if not self.api_key or self.api_key == "test_key":
            logger.warning("FRED fetch skipped for %s: missing API key", series_id)
            return []
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json"
        }
        try:
            resp = requests.get(self.base_url, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as exc:
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

if __name__ == "__main__":
    key = os.getenv("PIMS_FRED_API_KEY")
    fetcher = FredFetcher(key)
    series = ["CPIAUCSL", "GDPC1", "UNRATE", "FEDFUNDS", "DGS10"]
    for s in series:
        data = fetcher.fetch(s)
        print(f"{s}: {len(data)} obs - Valid: {len(data) > 0}")
