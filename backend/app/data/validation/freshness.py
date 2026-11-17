"Data freshness policy shared by scanner, qualification, and dashboard."
from datetime import timedelta

TIMEFRAME_SECONDS = {"1h": 3600, "4h": 14400, "1d": 86400}


def freshness_status(last_data_time, now, timeframe: str) -> str:
    """LIVE if data is newer than 2 closed candles, STALE otherwise."""
    seconds = TIMEFRAME_SECONDS.get(timeframe)
    if seconds is None or last_data_time is None:
        return "UNKNOWN"
    return "LIVE" if (now - last_data_time) <= timedelta(seconds=2 * seconds) else "STALE"
