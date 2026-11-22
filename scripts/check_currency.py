import sys
sys.path.append("backend")

from app.core.db import get_engine
from sqlalchemy import text

engine = get_engine()

with engine.connect() as conn:
    query = text("SELECT currency, count(*) FROM market_candles GROUP BY 1")
    result = conn.execute(query)
    for row in result:
        print(f"Currency: {row[0]}, Count: {row[1]}")
