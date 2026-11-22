import sys
sys.path.append("backend")

from app.core.db import get_engine
from sqlalchemy import text

engine = get_engine()

with engine.connect() as conn:
    query = text("SELECT a.symbol, a.quote_currency, m.currency FROM assets a JOIN market_candles m ON a.id = m.asset_id GROUP BY a.symbol, a.quote_currency, m.currency")
    result = conn.execute(query)
    for row in result:
        print(f"Asset: {row[0]}, Quote: {row[1]}, Candle Currency: {row[2]}")
