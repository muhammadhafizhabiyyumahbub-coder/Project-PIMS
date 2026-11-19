"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { formatMoneyString, formatReturnPct, formatUtc, pnlTone } from "@/lib/format";
import { ApiRequestError, getRisk } from "@/services/api";
import type { PortfolioRisk, RiskMetrics } from "@/types/api";

const WINDOWS = [30, 90, 180, 365] as const;

/**
 * Risk panel (Stage M). Pure presentation over the backend risk endpoint.
 * Every metric is a decimal-fraction string rendered verbatim: null means the
 * backend could not compute it, and its reason from metric_reasons is shown
 * instead. The client never computes, estimates or zero-fills a metric.
 */
export default function RiskPanel({
  portfolioId,
  windowDays,
  onWindowChange,
}: {
  portfolioId: string;
  /** Lifted to the page so "Simpan analisis" can persist the chosen window. */
  windowDays: number;
  onWindowChange: (windowDays: number) => void;
}) {
  const [risk, setRisk] = useState<PortfolioRisk | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getRisk(portfolioId, windowDays)
      .then((response) => {
        if (cancelled) return;
        setRisk(response.data);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setRisk(null);
        setLoadError(error instanceof ApiRequestError ? error.message : "Could not load risk.");
      });
    return () => {
      cancelled = true;
    };
  }, [portfolioId, windowDays, reloadKey]);

  const retry = useCallback(() => setReloadKey((k) => k + 1), []);

  return (
    <section aria-label="Risiko" className="bg-card border border-line rounded-lg">
      <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-line">
        <div>
          <h2 className="text-[15px] font-semibold">Risiko</h2>
          <p className="text-[11px] text-ink3">
            Aproksimasi komposisi saat ini (buy &amp; hold) — bukan kinerja historis aktual.
          </p>
        </div>
        <label className="flex items-center gap-2 text-[11px] text-ink2">
          Window
          <select
            value={windowDays}
            onChange={(event) => onWindowChange(Number(event.target.value))}
            className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink focus-visible:outline focus-visible:outline-accent"
          >
            {WINDOWS.map((days) => (
              <option key={days} value={days}>
                {days} hari
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
      ) : risk === null ? (
        <p aria-live="polite" className="px-4 py-8 text-center text-[12px] text-ink3">
          Loading risk...
        </p>
      ) : (
        <RiskBody risk={risk} />
      )}
    </section>
  );
}

function RiskBody({ risk }: { risk: PortfolioRisk }) {
  const unavailable = risk.data_status !== "AVAILABLE";
  return (
    <>
      {unavailable && (
        <div role="status" className="px-4 py-3 border-b border-line text-[11px] text-ink2">
          <Badge label={risk.data_status} />
          <p className="pt-1.5">
            {risk.data_status_reason ?? "Tidak ada data risiko tersedia untuk window ini."}
          </p>
        </div>
      )}

      <dl className="grid grid-cols-2 md:grid-cols-3 gap-3 px-4 py-3">
        <FractionMetric label="Volatilitas harian" value={risk.metrics.volatility} />
        <FractionMetric
          label="Volatilitas annualized"
          value={risk.metrics.annualized_volatility}
        />
        <FractionMetric
          label="Max drawdown"
          value={risk.metrics.max_drawdown}
          tone={pnlTone(risk.metrics.max_drawdown)}
        />
        <RatioMetric label="Sharpe" value={risk.metrics.sharpe} />
        <RatioMetric label="Sortino" value={risk.metrics.sortino} />
        <FractionMetric label="VaR 95%" value={risk.metrics.var_95} />
        <FractionMetric label="VaR 99%" value={risk.metrics.var_99} />
        <FractionMetric label="CVaR 95%" value={risk.metrics.cvar_95} />
        <FractionMetric label="CVaR 99%" value={risk.metrics.cvar_99} />
      </dl>

      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 px-4 pb-3 border-t border-line pt-3">
        <TextMetric label="Metode" value={risk.method} />
        <TextMetric
          label="Risk-free rate"
          value={formatReturnPct(risk.risk_free_rate)}
        />
        <TextMetric
          label="Annualization"
          value={`${risk.annualization} (${risk.annualization_factor})`}
        />
        <TextMetric label="Observasi" value={`${risk.return_count} return harian`} />
        <TextMetric label="Periode diamati" value={`${formatUtc(risk.observation_start)} — ${formatUtc(risk.observation_end)}`} />
        <TextMetric label="Dasar bobot" value={risk.weight_base} />
        <TextMetric label="Sumber harga" value={risk.price_source || "—"} />
        <TextMetric label="Mata uang" value={risk.reporting_currency} />
      </dl>

      <MetricReasons reasons={risk.metric_reasons} metrics={risk.metrics} />

      <p className="px-4 pb-3 text-[10px] text-ink3 border-t border-line pt-2">
        Volatilitas, drawdown, VaR dan CVaR adalah pecahan desimal (mis. -0.034 = -3.4%);
        risiko dihitung atas komposisi bobot saat ini, bukan urutan transaksi historis.
        Angka berasal dari backend; UI tidak menghitung ulang.
      </p>
    </>
  );
}

function MetricReasons({
  reasons,
  metrics,
}: {
  reasons: Record<string, string>;
  metrics: RiskMetrics;
}) {
  const entries = Object.entries(reasons).filter(([key]) => metrics[key as keyof RiskMetrics] === null);
  if (entries.length === 0) return null;
  return (
    <div className="px-4 pb-3 flex flex-col gap-1 border-t border-line pt-3">
      {entries.map(([key, reason]) => (
        <p key={key} className="text-[11px] text-ink3">
          <span className="font-mono">{key}</span>: {reason}
        </p>
      ))}
    </div>
  );
}

function FractionMetric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string | null;
  tone?: string;
}) {
  return (
    <Metric
      label={label}
      value={
        value === null ? (
          <NotAvailable />
        ) : (
          <span className={tone ?? "text-ink"}>{formatReturnPct(value)}</span>
        )
      }
    />
  );
}

/** Sharpe/Sortino are ratios, not fractions: shown as sent, never as a percent. */
function RatioMetric({ label, value }: { label: string; value: string | null }) {
  return (
    <Metric
      label={label}
      value={value === null ? <NotAvailable /> : <span className="text-ink">{formatMoneyString(value)}</span>}
    />
  );
}

function TextMetric({ label, value }: { label: string; value: string }) {
  return (
    <Metric
      label={label}
      value={<span className="text-ink2 text-[12px] font-sans font-normal">{value}</span>}
    />
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

function NotAvailable() {
  return <span className="text-ink3 text-[12px] font-sans font-normal">tidak tersedia</span>;
}