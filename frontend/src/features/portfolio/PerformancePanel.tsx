"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { formatReturnPct, formatSignedMoneyString, formatUtc, pnlTone } from "@/lib/format";
import { ApiRequestError, getPerformance } from "@/services/api";
import type { PortfolioPerformance } from "@/types/api";

const PERIODS = [
  { key: "ALL", label: "Semua" },
  { key: "30D", label: "30 hari" },
  { key: "90D", label: "90 hari" },
  { key: "1Y", label: "1 tahun" },
] as const;

type PeriodKey = (typeof PERIODS)[number]["key"];

/**
 * Window start for a period choice. This is the only date the UI computes; the
 * measured period itself always comes back from the backend (period_start /
 * period_end), so the UI never decides what was actually measured. "Semua"
 * sends no bound, which lets the backend use the whole stored history.
 */
function startFor(key: PeriodKey): string | undefined {
  if (key === "ALL") return undefined;
  const days = key === "30D" ? 30 : key === "90D" ? 90 : 365;
  return new Date(Date.now() - days * 86_400_000).toISOString();
}

export default function PerformancePanel({ portfolioId }: { portfolioId: string }) {
  const [period, setPeriod] = useState<PeriodKey>("ALL");
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getPerformance(portfolioId, { start: startFor(period) })
      .then((response) => {
        if (cancelled) return;
        setPerformance(response.data);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setPerformance(null);
        setLoadError(
          error instanceof ApiRequestError ? error.message : "Could not load performance.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [portfolioId, period, reloadKey]);

  const retry = useCallback(() => setReloadKey((k) => k + 1), []);

  return (
    <section aria-label="Portfolio performance" className="bg-card border border-line rounded-lg">
      <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-line">
        <div>
          <h2 className="text-[15px] font-semibold">Performa</h2>
          <p className="text-[11px] text-ink3">
            TWR menetralkan pengaruh deposit/withdrawal; simple return tidak. Keduanya ukuran
            berbeda dan tidak boleh saling dipertukarkan (spec §10.2 vs §10.3).
          </p>
        </div>
        <label className="flex items-center gap-2 text-[11px] text-ink2">
          Periode
          <select
            value={period}
            onChange={(event) => setPeriod(event.target.value as PeriodKey)}
            className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink focus-visible:outline focus-visible:outline-accent"
          >
            {PERIODS.map((p) => (
              <option key={p.key} value={p.key}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
      </header>

      {loadError !== null ? (
        <div role="alert" className="px-4 py-3 text-[12px] text-loss">
          {loadError.split(".")[0] === "Cannot reach the PIMS backend."
            ? "Backend is not reachable. Open portfolios once the backend is running on port 8000."
            : loadError}
          <button type="button" onClick={retry} className="ml-2 underline underline-offset-2">
            Retry
          </button>
        </div>
      ) : performance === null ? (
        <p aria-live="polite" className="px-4 py-8 text-center text-[12px] text-ink3">
          Loading performance...
        </p>
      ) : (
        <PerformanceBody performance={performance} />
      )}
    </section>
  );
}

function PerformanceBody({ performance }: { performance: PortfolioPerformance }) {
  const unavailable = performance.return_status === "UNAVAILABLE";
  return (
    <>
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 px-4 py-3">
        <Metric
          label="TWR (time-weighted)"
          value={
            performance.twr === null ? (
              <span className="text-ink3 text-[12px] font-sans font-normal">tidak tersedia</span>
            ) : (
              <span className={pnlTone(performance.twr)}>{formatReturnPct(performance.twr)}</span>
            )
          }
        />
        <Metric
          label="Simple return"
          value={
            performance.simple_return === null ? (
              <span className="text-ink3 text-[12px] font-sans font-normal">tidak tersedia</span>
            ) : (
              <span className={pnlTone(performance.simple_return)}>
                {formatReturnPct(performance.simple_return)}
              </span>
            )
          }
        />
        <Metric
          label="Realized P&L"
          value={
            performance.realized_pnl === null ? (
              <span className="text-ink3 text-[12px] font-sans font-normal">tidak tersedia</span>
            ) : (
              <span className={pnlTone(performance.realized_pnl)}>
                {formatSignedMoneyString(performance.realized_pnl)}
              </span>
            )
          }
        />
        <Metric
          label="Unrealized P&L"
          value={
            performance.unrealized_pnl === null ? (
              <span className="text-ink3 text-[12px] font-sans font-normal">tidak tersedia</span>
            ) : (
              <span className={pnlTone(performance.unrealized_pnl)}>
                {formatSignedMoneyString(performance.unrealized_pnl)}
              </span>
            )
          }
        />
      </dl>

      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 px-4 pb-3 border-t border-line pt-3">
        <Metric
          label="CAGR"
          value={
            performance.cagr === null ? (
              <span className="text-ink3 text-[12px] font-sans font-normal">tidak tersedia</span>
            ) : (
              <span className={pnlTone(performance.cagr)}>{formatReturnPct(performance.cagr)}</span>
            )
          }
        />
        <Metric
          label="Sub-periode"
          value={<span className="text-ink">{performance.sub_period_count}</span>}
        />
        <Metric
          label="Periode diukur"
          value={
            <span className="text-ink2 text-[12px] font-sans font-normal">
              {formatUtc(performance.period_start)} — {formatUtc(performance.period_end)}
            </span>
          }
        />
        <Metric
          label="Hari"
          value={
            <span className="text-ink2 text-[12px] font-sans font-normal">
              {performance.period_days === null ? "tidak tersedia" : `${performance.period_days} hari`}
            </span>
          }
        />
      </dl>

      {/* Reasons are shown verbatim from the API: null never becomes 0, and the
          UI never hides or recomputes an unavailable return. */}
      {(performance.twr_reason || performance.simple_return_reason || performance.cagr_reason) && (
        <div className="px-4 pb-3 flex flex-col gap-1.5 border-t border-line pt-3">
          {performance.twr_reason && (
            <div className="flex flex-wrap items-center gap-2">
              <Badge label={performance.return_status} />
              <p className="text-[11px] text-ink2">{performance.twr_reason}</p>
            </div>
          )}
          {performance.simple_return_reason && (
            <p className="text-[11px] text-ink3">{performance.simple_return_reason}</p>
          )}
          {performance.cagr_reason && (
            <p className="text-[11px] text-ink3">{performance.cagr_reason}</p>
          )}
        </div>
      )}

      <p className="px-4 py-2 text-[10px] text-ink3 border-t border-line">
        Currency {performance.reporting_currency}.{" "}
        {unavailable
          ? "TWR tidak dapat dihitung untuk periode ini. Angka tidak ditampilkan sebagai 0 dan tidak diestimasi di frontend."
          : "Angka berasal dari backend; UI tidak menghitung ulang return."}
      </p>
    </>
  );
}

function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <dt className="text-[10px] text-ink3">{label}</dt>
      <dd className="text-[14px] font-mono font-semibold tabular-nums truncate">{value}</dd>
    </div>
  );
}
