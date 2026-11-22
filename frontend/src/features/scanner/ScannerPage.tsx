"use client";

import Link from "next/link";
import { Fragment, useCallback, useEffect, useState } from "react";

import { Badge, DeltaText } from "@/components/Badge";
import { formatPrice, formatScore, formatUtc } from "@/lib/format";
import { ApiRequestError, getOpportunities, getQualification, runScanner } from "@/services/api";
import type { Opportunity, ScannerQualification, ScannerRunSummary } from "@/types/api";

type MarketFilter = "ALL" | "CRYPTO" | "US" | "IDX";
type QualificationFilter = "ALL" | "QUALIFIED" | "PARTIAL" | "NOT_QUALIFIED" | "STALE";
type SortField = "scanner_score" | "daily_change" | "symbol" | "updated_at";

const MARKETS: { id: MarketFilter; label: string }[] = [
  { id: "ALL", label: "Semua market" },
  { id: "CRYPTO", label: "Crypto" },
  { id: "US", label: "US Stocks" },
  { id: "IDX", label: "IDX" },
];

const QUALIFICATIONS: { id: QualificationFilter; label: string }[] = [
  { id: "ALL", label: "Semua status" },
  { id: "QUALIFIED", label: "Qualified" },
  { id: "PARTIAL", label: "Partial" },
  { id: "NOT_QUALIFIED", label: "Not qualified" },
  { id: "STALE", label: "Stale" },
];

const SORTS: { id: SortField; label: string }[] = [
  { id: "scanner_score", label: "Skor scanner" },
  { id: "daily_change", label: "Perubahan harian" },
  { id: "updated_at", label: "Update terakhir" },
  { id: "symbol", label: "Simbol" },
];

/** Timeframes accepted by POST /scanner/run (spec §8.2 candle-based scanning). */
const TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"] as const;

/** Spec §5 scanner categories. Backend runs one deterministic technical scan over
 * the CRYPTO universe, so these are shown as scope, not as working filters. */
const CATEGORIES = [
  "Technical",
  "Momentum",
  "Volume",
  "Volatility",
  "Fundamental",
  "Market Trend",
  "Anomaly",
  "Correlation",
] as const;

const CONTROL =
  "bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink focus-visible:outline focus-visible:outline-accent";

/**
 * Market Scanner page (Stage N). Every number here comes from the scanner
 * endpoints: POST /scanner/run, GET /dashboard/instrument-opportunities and
 * GET /scanner/results/{id}/qualification. The client never scores, ranks or
 * recomputes freshness.
 */
export default function ScannerPage() {
  const [rows, setRows] = useState<Opportunity[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const [market, setMarket] = useState<MarketFilter>("ALL");
  const [qualification, setQualification] = useState<QualificationFilter>("ALL");
  const [sort, setSort] = useState<SortField>("scanner_score");
  const [timeframe, setTimeframe] = useState<string>("1h");

  const [scanning, setScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [lastRun, setLastRun] = useState<ScannerRunSummary | null>(null);

  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getOpportunities({ market, qualification, sort })
      .then((envelope) => {
        if (cancelled) return;
        setRows(envelope.data);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setRows(null);
        setLoadError(
          error instanceof ApiRequestError ? error.message : "Could not load scanner results.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [market, qualification, sort, reloadKey]);

  const runScan = useCallback(async () => {
    setScanning(true);
    setScanError(null);
    setOpenId(null);
    try {
      const envelope = await runScanner(timeframe);
      setLastRun(envelope.data);
      setReloadKey((k) => k + 1);
    } catch (error) {
      setScanError(
        error instanceof ApiRequestError ? error.message : "Scan failed unexpectedly.",
      );
    } finally {
      setScanning(false);
    }
  }, [timeframe]);

  const retry = useCallback(() => setReloadKey((k) => k + 1), []);

  return (
    <main className="mx-auto max-w-[1700px] px-4 py-6 sm:px-6 flex flex-col gap-5">
      <nav aria-label="Breadcrumb" className="text-[11px] text-ink3">
        <Link href="/" className="underline underline-offset-2 hover:text-ink2">
          Dashboard
        </Link>
        <span className="mx-1.5">/</span>
        <span className="text-ink2">Scanner</span>
      </nav>

      <header>
        <h1 className="text-[20px] font-bold tracking-tight">Market Scanner</h1>
        <p className="text-[12px] text-ink3">
          Menyaring market universe dengan aturan deterministik dan skor peringkat. Hasil
          screening bukan jaminan arah harga.
        </p>
      </header>

      <section aria-label="Scope scanner" className="bg-card border border-line rounded-lg">
        <header className="px-4 py-3 border-b border-line">
          <h2 className="text-[13px] font-semibold">Kategori</h2>
          <p className="text-[11px] text-ink3">
            Scan berjalan atas seluruh universe CRYPTO yang tersimpan. Kategori lain ada di
            roadmap engine (spec §5, Phase 6) dan belum punya parameter API, jadi tidak
            ditampilkan sebagai filter yang bisa diklik.
          </p>
        </header>
        <ul className="flex flex-wrap gap-1.5 px-4 py-3">
          {CATEGORIES.map((category) => {
            const active = category === "Technical";
            return (
              <li key={category}>
                <span
                  className={`inline-flex items-center px-2 py-1 rounded border text-[11px] ${
                    active
                      ? "bg-accent-bg text-accent border-accent-line font-medium"
                      : "bg-recessed text-ink3 border-line"
                  }`}
                  title={
                    active
                      ? "Kategori yang dijalankan backend saat ini"
                      : "Belum didukung backend; tidak tersedia sebagai filter"
                  }
                >
                  {category}
                </span>
              </li>
            );
          })}
        </ul>
      </section>

      <section aria-label="Konfigurasi scan" className="bg-card border border-line rounded-lg">
        <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-line">
          <div>
            <h2 className="text-[15px] font-semibold">Konfigurasi scan</h2>
            <p className="text-[11px] text-ink3">
              Universe CRYPTO, minimal 60 candle dan quote volume 24 jam ≥ 1.000.000.
            </p>
          </div>
          <button
            type="button"
            onClick={() => void runScan()}
            disabled={scanning}
            className="bg-accent-bg text-accent border border-accent-line rounded px-3 py-1.5 text-[12px] font-medium hover:bg-hover disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
          >
            {scanning ? "Memindai…" : "Jalankan scan"}
          </button>
        </header>

        <div className="flex flex-wrap items-end gap-3 px-4 py-3 border-b border-line">
          <label className="flex flex-col gap-1 text-[11px] text-ink2">
            Timeframe
            <select
              value={timeframe}
              onChange={(event) => setTimeframe(event.target.value)}
              className={CONTROL}
            >
              {TIMEFRAMES.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-[11px] text-ink2">
            Market
            <select
              value={market}
              onChange={(event) => setMarket(event.target.value as MarketFilter)}
              className={CONTROL}
            >
              {MARKETS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-[11px] text-ink2">
            Qualification
            <select
              value={qualification}
              onChange={(event) => setQualification(event.target.value as QualificationFilter)}
              className={CONTROL}
            >
              {QUALIFICATIONS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-[11px] text-ink2">
            Urutkan
            <select
              value={sort}
              onChange={(event) => setSort(event.target.value as SortField)}
              className={CONTROL}
            >
              {SORTS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <p className="text-[10px] text-ink3 max-w-[420px]">
            Market, qualification dan urutan diteruskan apa adanya ke API hasil scan; UI tidak
            memfilter atau mengurutkan ulang di klien.
          </p>
        </div>

        {scanning && (
          <p aria-live="polite" className="px-4 py-2 text-[11px] text-ink2 border-b border-line">
            Scan sedang berjalan atas universe tersimpan. Candle belum diperbarui selama proses
            ini.
          </p>
        )}
        {scanError && (
          <div role="alert" className="px-4 py-3 text-[12px] text-loss">
            {scanError}
          </div>
        )}
        {lastRun && !scanning && (
          <div className="px-4 py-2 text-[11px] text-ink2 border-b border-line flex flex-wrap gap-x-4 gap-y-1">
            <span>Status {lastRun.execution_status}</span>
            <span>
              Universe {lastRun.universe_size ?? "—"} · eligible {lastRun.eligible_count ?? "—"} ·
              hasil {lastRun.result_count ?? "—"}
            </span>
            <span>Selesai {formatUtc(lastRun.completed_at)}</span>
          </div>
        )}

        {loadError !== null ? (
          <div role="alert" className="px-4 py-3 text-[12px] text-loss">
            {loadError.split(".")[0] === "Cannot reach the PIMS backend."
              ? "Backend is not reachable. Start the API on port 8000, then retry."
              : loadError}
            <button type="button" onClick={retry} className="ml-2 underline underline-offset-2">
              Retry
            </button>
          </div>
        ) : rows === null ? (
          <p aria-live="polite" className="px-4 py-8 text-center text-[12px] text-ink3">
            Loading scanner results…
          </p>
        ) : rows.length === 0 ? (
          <EmptyState filtered={market !== "ALL" || qualification !== "ALL"} onRun={() => void runScan()} scanning={scanning} />
        ) : (
          <>
            <ResultsTable rows={rows} openId={openId} onToggle={(id) => setOpenId(openId === id ? null : id)} />
            <p className="px-4 py-2 text-[10px] text-ink3 border-t border-line">
              {rows.length} hasil ditampilkan. Angka berasal dari backend; skor dan rank tidak
              dihitung ulang di UI.
            </p>
          </>
        )}
      </section>
    </main>
  );
}

function EmptyState({
  filtered,
  onRun,
  scanning,
}: {
  filtered: boolean;
  onRun: () => void;
  scanning: boolean;
}) {
  return (
    <div className="px-4 py-10 text-center flex flex-col items-center gap-3">
      <p className="text-[13px] text-ink2">
        {filtered
          ? "Tidak ada hasil scan yang cocok dengan filter ini."
          : "Belum ada hasil scan tersimpan untuk universe ini."}
      </p>
      <p className="text-[11px] text-ink3 max-w-[520px]">
        {filtered
          ? "Kosongkan market atau qualification untuk melihat seluruh hasil."
          : "Jalankan scan untuk mengevaluasi instrumen yang punya minimal 60 candle tersimpan pada timeframe terpilih."}
      </p>
      {!filtered && (
        <button
          type="button"
          onClick={onRun}
          disabled={scanning}
          className="bg-accent-bg text-accent border border-accent-line rounded px-3 py-1.5 text-[12px] font-medium hover:bg-hover disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
        >
          {scanning ? "Memindai…" : "Jalankan scan"}
        </button>
      )}
    </div>
  );
}

function ResultsTable({
  rows,
  openId,
  onToggle,
}: {
  rows: Opportunity[];
  openId: string | null;
  onToggle: (id: string) => void;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-left text-[10px] text-ink3 border-b border-line">
            <th className="px-4 py-2 font-medium">Simbol</th>
            <th className="px-4 py-2 font-medium">Market</th>
            <th className="px-4 py-2 font-medium text-right">Skor</th>
            <th className="px-4 py-2 font-medium text-right">Rank</th>
            <th className="px-4 py-2 font-medium text-right">Harga</th>
            <th className="px-4 py-2 font-medium text-right">Δ harian</th>
            <th className="px-4 py-2 font-medium">Qualification</th>
            <th className="px-4 py-2 font-medium">Data</th>
            <th className="px-4 py-2 font-medium">Update</th>
            <th className="px-4 py-2 font-medium text-right">Detail</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const id = row.scanner_result_id;
            const open = openId === id;
            return (
              <Fragment key={id}>
                <tr className="border-b border-line">
                  <td className="px-4 py-2 font-mono font-semibold">{row.instrument.symbol}</td>
                  <td className="px-4 py-2 font-mono">{row.market ?? "—"}</td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">
                    {formatScore(row.scanner_score)}
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">
                    {row.scanner_rank === null ? "—" : `#${row.scanner_rank}`}
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">
                    {row.current_price === null ? "—" : (
                      <>
                        <span className="text-ink">{formatPrice(row.current_price)}</span>
                        <span className="text-[10px] text-ink3 ml-1">{row.data_currency ?? "—"}</span>
                        {row.data_currency && row.quote_currency && row.data_currency !== row.quote_currency && (
                           <span className="block text-[9px] text-loss">Aset: {row.quote_currency}</span>
                        )}
                      </>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <DeltaText value={row.daily_change_pct} />
                  </td>
                  <td className="px-4 py-2">
                    <Badge label={row.approval_status} mono />
                  </td>
                  <td className="px-4 py-2">
                    <Badge label={row.data_status} mono />
                  </td>
                  <td className="px-4 py-2 text-[11px] text-ink3 whitespace-nowrap">
                    {formatUtc(row.updated_at)}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      type="button"
                      onClick={() => onToggle(id)}
                      aria-expanded={open}
                      className="border border-line rounded px-2 py-1 text-[11px] text-ink2 hover:bg-hover focus-visible:outline focus-visible:outline-accent"
                    >
                      {open ? "Tutup" : "Qualification"}
                    </button>
                  </td>
                </tr>
                {open && (
                  <tr className="border-b border-line bg-recessed">
                    <td colSpan={10} className="px-4 py-3">
                      <QualificationDetail resultId={id} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Server-side qualification for one stored result row. Values are rendered as sent. */
function QualificationDetail({ resultId }: { resultId: string }) {
  const [detail, setDetail] = useState<ScannerQualification | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getQualification(resultId)
      .then((envelope) => {
        if (cancelled) return;
        setDetail(envelope.data);
        setError(null);
      })
      .catch((reason: unknown) => {
        if (cancelled) return;
        setDetail(null);
        setError(
          reason instanceof ApiRequestError ? reason.message : "Could not load qualification.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [resultId]);

  if (error !== null) {
    return (
      <p role="alert" className="text-[12px] text-loss">
        {error}
      </p>
    );
  }
  if (detail === null) {
    return (
      <p aria-live="polite" className="text-[12px] text-ink3">
        Loading qualification…
      </p>
    );
  }

  const engines = Object.entries(detail.engine_readiness);
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-ink2">
        <span className="font-mono font-semibold text-ink">{detail.instrument}</span>
        <Badge label={detail.approval_status} mono />
        <span>Data {detail.data_status}</span>
        <span>Update {formatUtc(detail.updated_at)}</span>
      </div>
      <div>
        <p className="text-[10px] text-ink3 mb-1.5">Lolos engine</p>
        {detail.passed_by.length === 0 ? (
          <p className="text-[11px] text-ink3">Belum ada engine yang lolos.</p>
        ) : (
          <div className="flex flex-wrap gap-1">
            {detail.passed_by.map((engine) => (
              <Badge key={engine} label={engine} mono />
            ))}
          </div>
        )}
      </div>
      {engines.length > 0 ? (
        <dl className="flex flex-col gap-1 text-[11px]">
          {engines.map(([engine, readiness]) => (
            <div key={engine} className="flex flex-wrap items-baseline gap-2">
              <dt className="font-mono text-ink2 w-[130px]">{engine}</dt>
              <dd className="font-mono text-ink">{readiness.state}</dd>
              <dd className="text-ink3">{readiness.label}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="text-[11px] text-ink3">
          Tidak ada engine readiness tersimpan untuk {detail.instrument}.
        </p>
      )}
    </div>
  );
}