"""Stage H: Performance Engine tests (TWR, simple return, CAGR, P&L, tolerances).

All expected numbers are hand-computed and written in comments.
Decimal only; no JSON floats; snapshot-tolerance driven UNAVAILABLE.
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.database.repositories import portfolio as repo
from app.engines.portfolio.performance import (
    CashFlowPoint,
    SnapshotPoint,
    compute_performance,
)
from app.main import app

D = Decimal

PID = uuid.UUID("00000000-0000-0000-0000-0000000000aa")


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def portfolio_id(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Performance Test Portfolio", "base_currency": "USD"},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def _at(day, hour=0):
    return datetime(2026, 1, day, hour, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# 1. No external cash flow: TWR == simple return
# ---------------------------------------------------------------------------


def test_no_cash_flow_twr_equals_simple_return():
    """Snapshots 1000 -> 1250, no flows.

    Hand-computed:
      TWR           = 1250/1000 - 1 = 0.25
      simple return = (1250 - 1000)/1000 = 0.25
    """
    res = compute_performance(
        portfolio_id=PID,
        reporting_currency="USD",
        snapshots=[
            SnapshotPoint(at=_at(1), total_value=D("1000"), valuation_status="COMPLETE"),
            SnapshotPoint(
                at=_at(10),
                total_value=D("1250"),
                valuation_status="COMPLETE",
                realized_pnl="50",
                unrealized_pnl="200",
            ),
        ],
        cash_flows=[],
        start=_at(1),
        end=_at(10),
    )
    assert res.return_status == "AVAILABLE"
    assert res.twr == D("0.25")
    assert res.simple_return == D("0.25")
    assert res.sub_period_count == 1
    assert res.realized_pnl == "50"
    assert res.unrealized_pnl == "200"


# ---------------------------------------------------------------------------
# 2. One mid-period deposit: TWR is timing-neutral, plain return is not
# ---------------------------------------------------------------------------


def test_deposit_twr_is_timing_neutral_while_plain_return_distorts():
    """Same market path product, two deposit dates; TWR unchanged, plain differs.

    Case A (deposit at day 5): market factors 1.20 (day1->day5) then 1.25.
        1000 * 1.20 = 1200 pre-deposit; +500 => day5 snapshot 1700
        1700 * 1.25 = day10 2125
        r1 = (1700 - 500)/1000 - 1 = 0.20 ; r2 = 2125/1700 - 1 = 0.25
        TWR = 1.20 * 1.25 - 1 = 0.50
        plain = (2125 - 1000)/1000 = 1.125
    Case B (deposit at day 2): market factors 1.10 then 1.50/1.10.
        1000 * 1.10 = 1100 pre-deposit; +500 => day2 snapshot 1600
        1600 * (1.50/1.10) = 24000/11 = 2181.818181... at day10
        r1 = (1600 - 500)/1000 - 1 = 0.10 ; r2 = (24000/11)/1600 - 1 = 0.3636...
        TWR = 1.10 * (1.50/1.10) - 1 = 0.50
        plain = (2181.818181... - 1000)/1000 = 1.181818...

    TWR equal (0.50) in both cases; plain return differs (1.125 vs 1.1818...).
    """
    a = compute_performance(
        portfolio_id=PID,
        reporting_currency="USD",
        snapshots=[
            SnapshotPoint(at=_at(1), total_value=D("1000"), valuation_status="COMPLETE"),
            SnapshotPoint(at=_at(5), total_value=D("1700"), valuation_status="COMPLETE"),
            SnapshotPoint(at=_at(10), total_value=D("2125"), valuation_status="COMPLETE"),
        ],
        cash_flows=[CashFlowPoint(at=_at(5), amount=D("500"))],
        start=_at(1),
        end=_at(10),
    )
    b = compute_performance(
        portfolio_id=PID,
        reporting_currency="USD",
        snapshots=[
            SnapshotPoint(at=_at(1), total_value=D("1000"), valuation_status="COMPLETE"),
            SnapshotPoint(at=_at(2), total_value=D("1600"), valuation_status="COMPLETE"),
            SnapshotPoint(
                at=_at(10),
                total_value=D("24000") / D("11"),
                valuation_status="COMPLETE",
            ),
        ],
        cash_flows=[CashFlowPoint(at=_at(2), amount=D("500"))],
        start=_at(1),
        end=_at(10),
    )

    assert a.return_status == "AVAILABLE" and b.return_status == "AVAILABLE"
    assert a.sub_period_count == 2 and b.sub_period_count == 2
    assert abs(a.twr - D("0.50")) < D("0.000000000001")
    assert abs(b.twr - D("0.50")) < D("0.000000000001")

    # Plain return would distort the answer; the engine refuses to report it
    # while external flows exist (spec §10.2).
    assert a.simple_return is None and b.simple_return is None
    assert "external cash flows" in a.simple_return_reason
    # Timing changed the naive number (1.125 vs 1.181818...), not the TWR.
    assert D("1.125") != (D("24000") / D("11") - D("1000")) / D("1000")


# ---------------------------------------------------------------------------
# 3. Withdrawal
# ---------------------------------------------------------------------------


def test_withdrawal_sub_period_return():
    """1000 -> (day5) 1500 then withdraw 500 -> (day10) 1100.

    Sub-period 1: BMV 1000, EMV 1000 (post-withdrawal snapshot), CF -500
        r1 = (1000 - (-500))/1000 - 1 = 0.50
    Sub-period 2: BMV 1000, EMV 1100, CF 0
        r2 = 1100/1000 - 1 = 0.10
    TWR = 1.50 * 1.10 - 1 = 0.65
    """
    res = compute_performance(
        portfolio_id=PID,
        reporting_currency="USD",
        snapshots=[
            SnapshotPoint(at=_at(1), total_value=D("1000"), valuation_status="COMPLETE"),
            SnapshotPoint(at=_at(5), total_value=D("1000"), valuation_status="COMPLETE"),
            SnapshotPoint(at=_at(10), total_value=D("1100"), valuation_status="COMPLETE"),
        ],
        cash_flows=[CashFlowPoint(at=_at(5), amount=D("-500"))],
        start=_at(1),
        end=_at(10),
    )
    assert res.return_status == "AVAILABLE"
    assert abs(res.twr - D("0.65")) < D("0.000000000001")


# ---------------------------------------------------------------------------
# 4. Missing/stale snapshot near a cash flow -> TWR UNAVAILABLE + reason
# ---------------------------------------------------------------------------


def test_twr_unavailable_when_no_snapshot_within_tolerance():
    """Deposit at day5 12:00; nearest snapshot is day8 (2.5 days away > 1 day).

    Nothing is interpolated, so TWR is UNAVAILABLE with an explicit reason.
    """
    flow_at = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    res = compute_performance(
        portfolio_id=PID,
        reporting_currency="USD",
        snapshots=[
            SnapshotPoint(at=_at(1), total_value=D("1000"), valuation_status="COMPLETE"),
            SnapshotPoint(at=_at(8), total_value=D("2500"), valuation_status="COMPLETE"),
            SnapshotPoint(at=_at(10), total_value=D("3000"), valuation_status="COMPLETE"),
        ],
        cash_flows=[CashFlowPoint(at=flow_at, amount=D("1000"))],
        start=_at(1),
        end=_at(10),
    )
    assert res.return_status == "UNAVAILABLE"
    assert res.twr is None
    assert res.twr_reason and "No stored snapshot within 1 day" in res.twr_reason
    assert res.cagr is None


def test_twr_unavailable_when_boundary_snapshot_has_no_value():
    """A boundary snapshot with total_value NULL cannot anchor a sub-period."""
    res = compute_performance(
        portfolio_id=PID,
        reporting_currency="USD",
        snapshots=[
            SnapshotPoint(at=_at(1), total_value=D("1000"), valuation_status="COMPLETE"),
            SnapshotPoint(
                at=_at(10),
                total_value=None,
                valuation_status="UNAVAILABLE",
                status_reason="MISSING_PRICE",
            ),
        ],
        cash_flows=[],
        start=_at(1),
        end=_at(10),
    )
    assert res.return_status == "UNAVAILABLE"
    assert "no total value" in res.twr_reason
    assert "UNAVAILABLE: MISSING_PRICE" in res.twr_reason


# ---------------------------------------------------------------------------
# 5. CAGR gating (< 365 days -> null; >= 365 with correct value)
# ---------------------------------------------------------------------------


def test_cagr_null_below_one_year():
    """151 days < 365 -> no CAGR, explicit reason."""
    res = compute_performance(
        portfolio_id=PID,
        reporting_currency="USD",
        snapshots=[
            SnapshotPoint(
                at=datetime(2025, 1, 1, tzinfo=UTC),
                total_value=D("1000"),
                valuation_status="COMPLETE",
            ),
            SnapshotPoint(
                at=datetime(2025, 6, 1, tzinfo=UTC),
                total_value=D("1200"),
                valuation_status="COMPLETE",
            ),
        ],
        cash_flows=[],
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2025, 6, 1, tzinfo=UTC),
    )
    assert res.return_status == "AVAILABLE"
    assert res.period_days == 151
    assert res.cagr is None
    assert "at least 365 days" in res.cagr_reason


def test_cagr_two_year_period():
    """1000 -> 1440 over 730 days (2 years).

    Growth = 1440/1000 = 1.44; CAGR = 1.44 ** (1/2) - 1 = 1.2 - 1 = 0.20
    """
    res = compute_performance(
        portfolio_id=PID,
        reporting_currency="USD",
        snapshots=[
            SnapshotPoint(
                at=datetime(2025, 1, 1, tzinfo=UTC),
                total_value=D("1000"),
                valuation_status="COMPLETE",
            ),
            SnapshotPoint(
                at=datetime(2027, 1, 1, tzinfo=UTC),
                total_value=D("1440"),
                valuation_status="COMPLETE",
            ),
        ],
        cash_flows=[],
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2027, 1, 1, tzinfo=UTC),
    )
    assert res.return_status == "AVAILABLE"
    assert res.period_days == 730
    assert abs(res.cagr - D("0.20")) < D("0.000000000001")


# ---------------------------------------------------------------------------
# 6. HTTP contract: envelope, decimal strings, no floats
# ---------------------------------------------------------------------------


def test_performance_endpoint_without_snapshots_is_unavailable(client, portfolio_id):
    r = client.get(f"/api/v1/portfolios/{portfolio_id}/performance")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["portfolio_id"] == portfolio_id
    assert body["reporting_currency"] == "USD"
    assert body["return_status"] == "UNAVAILABLE"
    assert body["twr"] is None
    assert body["twr_reason"]


def test_performance_endpoint_returns_decimal_strings(client, portfolio_id, db_session):
    """Two stored snapshots -> AVAILABLE, every return value is a JSON string."""
    pid = uuid.UUID(portfolio_id)
    repo.add_snapshot(
        db_session,
        portfolio_id=pid,
        snapshot_at=_at(1),
        total_value=D("1000"),
        cash_value=D("1000"),
        invested_value=D("0"),
        reporting_currency="USD",
        valuation_status="COMPLETE",
        snapshot_metadata={"realized_pnl": "10", "unrealized_pnl": "240"},
    )
    repo.add_snapshot(
        db_session,
        portfolio_id=pid,
        snapshot_at=_at(10),
        total_value=D("1250"),
        cash_value=D("1000"),
        invested_value=D("250"),
        reporting_currency="USD",
        valuation_status="COMPLETE",
        snapshot_metadata={"realized_pnl": "50", "unrealized_pnl": "300"},
    )
    db_session.commit()

    r = client.get(
        f"/api/v1/portfolios/{portfolio_id}/performance",
        params={"start": "2026-01-01T00:00:00Z", "end": "2026-01-10T00:00:00Z"},
    )
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["return_status"] == "AVAILABLE"
    assert body["sub_period_count"] == 1
    # Returns are fixed-scale decimal strings, never JSON numbers.
    assert body["twr"] == "0.250000000000"
    assert body["simple_return"] == "0.250000000000"
    assert isinstance(body["twr"], str)
    assert body["realized_pnl"] == "50"
    assert body["unrealized_pnl"] == "300"


def test_performance_endpoint_rejects_bad_date(client, portfolio_id):
    r = client.get(f"/api/v1/portfolios/{portfolio_id}/performance", params={"start": "not-a-date"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_performance_endpoint_unknown_portfolio(client):
    r = client.get(f"/api/v1/portfolios/{uuid.uuid4()}/performance")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"
