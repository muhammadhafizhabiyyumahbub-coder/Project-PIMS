"""Performance engine: Time-Weighted Return and companions.

Methodology approved by the Project Owner on 2026-11-17 (technical-decisions.md
§7.10, portfolio-engine-spec §10.6):

- Primary metric is TIME-WEIGHTED RETURN, spec §10.3:
      TWR = (prod(1 + r_i)) - 1
  The period is split at every external cash flow (DEPOSIT / WITHDRAWAL), so
  the timing and size of contributions do not change the measured return.
- Sub-period return (owner-specified):
      r_i = (EMV_i - CF_i) / BMV_i - 1
  CF_i is the NET external cash flow at/end of sub-period i, taken from
  cash_ledger entries: deposit positive, withdrawal negative.
- SIMPLE RETURN (spec §10.2) is reported ONLY when the period contains no
  external cash flow at all. Otherwise it is null with an explicit reason.
- MWR / IRR / XIRR are deferred (need a solver) and are NOT computed here.
- CAGR (spec §10.5) is reported only when TWR is available, beginning value
  is > 0, years > 0, and the requested period is >= 365 days.
- Boundary valuations come from STORED SNAPSHOTS only. A snapshot further than
  SNAPSHOT_TOLERANCE from the required timestamp makes TWR UNAVAILABLE with a
  reason; nothing is invented or interpolated (spec §8.4, §11.2).
- All arithmetic is Decimal. Returns leave the API as fixed-scale decimal
  strings (RETURN_SCALE places), never JSON floats.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext

from sqlalchemy.orm import Session

from app.database.repositories import portfolio as repo
from app.engines.portfolio.holdings import quantize
from app.schemas.portfolio import serialize_money

EXTERNAL_FLOW_TYPES = {"DEPOSIT", "WITHDRAWAL"}
# Owner decision §7.10: a boundary valuation must sit within this window of the
# required timestamp. Wider windows are not allowed because they would silently
# substitute a valuation taken at a materially different time.
SNAPSHOT_TOLERANCE = timedelta(days=1)
# Owner decision §7.10 rule 7: returns are serialized with an explicit scale.
RETURN_SCALE = Decimal("0.000000000001")  # 12 decimal places
CAGR_MIN_DAYS = 365
SECONDS_PER_YEAR = Decimal(365 * 24 * 60 * 60)

ZERO = Decimal(0)
ONE = Decimal(1)


@dataclass
class SnapshotPoint:
    """One stored valuation used as a sub-period boundary."""

    at: datetime
    total_value: Decimal | None
    valuation_status: str = "UNKNOWN"
    status_reason: str | None = None
    realized_pnl: str | None = None
    unrealized_pnl: str | None = None


@dataclass
class CashFlowPoint:
    """One external cash flow; deposit positive, withdrawal negative."""

    at: datetime
    amount: Decimal


@dataclass
class PerformanceResult:
    portfolio_id: uuid.UUID
    reporting_currency: str
    period_start: datetime | None
    period_end: datetime | None
    period_days: int | None
    return_status: str  # AVAILABLE | UNAVAILABLE
    twr: Decimal | None
    twr_reason: str | None
    simple_return: Decimal | None
    simple_return_reason: str | None
    sub_period_count: int
    cagr: Decimal | None
    cagr_reason: str | None
    realized_pnl: str | None
    unrealized_pnl: str | None


def serialize_return(value: Decimal | None) -> str | None:
    """Fixed-scale decimal string (owner decision §7.10 rule 7). None stays None."""
    if value is None:
        return None
    return format(Decimal(str(value)).quantize(RETURN_SCALE), "f")


def _nearest_snapshot(
    snapshots: list[SnapshotPoint], at: datetime
) -> tuple[SnapshotPoint | None, timedelta | None]:
    best: SnapshotPoint | None = None
    best_gap: timedelta | None = None
    for snapshot in snapshots:
        gap = abs(snapshot.at - at)
        if best_gap is None or gap < best_gap:
            best, best_gap = snapshot, gap
    return best, best_gap


def _is_aware(moment: datetime) -> bool:
    return moment.tzinfo is not None and moment.utcoffset() is not None


def compute_performance(
    portfolio_id: uuid.UUID,
    reporting_currency: str,
    snapshots: list[SnapshotPoint],
    cash_flows: list[CashFlowPoint],
    start: datetime | None = None,
    end: datetime | None = None,
) -> PerformanceResult:
    """Pure TWR calculation over stored snapshots and external cash flows.

    No database access, no floats. Expected values for the tests are
    hand-computed in test_performance.py.
    """
    ordered = sorted(snapshots, key=lambda s: s.at)
    flows = sorted(
        (f for f in cash_flows if f.amount != ZERO),
        key=lambda f: f.at,
    )

    if start is None or end is None:
        if len(ordered) < 2:
            return _unavailable(
                portfolio_id,
                reporting_currency,
                start,
                end,
                0,
                "Fewer than two stored snapshots: there is no period to measure.",
            )
        start = start if start is not None else ordered[0].at
        end = end if end is not None else ordered[-1].at

    if end <= start:
        return _unavailable(
            portfolio_id,
            reporting_currency,
            start,
            end,
            0,
            "Period end must be after period start.",
        )

    period_days = (end - start).days

    # Sub-period boundaries: period start, every external cash flow strictly
    # inside the period, then period end. A flow exactly at `start` belongs to
    # the period before (it is the opening contribution, not a mid-period one).
    boundaries = [start]
    for flow in flows:
        if start < flow.at < end and flow.at != boundaries[-1]:
            boundaries.append(flow.at)
    boundaries.append(end)

    in_period_flows = [f for f in flows if start < f.at <= end]

    sub_returns: list[Decimal] = []
    for index in range(len(boundaries) - 1):
        begin_at, end_at = boundaries[index], boundaries[index + 1]
        begin, begin_gap = _nearest_snapshot(ordered, begin_at)
        finish, finish_gap = _nearest_snapshot(ordered, end_at)
        problem = _boundary_problem(begin, begin_gap, begin_at, "start")
        if problem is None:
            problem = _boundary_problem(finish, finish_gap, end_at, "end")
        if problem is not None:
            return _unavailable(
                portfolio_id,
                reporting_currency,
                start,
                end,
                len(boundaries) - 1,
                problem,
            )
        assert begin is not None and finish is not None  # narrowed by _boundary_problem
        if begin.total_value is None:
            return _unavailable(
                portfolio_id,
                reporting_currency,
                start,
                end,
                len(boundaries) - 1,
                f"Snapshot at {begin.at.isoformat()} has no total value "
                f"({_reason_for_status(begin)}).",
            )
        if finish.total_value is None:
            return _unavailable(
                portfolio_id,
                reporting_currency,
                start,
                end,
                len(boundaries) - 1,
                f"Snapshot at {finish.at.isoformat()} has no total value "
                f"({_reason_for_status(finish)}).",
            )

        bmv = Decimal(str(begin.total_value))
        emv = Decimal(str(finish.total_value))
        if bmv <= ZERO:
            return _unavailable(
                portfolio_id,
                reporting_currency,
                start,
                end,
                len(boundaries) - 1,
                f"Beginning value is {serialize_money(bmv)}; a return cannot be "
                "divided by a non-positive value.",
            )
        flow = sum(
            (f.amount for f in in_period_flows if begin_at < f.at <= end_at),
            ZERO,
        )
        # Fixed 50-digit precision: the default 28 already covers a handful of
        # sub-periods, but pinning it here keeps replays bit-for-bit identical.
        with localcontext() as ctx:
            ctx.prec = 50
            ratio = (emv - flow) / bmv
        sub_returns.append(ratio - ONE)

    with localcontext() as ctx:
        ctx.prec = 50
        twr = ONE
        for sub in sub_returns:
            twr *= ONE + sub
        twr -= ONE

    no_flows = not in_period_flows
    simple_return: Decimal | None = None
    simple_reason: str | None = None
    if no_flows:
        # A single sub-period, so TWR and simple return are the same number.
        first, _ = _nearest_snapshot(ordered, start)
        last, _ = _nearest_snapshot(ordered, end)
        assert first is not None and last is not None
        first_value = Decimal(str(first.total_value))
        last_value = Decimal(str(last.total_value))
        with localcontext() as ctx:
            ctx.prec = 50
            simple_return = (last_value - first_value) / first_value
    else:
        simple_reason = (
            "Simple return is not reported: the period contains external cash "
            "flows, so it would mix contributions with performance (spec §10.2)."
        )

    end_snapshot, _ = _nearest_snapshot(ordered, end)
    realized = end_snapshot.realized_pnl if end_snapshot else None
    unrealized = end_snapshot.unrealized_pnl if end_snapshot else None

    cagr, cagr_reason = _compute_cagr(twr, ordered, start, end, period_days)

    return PerformanceResult(
        portfolio_id=portfolio_id,
        reporting_currency=reporting_currency,
        period_start=start,
        period_end=end,
        period_days=period_days,
        return_status="AVAILABLE",
        twr=quantize(twr),
        twr_reason=None,
        simple_return=quantize(simple_return) if simple_return is not None else None,
        simple_return_reason=simple_reason,
        sub_period_count=len(sub_returns),
        cagr=quantize(cagr) if cagr is not None else None,
        cagr_reason=cagr_reason,
        realized_pnl=realized,
        unrealized_pnl=unrealized,
    )


def _reason_for_status(snapshot: SnapshotPoint) -> str:
    """Why a stored snapshot cannot serve as a boundary valuation."""
    if snapshot.status_reason:
        return f"{snapshot.valuation_status}: {snapshot.status_reason}"
    return f"valuation_status is {snapshot.valuation_status}"


def _boundary_problem(
    snapshot: SnapshotPoint | None,
    gap: timedelta | None,
    at: datetime,
    label: str,
) -> str | None:
    if snapshot is None:
        return (
            f"No stored snapshot exists to value the {label} of a sub-period at "
            f"{at.isoformat()}; TWR is unavailable rather than estimated."
        )
    assert gap is not None
    if gap > SNAPSHOT_TOLERANCE:
        return (
            f"No stored snapshot within {SNAPSHOT_TOLERANCE.days} day of "
            f"{at.isoformat()} (closest is {snapshot.at.isoformat()}, "
            f"{gap.total_seconds() / 86400:.2f} day(s) away); TWR is unavailable "
            "rather than interpolated."
        )
    return None


def _compute_cagr(
    twr: Decimal,
    snapshots: list[SnapshotPoint],
    start: datetime,
    end: datetime,
    period_days: int,
) -> tuple[Decimal | None, str | None]:
    """CAGR from the TWR series (spec §10.5), gated by the owner's conditions.

    When the period has no external cash flow, TWR equals the simple return, so
    this reduces exactly to ((EndingValue / BeginningValue) ** (1/Years)) - 1.
    """
    if period_days < CAGR_MIN_DAYS:
        return None, (
            f"CAGR requires a period of at least {CAGR_MIN_DAYS} days; this period "
            f"is {period_days} day(s)."
        )
    first, _ = _nearest_snapshot(snapshots, start)
    if first is None or first.total_value is None:
        return None, "Beginning value is unavailable, so CAGR cannot be computed."
    bmv = Decimal(str(first.total_value))
    if bmv <= ZERO:
        return None, (
            f"Beginning value is {serialize_money(bmv)}; CAGR requires a "
            "beginning value greater than zero."
        )
    years = Decimal((end - start).total_seconds()) / SECONDS_PER_YEAR
    if years <= ZERO:
        return None, "Period is shorter than a year fraction, so CAGR is undefined."
    growth = ONE + twr
    if growth <= ZERO:
        return None, "Portfolio value did not survive the period; CAGR is undefined."
    with localcontext() as ctx:
        ctx.prec = 50
        cagr = (growth ** (ONE / years)) - ONE
    return cagr, None


def _unavailable(
    portfolio_id: uuid.UUID,
    reporting_currency: str,
    start: datetime | None,
    end: datetime | None,
    sub_period_count: int,
    reason: str,
) -> PerformanceResult:
    return PerformanceResult(
        portfolio_id=portfolio_id,
        reporting_currency=reporting_currency,
        period_start=start,
        period_end=end,
        period_days=(end - start).days if start is not None and end is not None else None,
        return_status="UNAVAILABLE",
        twr=None,
        twr_reason=reason,
        simple_return=None,
        simple_return_reason=(
            "Simple return is not reported while the period return is unavailable."
        ),
        sub_period_count=sub_period_count,
        cagr=None,
        cagr_reason="CAGR is not reported while the period return is unavailable.",
        realized_pnl=None,
        unrealized_pnl=None,
    )


def _as_utc(moment: datetime) -> datetime:
    """Naive timestamps are read as UTC so comparisons never mix offsets."""
    if not _is_aware(moment):
        return moment.replace(tzinfo=UTC)
    return moment


def performance_for_portfolio(
    session: Session,
    portfolio_id: uuid.UUID,
    start: datetime | None = None,
    end: datetime | None = None,
) -> PerformanceResult:
    """Load stored snapshots + external cash flows and compute performance.

    Read-only: nothing is persisted (persistence is a separate round).
    """
    portfolio = repo.get_portfolio(session, portfolio_id)
    if portfolio is None:
        raise ValueError(f"portfolio {portfolio_id} not found")
    currency = portfolio.reporting_currency

    snapshots = [
        SnapshotPoint(
            at=_as_utc(row.snapshot_at),
            total_value=(Decimal(str(row.total_value)) if row.total_value is not None else None),
            valuation_status=row.valuation_status,
            status_reason=(row.snapshot_metadata or {}).get("status_reason"),
            realized_pnl=(row.snapshot_metadata or {}).get("realized_pnl"),
            unrealized_pnl=(row.snapshot_metadata or {}).get("unrealized_pnl"),
        )
        for row in repo.list_snapshots_in_range(session, portfolio_id)
    ]
    # External flows come from the cash ledger, not from BUY/SELL: only
    # DEPOSIT/WITHDRAWAL move money in or out of the portfolio (spec §10.3).
    flows = [
        CashFlowPoint(at=_as_utc(entry.effective_at), amount=Decimal(str(entry.amount)))
        for entry in repo.ledger_entries(session, portfolio_id)
        if entry.entry_type in EXTERNAL_FLOW_TYPES
    ]

    return compute_performance(
        portfolio_id=portfolio_id,
        reporting_currency=currency,
        snapshots=snapshots,
        cash_flows=flows,
        start=_as_utc(start) if start is not None else None,
        end=_as_utc(end) if end is not None else None,
    )
