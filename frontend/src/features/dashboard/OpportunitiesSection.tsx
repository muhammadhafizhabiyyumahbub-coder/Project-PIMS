"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Badge, DeltaText } from "@/components/Badge";
import { formatPrice, formatScore, formatUtc } from "@/lib/format";
import { ApiRequestError, getOpportunities, refreshMarketData, runScanner } from "@/services/api";
import type { Opportunity } from "@/types/api";

type MarketFilter = "ALL" | "CRYPTO" | "US" | "IDX";
type QualificationFilter = "ALL" | "QUALIFIED" | "PARTIAL" | "NOT_QUALIFIED" | "STALE";
type SortField = "scanner_score" | "daily_change" | "symbol" | "updated_at";

const MARKETS: { id: MarketFilter; label: string }[] = [
  { id: "ALL", label: "All Markets" },
  { id: "CRYPTO", label: "Crypto" },
  { id: "US", label: "US Stocks" },
  { id: "IDX", label: "IDX" },
];

const QUALIFICATIONS: { id: QualificationFilter; label: string }[] = [
  { id: "ALL", label: "All Status" },
  { id: "QUALIFIED", label: "Qualified" },
  { id: "PARTIAL", label: "Partial" },
  { id: "NOT_QUALIFIED", label: "Not Qualified" },
  { id: "STALE", label: "Stale" },
];

const SORTS: { id: SortField; label: string }[] = [
  { id: "scanner_score", label: "Scanner Score" },
  { id: "daily_change", label: "Daily Change" },
  { id: "updated_at", label: "Last Update" },
  { id: "symbol", label: "Symbol" },
];

const TAB_BASE =
  "px-2.5 py-1 rounded text-[11px] font-medium border transition-colors focus-visible:outline focus-visible:outline-accent";
const TAB_OFF = `${TAB_BASE} border-line text-ink2 hover:bg-hover`;
const TAB_ON = `${TAB_BASE} bg-accent-bg text-accent border-accent-line`;

export default function OpportunitiesSection() {
  const [rows, setRows] = useState<Opportunity[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [market, setMarket] = useState<MarketFilter>("ALL");
  const [qualification, setQualification] = useState<QualificationFilter>("ALL");
  const [sort, setSort] = useState<SortField>("scanner_score");
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const loading = rows === null && loadError === null;

  const fetchRows = useCallback(async (): Promise<Opportunity[]> => {
    const envelope = await getOpportunities({ market, qualification, sort });
    return envelope.data;
  }, [market, qualification, sort]);

  useEffect(() => {
    let cancelled = false;
    fetchRows()
      .then((data) => {
        if (!cancelled) {
          setRows(data);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setRows(null);
          setLoadError(
            error instanceof ApiRequestError ? error.message : "Unexpected error loading scanner results.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [fetchRows, reloadKey]);

  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  const runAction = useCallback(
    async (id: string) => {
      setActionBusy(id);
      setActionMessage(null);
      try {
        if (id === "refresh") {
          const envelope = await refreshMarketData("1h");
          const refreshed = envelope.data.refreshed_candles;
          const total = Object.values(refreshed).reduce((sum, n) => sum + n, 0);
          setActionMessage(`Market data refreshed: ${total} candles stored.`);
        } else if (id === "scanner") {
          const envelope = await runScanner("1h");
          const run = envelope.data;
          if (run.execution_status !== "COMPLETED") {
            setActionMessage(`Scanner finished with status ${run.execution_status}.`);
          } else {
            setActionMessage(`Scan complete: ${run.result_count ?? 0} of ${run.universe_size ?? 0} instruments eligible.`);
          }
        }
        setRows(await fetchRows());
        setLoadError(null);
      } catch (error) {
        setActionMessage(
          error instanceof ApiRequestError ? `Action failed: ${error.message}` : "Action failed unexpectedly.",
        );
      } finally {
        setActionBusy(null);
      }
    },
    [fetchRows],
  );

  return (
    <section aria-label="Instrument opportunities" className="bg-card border border-line rounded-lg">
      <header className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-line">
        <div>
          <h2 className="text-[15px] font-semibold">Instrument Opportunities</h2>
          <p className="text-[11px] text-ink3">Scanner-detected instruments. Not a guarantee of future price movement.</p>
        </div>
        <div className="flex items-center gap-2">
          {actionMessage && <span className="text-[11px] text-ink2 max-w-[280px]">{actionMessage}</span>}
          <button
            type="button"
            disabled={actionBusy !== null}
            onClick={() => void runAction("refresh")}
            className={TAB_OFF}
          >
            {actionBusy === "refresh" ? "Refreshing…" : "Refresh Data"}
          </button>
          <button
            type="button"
            disabled={actionBusy !== null}
            onClick={() => void runAction("scanner")}
            className={TAB_ON}
          >
            {actionBusy === "scanner" ? "Scanning…" : "Run Scanner"}
          </button>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5 border-b border-line">
        <FilterGroup
          ariaLabel="Filter by market"
          options={MARKETS}
          active={market}
          onChange={setMarket}
          renderId={(id) => id}
        />
        <FilterGroup
          ariaLabel="Filter by qualification"
          options={QUALIFICATIONS}
          active={qualification}
          onChange={setQualification}
          renderId={(id) => id}
        />
        <label className="flex items-center gap-1.5 text-[11px] text-ink2">
          Sort
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as SortField)}
            className="bg-recessed border border-line rounded px-2 py-1 text-[11px] text-ink focus-visible:outline focus-visible:outline-accent"
          >
            {SORTS.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loadError !== null && (
        <div role="alert" className="mx-4 my-3 rounded border border-loss-line bg-loss-bg px-3 py-2 text-[12px] text-loss">
          {loadError}
          <button type="button" onClick={reload} className="ml-2 underline underline-offset-2">
            Retry
          </button>
        </div>
      )}

      {loading && (
        <div className="px-4 py-10 text-center text-[12px] text-ink3" aria-live="polite">
          Loading scanner results…
        </div>
      )}

      {rows !== null && rows.length === 0 && loadError === null && (
        <div className="px-4 py-10 text-center">
          <p className="text-[13px] text-ink2">
            {qualification !== "ALL" || market !== "ALL"
              ? "No instruments match the current filters."
              : "No scanner results yet. Run the scanner to evaluate the market universe."}
          </p>
        </div>
      )}

      {rows !== null && rows.length > 0 && (
        <ul className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 p-4">
          {rows.map((row) => (
            <OpportunityCard key={row.instrument.symbol} row={row} />
          ))}
        </ul>
      )}
    </section>
  );
}

function FilterGroup<T extends string>({
  ariaLabel,
  options,
  active,
  onChange,
}: {
  ariaLabel: string;
  options: { id: T; label: string }[];
  active: T;
  onChange: (id: T) => void;
  renderId?: (id: T) => string;
}) {
  return (
    <div role="group" aria-label={ariaLabel} className="flex items-center gap-1">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          aria-pressed={active === option.id}
          onClick={() => onChange(option.id)}
          className={active === option.id ? TAB_ON : TAB_OFF}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function OpportunityCard({ row }: { row: Opportunity }) {
  return (
    <li className="bg-recessed border border-line rounded-md hover:border-line-strong transition-colors">
      <Link
        href={`/instrument/${encodeURIComponent(row.instrument.symbol)}`}
        className="flex flex-col gap-2.5 p-3.5 focus-visible:outline focus-visible:outline-accent rounded-md"
      >
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <span className="font-mono text-[13px] font-semibold">{row.instrument.symbol}</span>
            <span className="ml-2 text-[11px] text-ink3 truncate">{row.market ?? "UNKNOWN"}</span>
            <p className="text-[11px] text-ink3 truncate">{row.instrument.name}</p>
          </div>
          <Badge label={row.approval_status} />
        </div>

        <div className="flex items-baseline justify-between gap-2">
          <span className="font-mono text-[17px] font-semibold tabular-nums">
            {formatPrice(row.current_price)}
            {row.quote_currency ? <span className="text-[11px] text-ink3 ml-1">{row.quote_currency}</span> : null}
          </span>
          <span className="text-[12px]">
            <DeltaText value={row.daily_change_pct} />
          </span>
        </div>

        <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-[11px]">
          <Metric label="Score" value={<span className="font-mono tabular-nums">{formatScore(row.scanner_score)}</span>} />
          <Metric
            label="Rank"
            value={row.scanner_rank !== null ? <span className="font-mono tabular-nums">#{row.scanner_rank}</span> : <span className="text-ink3">—</span>}
          />
          <Metric label="Regime" value={row.market_regime ?? <span className="text-ink3">—not available</span>} />
          <Metric label="Risk" value={row.risk_status ?? <span className="text-ink3">not available</span>} />
        </div>

        {row.passed_by.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {row.passed_by.map((engine) => (
              <Badge key={engine} label={engine} mono />
            ))}
          </div>
        ) : (
          <p className="text-[11px] text-ink3">No engines passed yet.</p>
        )}

        <div className="flex items-center justify-between text-[10px] text-ink3 border-t border-line pt-2">
          <span>Data {row.data_status}</span>
          <span>Updated {formatUtc(row.updated_at)}</span>
        </div>
      </Link>
    </li>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 min-w-0">
      <span className="text-ink3 shrink-0">{label}</span>
      <span className="text-ink2 truncate">{value}</span>
    </div>
  );
}
