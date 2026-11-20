from datetime import datetime, UTC
import pytest
from sqlalchemy import event
from app.core.db import get_session_factory
from app.engines.portfolio.valuation import value_portfolio
from app.database.repositories.portfolio import create_portfolio
from app.database.models import Asset
import uuid

@pytest.fixture
def query_counter():
    class Counter:
        def __init__(self):
            self.count = 0
        def reset(self):
            self.count = 0
        def __call__(self, *args, **kwargs):
            self.count += 1
    return Counter()

def test_valuation_query_budget(query_counter):
    session_factory = get_session_factory()
    engine = session_factory.kw['bind']
    
    event.listen(engine, "before_cursor_execute", query_counter)
    
    try:
        def run_test(num_assets):
            with session_factory() as session:
                p = create_portfolio(session, "test", "USD")
                assets = []
                for i in range(num_assets):
                    a = Asset(symbol=f"SYM{i}", name=f"Name{i}", asset_type="CRYPTO")
                    session.add(a)
                    session.flush()
                    assets.append(a)
                
                query_counter.reset()
                value_portfolio(session, p.id, datetime.now(UTC))
                return query_counter.count

        count10 = run_test(10)
        count30 = run_test(30)
        
        # Current budget: 10/30 should be identical as per n+1 fix
        assert count10 == count30, f"Query count must be constant: {count10} vs {count30}"
        
    finally:
        event.remove(engine, "before_cursor_execute", query_counter)
