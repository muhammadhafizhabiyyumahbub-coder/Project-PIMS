"""Portfolio Stage A tests: cost basis (WAC), holdings, valuation, DB integrity.

All expected numbers are computed by hand and written in comments next to the
assertions. Candle fixtures are SYNTHETIC test data, never presented as market
data (AGENTS.md §18).
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.database.repositories import portfolio as repo
from app.engines.portfolio.cost_basis import CostBasisState, apply_buy, apply_sell, unrealized_pnl
from app.engines.portfolio.holdings import quantize, replay_holdings
from app.engines.portfolio.service import TransactionError, record_transaction
from app.engines.portfolio.valuation import value_portfolio
from app.database.models import MarketCandle

D = Decimal


@pytest.fixture()
def portfolio(db_session):
    return repo.create_portfolio(db_session, name="Test Portfolio", reporting_currency="USD")


def store_candle(db_session, asset_id, provider_id, close, open_time):
    """Store one synthetic candle (test fixture, labeled; not market data)."""
    db_session.add(
        MarketCandle(
            asset_id=asset_id,
            provider_id=provider_id,
            timeframe="1h",
            open_time=open_time,
            close_time=open_time + timedelta(hours=1),
            open_price=close,
            high_price=close,
            low_price=close,
            close_price=close,
            volume=D("1000"),
            currency="USD",
            candle_status="CLOSED",
        )
    )
    db_session.commit()


# ---------------------------------------------------------------------------
# 1. Pure cost-basis math (hand-computed)
# ---------------------------------------------------------------------------


def test_weighted_average_cost_buy_then_sell():
    # BUY 10 @ 100 fee 10: basis = 10*100 + 10 = 1010, qty 10, avg 101.00
    s = apply_buy(CostBasisState(), D("10"), D("100"), D("10"))
    assert s.quantity == D("10")
    assert s.cost_basis == D("1010")
    assert s.average_cost == D("101")

    # BUY 10 @ 120 fee 0: basis = 1010 + 1200 = 2210, qty 20, avg 110.50
    s = apply_buy(s, D("10"), D("120"))
    assert s.cost_basis == D("2210")
    assert s.average_cost == D("110.5")

    # SELL 5 @ 200 fee 5: net = 1000 - 5 = 995; allocated = 5 * 110.5 = 552.5
    # realized = 995 - 552.5 = 442.5; remaining basis = 2210 - 552.5 = 1657.5
    s2 = apply_sell(s, D("5"), D("200"), D("5"))
    assert s2.quantity == D("15")
    assert s2.cost_basis == D("1657.5")
    assert s2.average_cost == D("110.5")  # WAC unchanged by sale
    assert s2.realized_pnl == D("442.5")

    # Unrealized at price 130: 15*130 - 1657.5 = 292.5 (spec §9.1)
    assert unrealized_pnl(s2, D("130")) == D("292.5")


def test_sell_rejects_quantity_exceeding_holdings():
    s = apply_buy(CostBasisState(), D("2"), D("100"))
    with pytest.raises(ValueError, match="exceeds available holdings"):
        apply_sell(s, D("3"), D("100"))


def test_replay_holdings_matches_pure_engine():
    """Replay of transaction rows must equal the pure engine result."""

    class Row:  # minimal stand-in for a Transaction row (test only)
        def __init__(self, ttype, asset, qty, price, fee):
            self.transaction_type = ttype
            self.asset_id = asset
            self.quantity = qty
            self.price = price
            self.fee_amount = fee
            self.gross_amount = qty * price
            self.transaction_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
            self.created_at = None
            self.id = uuid.uuid4()

    asset = uuid.uuid4()
    rows = [
        Row("BUY", asset, D("10"), D("100"), D("10")),
        Row("BUY", asset, D("10"), D("120"), D("0")),
        Row("SELL", asset, D("5"), D("200"), D("5")),
    ]
    state = replay_holdings(rows)[asset]
    # Same numbers as test_weighted_average_cost_buy_then_sell
    assert state.quantity == D("15")
    assert state.cost_basis == D("1657.5")
    assert state.realized_pnl == D("442.5")


# ---------------------------------------------------------------------------
# 2. Service: atomic transaction + ledger + holdings (real PostgreSQL)
# ---------------------------------------------------------------------------


def test_transaction_scenario_end_to_end(db_session, portfolio, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio.id

    record_transaction(db_session, pid, "DEPOSIT", gross_amount=D("1000"))
    record_transaction(db_session, pid, "BUY", asset_id=asset.id, quantity=D("2"), price=D("100"), fee_amount=D("2"))
    record_transaction(db_session, pid, "BUY", asset_id=asset.id, quantity=D("3"), price=D("110"), fee_amount=D("3"))
    record_transaction(db_session, pid, "SELL", asset_id=asset.id, quantity=D("1"), price=D("120"), fee_amount=D("1"))

    transactions = repo.list_transactions(db_session, pid)
    assert len(transactions) == 4

    # Holding: qty 5-1=4, basis 202+333-107=428, avg 107
    holding = repo.get_holding(db_session, pid, asset.id)
    assert holding.quantity == D("4")
    assert holding.cost_basis == D("428")
    assert holding.average_cost == D("107")
    assert holding.calculation_status == "VALID"

    # Ledger sign convention: +1000 (deposit), -202 (buy 200+2), -333, +119 (120-1)
    entries = repo.ledger_entries(db_session, pid)
    assert [(e.entry_type, e.amount) for e in entries] == [
        ("DEPOSIT", D("1000")),
        ("BUY", D("-202")),
        ("BUY", D("-333")),
        ("SELL", D("119")),
    ]
    # Ledger sum equals cash balance exactly: 1000-202-333+119 = 584
    assert sum(e.amount for e in entries) == D("584")
    assert repo.cash_balance(db_session, pid, "USD") == D("584")

    # Every ledger entry traceable to its transaction (spec §5.3)
    for entry in entries:
        assert entry.transaction_id is not None
        assert entry.transaction_id in {t.id for t in transactions}


def test_idempotent_replay_returns_same_transaction(db_session, portfolio, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio.id
    record_transaction(db_session, pid, "DEPOSIT", gross_amount=D("500"), idempotency_key="dep-1")
    replayed, created = record_transaction(
        db_session, pid, "DEPOSIT", gross_amount=D("500"), idempotency_key="dep-1"
    )
    assert created is False
    assert len(repo.list_transactions(db_session, pid)) == 1
    assert repo.cash_balance(db_session, pid, "USD") == D("500")  # not 1000


def test_idempotency_scoped_per_portfolio(db_session, portfolio, seeded_universe):
    other = repo.create_portfolio(db_session, name="Other", reporting_currency="USD")
    asset = seeded_universe["assets"]["BTCUSDT"]
    record_transaction(db_session, portfolio.id, "DEPOSIT", gross_amount=D("100"), idempotency_key="k1")
    record_transaction(db_session, other.id, "DEPOSIT", gross_amount=D("200"), idempotency_key="k1")
    # Same key allowed in a different portfolio; one row each.
    assert len(repo.list_transactions(db_session, portfolio.id)) == 1
    assert len(repo.list_transactions(db_session, other.id)) == 1


def test_failed_sell_leaves_no_rows(db_session, portfolio, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio.id
    record_transaction(db_session, pid, "DEPOSIT", gross_amount=D("1000"))
    record_transaction(db_session, pid, "BUY", asset_id=asset.id, quantity=D("1"), price=D("100"))

    with pytest.raises(TransactionError) as exc:
        record_transaction(db_session, pid, "SELL", asset_id=asset.id, quantity=D("2"), price=D("99"))
    assert exc.value.code == "INSUFFICIENT_HOLDINGS"

    # Nothing half-written: exactly the 2 valid transactions, 2 ledger rows.
    assert len(repo.list_transactions(db_session, pid)) == 2
    assert len(repo.ledger_entries(db_session, pid)) == 2
    holding = repo.get_holding(db_session, pid, asset.id)
    assert holding.quantity == D("1")


def test_insufficient_cash_rejected(db_session, portfolio):
    with pytest.raises(TransactionError) as exc:
        record_transaction(db_session, portfolio.id, "WITHDRAWAL", gross_amount=D("50"))
    assert exc.value.code == "INSUFFICIENT_CASH"


def test_currency_mismatch_rejected(db_session, portfolio, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    with pytest.raises(TransactionError) as exc:
        record_transaction(
            db_session, portfolio.id, "BUY", asset_id=asset.id, quantity=D("1"), price=D("1"), currency="IDR"
        )
    assert exc.value.code == "CURRENCY_MISMATCH"


def test_holdings_rebuild_is_idempotent(db_session, portfolio, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio.id
    record_transaction(db_session, pid, "DEPOSIT", gross_amount=D("1000"))
    record_transaction(db_session, pid, "BUY", asset_id=asset.id, quantity=D("2"), price=D("100"), fee_amount=D("2"))
    first = repo.get_holding(db_session, pid, asset.id)
    repo.list_transactions(db_session, pid)  # touch session
    second = repo.get_holding(db_session, pid, asset.id)
    assert (first.quantity, first.cost_basis, first.average_cost) == (
        second.quantity,
        second.cost_basis,
        second.average_cost,
    )
    holdings = repo.list_holdings(db_session, pid)
    assert len(holdings) == 1  # upsert, never duplicate rows


# ---------------------------------------------------------------------------
# 3. Database integrity (constraints enforced by PostgreSQL)
# ---------------------------------------------------------------------------


def test_fk_violation_rejected(db_session, portfolio):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        repo.add_transaction(
            db_session,
            portfolio_id=uuid.uuid4(),  # nonexistent portfolio
            transaction_type="DEPOSIT",
            transaction_date=datetime.now(timezone.utc),
            gross_amount=D("10"),
            fee_amount=D("0"),
            currency="USD",
        )
    db_session.rollback()


def test_check_constraint_rejects_negative_amounts(db_session, portfolio):
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        repo.add_transaction(
            db_session,
            portfolio_id=portfolio.id,
            transaction_type="DEPOSIT",
            transaction_date=datetime.now(timezone.utc),
            gross_amount=D("-10"),  # violates ck_transaction_gross_non_negative
            fee_amount=D("0"),
            currency="USD",
        )
    db_session.rollback()
    # Rollback left nothing behind (atomic write, spec §15.1).
    assert len(repo.list_transactions(db_session, portfolio.id)) == 0


def test_unique_idempotency_enforced_in_db(db_session, portfolio):
    from sqlalchemy.exc import IntegrityError

    record_transaction(db_session, portfolio.id, "DEPOSIT", gross_amount=D("10"), idempotency_key="uq-1")
    with pytest.raises(IntegrityError):
        repo.add_transaction(
            db_session,
            portfolio_id=portfolio.id,
            transaction_type="DEPOSIT",
            transaction_date=datetime.now(timezone.utc),
            gross_amount=D("10"),
            fee_amount=D("0"),
            currency="USD",
            idempotency_key="uq-1",
        )
    db_session.rollback()


def test_ledger_one_entry_per_transaction(db_session, portfolio):
    record_transaction(db_session, portfolio.id, "DEPOSIT", gross_amount=D("10"))
    entries = repo.ledger_entries(db_session, portfolio.id)
    assert len(entries) == 1
    record_transaction(db_session, portfolio.id, "DEPOSIT", gross_amount=D("10"))
    assert len(repo.ledger_entries(db_session, portfolio.id)) == 2


def test_mid_write_failure_leaves_nothing(db_session, portfolio, seeded_universe, monkeypatch):
    """Ledger write fails after the transaction row flushed → both roll back."""
    from app.database.repositories import portfolio as repo_mod

    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio.id

    def explode(*args, **kwargs):
        raise RuntimeError("simulated ledger failure")

    monkeypatch.setattr(repo_mod, "add_ledger_entry", explode)
    with pytest.raises(RuntimeError):
        record_transaction(db_session, pid, "BUY", asset_id=asset.id, quantity=D("1"), price=D("10"))
    db_session.rollback()
    # Atomic: neither the transaction row nor any ledger row survived.
    assert len(repo.list_transactions(db_session, pid)) == 0
    assert len(repo.ledger_entries(db_session, pid)) == 0


# ---------------------------------------------------------------------------
# 4. Valuation (synthetic candles, labeled)
# ---------------------------------------------------------------------------


def test_valuation_complete(db_session, portfolio, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]  # YAHOO
    pid = portfolio.id
    record_transaction(db_session, pid, "DEPOSIT", gross_amount=D("1000"))
    record_transaction(db_session, pid, "BUY", asset_id=asset.id, quantity=D("2"), price=D("100"), fee_amount=D("2"))
    record_transaction(db_session, pid, "BUY", asset_id=asset.id, quantity=D("3"), price=D("110"), fee_amount=D("3"))
    record_transaction(db_session, pid, "SELL", asset_id=asset.id, quantity=D("1"), price=D("120"), fee_amount=D("1"))
    # SYNTHETIC candle (test fixture): close 105, fresh.
    store_candle(db_session, asset.id, provider.id, D("105"), datetime.now(timezone.utc) - timedelta(hours=1))

    valuation = value_portfolio(db_session, pid)
    assert valuation.valuation_status == "COMPLETE"
    # qty 4, basis 428 (see end-to-end test); market 4*105 = 420
    # unrealized = 420 - 428 = -8; realized = 119 - 107 = 12; total pnl = 4
    pos = valuation.positions[0]
    assert pos.quantity == D("4")
    assert pos.market_value == D("420")
    assert pos.unrealized_pnl == D("-8")
    assert valuation.realized_pnl == D("12")
    assert valuation.unrealized_pnl == D("-8")
    # total value = cash 584 + invested 420 = 1004
    assert valuation.cash_value == D("584")
    assert valuation.invested_value == D("420")
    assert valuation.total_value == D("1004")


def test_valuation_partial_when_price_missing(db_session, portfolio, seeded_universe):
    btc = seeded_universe["assets"]["BTCUSDT"]
    sol = seeded_universe["assets"]["SOLUSDT"]
    pid = portfolio.id
    record_transaction(db_session, pid, "DEPOSIT", gross_amount=D("1000"))
    record_transaction(db_session, pid, "BUY", asset_id=btc.id, quantity=D("1"), price=D("100"))
    record_transaction(db_session, pid, "BUY", asset_id=sol.id, quantity=D("1"), price=D("50"))
    # Candle only for BTC: SOL has no stored price and must NOT be invented.
    store_candle(db_session, btc.id, seeded_universe["providers"][1].id, D("110"), datetime.now(timezone.utc))

    valuation = value_portfolio(db_session, pid)
    assert valuation.valuation_status == "PARTIAL"
    by_symbol = {p.symbol: p for p in valuation.positions}
    assert by_symbol["BTCUSDT"].market_value == D("110")
    assert by_symbol["SOLUSDT"].market_price is None
    assert by_symbol["SOLUSDT"].market_value is None
    assert by_symbol["SOLUSDT"].price_status == "MISSING"
    # Unrealized P&L not reported when incomplete — never a fabricated number.
    assert valuation.unrealized_pnl is None
    # invested_value counts only valued positions (BTC), cash still exact.
    assert valuation.invested_value == D("110")


def test_valuation_stale_when_price_old(db_session, portfolio, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio.id
    record_transaction(db_session, pid, "DEPOSIT", gross_amount=D("1000"))
    record_transaction(db_session, pid, "BUY", asset_id=asset.id, quantity=D("1"), price=D("100"))
    # 3 hours old > PRICE_FRESHNESS_SECONDS (7200) → STALE, price shown but flagged.
    store_candle(db_session, asset.id, seeded_universe["providers"][1].id, D("130"), datetime.now(timezone.utc) - timedelta(hours=3))

    valuation = value_portfolio(db_session, pid)
    assert valuation.valuation_status == "STALE"
    pos = valuation.positions[0]
    assert pos.price_status == "STALE"
    assert pos.market_value is None  # stale price not used for valuation
    assert valuation.total_value is None


def test_valuation_unavailable_without_transactions(db_session, portfolio):
    valuation = value_portfolio(db_session, portfolio.id)
    assert valuation.valuation_status == "UNAVAILABLE"
    assert valuation.total_value is None


def test_quantize_matches_storage_scale():
    assert quantize(D("107")) == D("107")
    assert str(quantize(D("1") / D("3"))) == "0.333333333333"
