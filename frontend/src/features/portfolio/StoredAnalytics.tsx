"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { formatMoneyString, formatReturnPct, formatUtc, pnlTone } from "@/lib/format";
import { ApiRequestError, createAnalyticsRun, getAnalyticsRun, listAnalyticsRuns } from "@/services/api";
import type {
  AnalyticsRun,
  AnalyticsRunDetail,
  AnalyticsType,
  StoredAllocationResult,
  StoredPerformanceResult,
  StoredRiskResult,
} from "@/types/api";

const TYPE_LABELS: Record<string, string> = {
  PERFORMANCE: "Performa",
  RISK: "Risiko",
  ALLOCATION: "Alokasi",
};

const SAVE_BUTTONS: { type: AnalyticsType; label: string }[] = [
  { type: "performance", label: "Performa" },
  { type: "risk", label: "Risiko" },
  { type: "allocation", label: "Alokasi" },
];

/**
 * "Analisis tersimpan" (Stage S). The save buttons persist whatever period /
 * window the owner has currently chosen; the backend computes and stores the
 * run. This panel only displays stored rows verbatim: it never recomputes a
 * metric, and a null stays "tidak tersedia", never 0.
 */
export default function StoredAnalytics({
  portfolioId,
  performanceStart,
  riskWindowDays,
}: {
  portfolioId: string;
  /** Current performance period start (undefined = "Semua"); sent to the API. */
  performanceStart: string | undefined;
  /** Current risk window; sent to the API. */
  riskWindowDays: number;
}) {
  const [runs, setRuns] = useState<AnalyticsRun[] | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [savingType, setSavingType] = useState<AnalyticsType | null>(null);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [detail, setDetail] = useState<AnalyticsRunDetail | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listAnalyticsRuns(portfolioId)
      .then((response) => {
        if (cancelled) return;
        setRuns(response.data);
        setHasMore(Boolean((response.meta?.pagination as { has_more?: boolean } | undefined)?.has_more));
        setListError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setRuns([]);
        setHasMore(false);
        setListError(error instanceof ApiRequestError ? error.message : "Could not load stored analyses.");
      });
    return () => {
      cancelled = true;
    };
  }, [portfolioId, reloadKey]);

  const loadMore = useCallback(async () => {
    if (runs === null || runs.length === 0) return;
    setLoadingMore(true);
    try {
      const response = await listAnalyticsRuns(portfolioId, runs[runs.length - 1].id);
      setRuns([...runs, ...response.data]);
      setHasMore(Boolean((response.meta?.pagination as { has_more?: boolean } | undefined)?.has_more));
      setListError(null);
    } catch (error) {
      setListError(error instanceof ApiRequestError ? error.message : "Could not load more analyses.");
    } finally {
      setLoadingMore(false);
    }
  }, [portfolioId, runs]);

  const save = useCallback(
    async (type: AnalyticsType) => {
      setSavingType(type);
      setSaveNotice(null);
      setSaveError(null);
      try {
        const body =
          type === "risk"
            ? { analysis_type: type, window_days: riskWindowDays }
            : type === "performance"
              ? { analysis_type: type, ...(performanceStart ? { start: performanceStart } : {}) }
              : { analysis_type: type };
        const response = await createAnalyticsRun(portfolioId, body);
        const run = response.data.run;
        // Only facts the API returned: id, stored time, status, result count.
        setSaveNotice(
          `Tersimpan ${run.id} — ${formatUtc(run.completed_at ?? run.started_at)} (${run.execution_status}, ${response.data.results.length} baris hasil).`,
        );
        setReloadKey((k) => k + 1);
      } catch (error) {
        setSaveError(
          error instanceof ApiRequestError ? error.message : "Could not save the analysis.",
        );
      } finally {
        setSavingType(null);
      }
    },
    [portfolioId, performanceStart, riskWindowDays],
  );

  const openDetail = useCallback(
    async (runId: string) => {
      setDetailId(runId);
      setDetail(null);
      setDetailError(null);
      try {
        const response = await getAnalyticsRun(portfolioId, runId);
        setDetail(response.data);
      } catch (error) {
        setDetailError(
          error instanceof ApiRequestError ? error.message : "Could not load the stored run.",
        );
      }
    },
    [portfolioId],
  );

  const disconnected = (message: string) => message.split(".")[0] === "Cannot reach the PIMS backend.";

  return (
    <section aria-label="Analisis tersimpan" className="bg-card border border-line rounded-lg">
      <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-line">
        <div>
          <h2 className="text-[15px] font-semibold">Analisis tersimpan</h2>
          <p className="text-[11px] text-ink3">
            Analisis disimpan hanya saat Anda menekan tombol. Tidak ada penjadwalan otomatis.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {SAVE_BUTTONS.map(({ type, label }) => (
            <button
              key={type}
              type="button"
              onClick={() => void save(type)}
              disabled={savingType !== null}
              className="bg-accent-bg text-accent border border-accent-line rounded px-3 py-1.5 text-[12px] font-medium hover:bg-hover disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
            >
              {savingType === type ? "Menyimpan…" : `Simpan ${label}`}
            </button>
          ))}
        </div>
      </header>

      {saveNotice && (
        <p role="status" className="px-4 py-2 text-[11px] text-gain border-b border-line break-all">
          {saveNotice}
        </p>
      )}
      {saveError && (
        <p role="alert" className="px-4 py-2 text-[11px] text-loss border-b border-line">
          {disconnected(saveError)
            ? "Backend tidak dapat dijangkau. Jalankan backend pada port 8000 lalu coba lagi."
            : saveError}
        </p>
      )}

      {listError && (
        <div role="alert" className="px-4 py-3 text-[12px] text-loss">
          {disconnected(listError)
            ? "Backend tidak dapat dijangkau. Jalankan backend pada port 8000 lalu buka kembali halaman ini."
            : listError}
          <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="ml-2 underline underline-offset-2">
            Retry
          </button>
        </div>
      )}

      {runs === null ? (
        <p aria-live="polite" className="px-4 py-8 text-center text-[12px] text-ink3">
          Memuat analisis tersimpan…
        </p>
      ) : runs.length === 0 ? (
        <p className="px-4 py-8 text-center text-[12px] text-ink2">belum ada analisis tersimpan.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-left text-[10px] text-ink3 border-b border-line">
                <th className="px-4 py-2 font-medium">Waktu</th>
                <th className="px-4 py-2 font-medium">Jenis</th>
                <th className="px-4 py-2 font-medium">Window/Periode</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium">Run</th>
                <th className="px-4 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id} className="border-b border-line last:border-b-0">
                  <td className="px-4 py-2 text-[11px] text-ink2 whitespace-nowrap">
                    {formatUtc(run.started_at)}
                  </td>
                  <td className="px-4 py-2">{TYPE_LABELS[run.engine_type] ?? run.engine_type}</td>
                  <td className="px-4 py-2 text-[11px] text-ink2">{runWindow(run)}</td>
                  <td className="px-4 py-2">
                    <Badge label={run.execution_status} />
                  </td>
                  <td className="px-4 py-2 font-mono text-[10px] text-ink3">{run.id}</td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => void openDetail(run.id)}
                      className="border border-line rounded px-2 py-0.5 text-[11px] text-ink2 hover:bg-hover focus-visible:outline focus-visible:outline-accent"
                    >
                      Detail
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {runs !== null && runs.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 border-t border-line">
          <p className="text-[10px] text-ink3">
            Angka disimpan apa adanya dari backend; null ditampilkan &quot;tidak tersedia&quot;, bukan 0.
          </p>
          {hasMore && (
            <button
              type="button"
              onClick={() => void loadMore()}
              disabled={loadingMore}
              className="border border-line rounded px-3 py-1 text-[11px] text-ink2 hover:bg-hover disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
            >
              {loadingMore ? "Memuat…" : "Muat lagi"}
            </button>
          )}
        </div>
      )}

      {detailId !== null && (
        <RunDetail
          runId={detailId}
          detail={detail}
          error={detailError}
          onClose={() => {
            setDetailId(null);
            setDetail(null);
            setDetailError(null);
          }}
        />
      )}
    </section>
  );
}

/** Window/period label straight from the stored run; no inference. */
function runWindow(run: AnalyticsRun): string {
  const meta = run.input_metadata ?? {};
  if (run.engine_type === "RISK" && typeof meta.window_days === "number") {
    return `${meta.window_days} hari`;
  }
  if (run.observation_start && run.observation_end) {
    return `${formatUtc(run.observation_start)} — ${formatUtc(run.observation_end)}`;
  }
  if (run.observation_start) return formatUtc(run.observation_start);
  return "—";
}

function RunDetail({
  runId,
  detail,
  error,
  onClose,
}: {
  runId: string;
  detail: AnalyticsRunDetail | null;
  error: string | null;
  onClose: () => void;
}) {
  return (
    <div className="border-t border-line bg-recessed px-4 py-3 flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-[13px] font-semibold">
          Detail run <span className="font-mono text-[11px] text-ink3">{runId}</span>
        </h3>
        <button
          type="button"
          onClick={onClose}
          className="border border-line rounded px-2 py-0.5 text-[11px] text-ink2 hover:bg-hover focus-visible:outline focus-visible:outline-accent"
        >
          Tutup
        </button>
      </div>
      {error ? (
        <p role="alert" className="text-[12px] text-loss">
          {error}
        </p>
      ) : detail === null ? (
        <p aria-live="polite" className="text-[12px] text-ink3">
          Memuat detail…
        </p>
      ) : detail.results.length === 0 ? (
        <p className="text-[12px] text-ink2">Run ini tidak menyimpan baris hasil.</p>
      ) : (
        <RunResults run={detail.run} detail={detail} />
      )}
    </div>
  );
}

function RunResults({ run, detail }: { run: AnalyticsRun; detail: AnalyticsRunDetail }) {
  if (run.engine_type === "PERFORMANCE") {
    return <PerformanceDetail results={detail.results as StoredPerformanceResult[]} />;
  }
  if (run.engine_type === "RISK") {
    return <RiskDetail results={detail.results as StoredRiskResult[]} />;
  }
  return <AllocationDetail results={detail.results as StoredAllocationResult[]} />;
}

function PerformanceDetail({ results }: { results: StoredPerformanceResult[] }) {
  return (
    <>
      {results.map((r) => (
        <div key={r.id} className="flex flex-col gap-2">
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric label="Periode" value={`${formatUtc(r.period_start)} — ${formatUtc(r.period_end)}`} raw />
            <Metric
              label="Total return (TWR)"
              value={r.total_return === null ? NA : formatReturnPct(r.total_return)}
              tone={r.total_return === null ? undefined : pnlTone(r.total_return)}
            />
            <Metric
              label="CAGR"
              value={r.cagr === null ? NA : formatReturnPct(r.cagr)}
              tone={r.cagr === null ? undefined : pnlTone(r.cagr)}
            />
            <Metric
              label="Daily return"
              value={r.daily_return === null ? NA : formatReturnPct(r.daily_return)}
              tone={r.daily_return === null ? undefined : pnlTone(r.daily_return)}
            />
            <Metric
              label="Realized P&L"
              value={r.realized_pnl === null ? NA : formatMoneyString(r.realized_pnl)}
            />
            <Metric
              label="Unrealized P&L"
              value={r.unrealized_pnl === null ? NA : formatMoneyString(r.unrealized_pnl)}
            />
            <Metric label="Metodologi" value={r.methodology} raw />
            <Metric label="Mata uang" value={r.reporting_currency} raw />
          </dl>
          <MetadataBlock metadata={r.result_metadata} />
        </div>
      ))}
    </>
  );
}

function RiskDetail({ results }: { results: StoredRiskResult[] }) {
  return (
    <>
      {results.map((r) => (
        <div key={r.id} className="flex flex-col gap-2">
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric label="Periode observasi" value={r.observation_period ?? NA} raw />
            <Metric
              label="Volatilitas"
              value={r.volatility === null ? NA : formatReturnPct(r.volatility)}
            />
            <Metric
              label="Max drawdown"
              value={r.max_drawdown === null ? NA : formatReturnPct(r.max_drawdown)}
              tone={r.max_drawdown === null ? undefined : pnlTone(r.max_drawdown)}
            />
            <Metric
              label="Value at Risk"
              value={r.value_at_risk === null ? NA : formatReturnPct(r.value_at_risk)}
            />
            <Metric
              label="Confidence level"
              value={r.confidence_level === null ? NA : formatReturnPct(r.confidence_level)}
            />
            <Metric
              label="Klasifikasi risiko"
              value={r.risk_classification ?? NA}
              raw
            />
          </dl>
          <MetadataBlock metadata={r.result_metadata} />
        </div>
      ))}
    </>
  );
}

function AllocationDetail({ results }: { results: StoredAllocationResult[] }) {
  const metadata = results[0]?.result_metadata ?? {};
  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-[12px]">
          <thead>
            <tr className="text-left text-[10px] text-ink3 border-b border-line">
              <th className="px-3 py-2 font-medium">Jenis</th>
              <th className="px-3 py-2 font-medium">Kategori</th>
              <th className="px-3 py-2 font-medium text-right">Nilai</th>
              <th className="px-3 py-2 font-medium text-right">Bobot</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.id} className="border-b border-line last:border-b-0">
                <td className="px-3 py-2 font-mono text-[11px]">{r.allocation_type}</td>
                <td className="px-3 py-2 font-mono font-semibold">{r.allocation_key}</td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">
                  {r.market_value === null ? NA : formatMoneyString(r.market_value)}
                </td>
                <td className="px-3 py-2 text-right font-mono tabular-nums">
                  {r.allocation_percentage === null ? NA : `${formatMoneyString(r.allocation_percentage)}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <MetadataBlock metadata={metadata} />
    </>
  );
}

/** Renders stored methodology metadata verbatim; null → "tidak tersedia". */
function MetadataBlock({ metadata }: { metadata: Record<string, unknown> }) {
  const entries = Object.entries(metadata);
  if (entries.length === 0) return null;
  return (
    <div className="border border-line rounded bg-card px-3 py-2">
      <h4 className="text-[11px] font-semibold text-ink2 pb-1">Metadata metodologi (apa adanya)</h4>
      <dl className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
        {entries.map(([key, value]) => (
          <div key={key} className="flex gap-2 min-w-0">
            <dt className="font-mono text-ink3 shrink-0">{key}</dt>
            <dd className="font-mono text-ink break-all">{renderMetadataValue(value)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

function renderMetadataValue(value: unknown): string {
  if (value === null || value === undefined) return "tidak tersedia";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

const NA = <span className="text-ink3 text-[12px] font-sans font-normal">tidak tersedia</span>;

function Metric({
  label,
  value,
  tone,
  raw = false,
}: {
  label: string;
  value: React.ReactNode;
  tone?: string;
  raw?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1 min-w-0">
      <dt className="text-[10px] text-ink3">{label}</dt>
      <dd
        className={`text-[14px] font-semibold tabular-nums truncate ${raw ? "font-sans text-ink2" : `font-mono ${tone ?? "text-ink"}`}`}
      >
        {value}
      </dd>
    </div>
  );
}
