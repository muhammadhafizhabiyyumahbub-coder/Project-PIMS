"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/Badge";
import { formatMoneyString, formatSignedMoneyString, formatUtc, pnlTone } from "@/lib/format";
import { ApiRequestError, createSnapshot, createTransaction, getHoldings, getPortfolio, getValuation, listSnapshots, listTransactions } from "@/services/api";
import type { AssetSummary, Holding, Portfolio, PortfolioSnapshot, Transaction, Valuation } from "@/types/api";
import AssetPicker from "./AssetPicker";
import PerformancePanel from "./PerformancePanel";
import AllocationPanel from "./AllocationPanel";

const TRANSACTION_TYPES = ["DEPOSIT", "WITHDRAWAL", "BUY", "SELL"] as const;
const ASSET_TYPES: readonly string[] = ["BUY", "SELL"];

/** portfolio-engine-spec §8 status model, shown verbatim in the UI. */
const STATUS_REASONS: Record<string, string> = {
  COMPLETE: "All held positions priced from fresh stored candles.",
  PARTIAL: "Some positions have no stored price yet. Totals are withheld rather than estimated.",
  STALE: "Price data is older than the freshness policy. Values are shown as unavailable rather than computed from old prices.",
  UNAVAILABLE: "No transaction data for this portfolio yet.",
};

export default function PortfolioDetail({ portfolioId }: { portfolioId: string }) {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [valuation, setValuation] = useState<Valuation | null>(null);
  const [holdings, setHoldings] = useState<Holding[] | null>(null);
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const loading = loadError === null && (portfolio === null || valuation === null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getPortfolio(portfolioId), getValuation(portfolioId), getHoldings(portfolioId), listTransactions(portfolioId)])
      .then(([p, v, h, t]) => {
        if (cancelled) return;
        setPortfolio(p.data);
        setValuation(v.data);
        setHoldings(h.data);
        setTransactions(t.data);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setPortfolio(null);
        setValuation(null);
        setHoldings(null);
        setTransactions(null);
        setLoadError(
          error instanceof ApiRequestError ? error.message : "Unexpected error loading portfolio.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [portfolioId, reloadKey]);

  if (loading) {
    return (
      <div className="bg-card border border-line rounded-lg px-4 py-10 text-center text-[12px] text-ink3" aria-live="polite">
        Loading portfolio…
      </div>
    );
  }

  if (loadError !== null) {
    return (
      <div role="alert" className="bg-card border border-loss-line bg-loss-bg rounded-lg px-4 py-6 text-[12px] text-loss">
        {loadError}
        <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="ml-2 underline underline-offset-2">
          Retry
        </button>
      </div>
    );
  }

  if (portfolio === null || valuation === null || holdings === null || transactions === null) {
    return null;
  }

  return (
    <div className="flex flex-col gap-5">
      <nav aria-label="Breadcrumb" className="text-[11px] text-ink3">
        <Link href="/portfolios" className="underline underline-offset-2 hover:text-ink2">
          Portfolios
        </Link>
        <span className="mx-1.5">/</span>
        <span className="text-ink2">{portfolio.name}</span>
      </nav>

      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-[18px] font-bold tracking-tight">{portfolio.name}</h1>
          {portfolio.description && <p className="text-[12px] text-ink3">{portfolio.description}</p>}
          <p className="text-[10px] text-ink3 font-mono">{portfolio.id}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-ink2 font-mono">{portfolio.base_currency}</span>
          <Badge label={portfolio.status} />
        </div>
      </header>

      <ValuationSummary valuation={valuation} />
      <AllocationPanel portfolioId={portfolioId} />
      <PerformancePanel portfolioId={portfolioId} />
      <SnapshotHistory portfolioId={portfolioId} />
      <HoldingsTable holdings={holdings} statusReason={STATUS_REASONS[valuation.valuation_status]} />
      <TransactionForm portfolioId={portfolioId} currency={portfolio.base_currency} onRecorded={() => setReloadKey((k) => k + 1)} />
      <TransactionsTable transactions={transactions} />
    </div>
  );
}

function ValuationSummary({ valuation }: { valuation: Valuation }) {
  const reason = STATUS_REASONS[valuation.valuation_status] ?? valuation.valuation_status;
  return (
    <section aria-label="Valuation summary" className="bg-card border border-line rounded-lg">
      <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-line">
        <div>
          <h2 className="text-[15px] font-semibold">Valuation</h2>
          <p className="text-[11px] text-ink3">Valued {formatUtc(valuation.valued_at)}</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge label={valuation.valuation_status} />
        </div>
      </header>
      <p className="px-4 py-2 text-[11px] text-ink2 border-b border-line">{reason}</p>
      <dl className="grid grid-cols-2 md:grid-cols-5 gap-3 px-4 py-3">
        <Metric label="Cash" value={<Money value={valuation.cash_value} />} />
        <Metric label="Invested" value={<Money value={valuation.invested_value} />} />
        <Metric label="Total value" value={<Money value={valuation.total_value} />} />
        <Metric label="Realized P&L" value={<Pnl value={valuation.realized_pnl} />} />
        <Metric label="Unrealized P&L" value={<Pnl value={valuation.unrealized_pnl} />} />
      </dl>
      <p className="px-4 pb-3 text-[10px] text-ink3">
        Currency {valuation.reporting_currency}. Withheld values come from the backend when price data is missing or stale — the UI never estimates them.
      </p>
    </section>
  );
}

function HoldingsTable({ holdings, statusReason }: { holdings: Holding[]; statusReason: string }) {
  return (
    <section aria-label="Holdings" className="bg-card border border-line rounded-lg">
      <header className="px-4 py-3 border-b border-line">
        <h2 className="text-[15px] font-semibold">Holdings</h2>
      </header>
      {holdings.length === 0 ? (
        <p className="px-4 py-8 text-center text-[12px] text-ink2">
          No open positions. BUY transactions create holdings; fully sold positions are removed.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-left text-[10px] text-ink3 border-b border-line">
                <th className="px-4 py-2 font-medium">Symbol</th>
                <th className="px-4 py-2 font-medium text-right">Quantity</th>
                <th className="px-4 py-2 font-medium text-right">Average cost</th>
                <th className="px-4 py-2 font-medium text-right">Cost basis</th>
                <th className="px-4 py-2 font-medium text-right">Market price</th>
                <th className="px-4 py-2 font-medium text-right">Market value</th>
                <th className="px-4 py-2 font-medium text-right">Unrealized P&L</th>
                <th className="px-4 py-2 font-medium">Price</th>
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => (
                <tr key={holding.asset_id} className="border-b border-line last:border-b-0">
                  <td className="px-4 py-2 font-mono font-semibold">{holding.symbol}</td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{formatMoneyString(holding.quantity)}</td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{formatMoneyString(holding.average_cost)}</td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{formatMoneyString(holding.cost_basis)}</td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">
                    {holding.market_price === null ? <UnavailableCell /> : formatMoneyString(holding.market_price)}
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">
                    {holding.market_value === null ? <UnavailableCell /> : formatMoneyString(holding.market_value)}
                  </td>
                  <td className={`px-4 py-2 text-right font-mono tabular-nums ${pnlTone(holding.unrealized_pnl)}`}>
                    {holding.unrealized_pnl === null ? <UnavailableCell /> : formatSignedMoneyString(holding.unrealized_pnl)}
                  </td>
                  <td className="px-4 py-2">
                    <Badge label={holding.price_status} mono />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {holdings.length > 0 && (
        <p className="px-4 py-2 text-[10px] text-ink3">{statusReason}</p>
      )}
    </section>
  );
}

function SnapshotHistory({ portfolioId }: { portfolioId: string }) {
  const [snapshots, setSnapshots] = useState<PortfolioSnapshot[] | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [taking, setTaking] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [captureError, setCaptureError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  // Key for the capture attempt in progress. Two triggers that race (before the
  // first resolves) send the same key, so the backend replays instead of writing
  // two rows. Rotated after success, so a later capture is a new snapshot
  // (technical-decisions §7.9). No unique index backs this: it is best-effort.
  const pendingKey = useRef<string | null>(null);

  // Same shape as the parent loader: fetch in the effect, state set in the
  // callback, reloadKey re-runs it after a new snapshot is captured.
  useEffect(() => {
    let cancelled = false;
    listSnapshots(portfolioId)
      .then((response) => {
        if (cancelled) return;
        setSnapshots(response.data);
        setHasMore(Boolean((response.meta?.pagination as { has_more?: boolean } | undefined)?.has_more));
        setListError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setSnapshots([]);
        setHasMore(false);
        setListError(error instanceof ApiRequestError ? error.message : "Could not load snapshots.");
      });
    return () => {
      cancelled = true;
    };
  }, [portfolioId, reloadKey]);

  const loadMore = useCallback(async () => {
    if (snapshots === null || snapshots.length === 0) return;
    setLoadingMore(true);
    try {
      const response = await listSnapshots(portfolioId, snapshots[snapshots.length - 1].id);
      setSnapshots([...snapshots, ...response.data]);
      setHasMore(Boolean((response.meta?.pagination as { has_more?: boolean } | undefined)?.has_more));
      setListError(null);
    } catch (error) {
      setListError(error instanceof ApiRequestError ? error.message : "Could not load more snapshots.");
    } finally {
      setLoadingMore(false);
    }
  }, [portfolioId, snapshots]);

  const takeSnapshot = useCallback(async () => {
    setTaking(true);
    setNotice(null);
    setCaptureError(null);
    try {
      // Reuse the in-progress key so a double trigger replays instead of writing
      // two rows; rotate after success so a later capture is genuinely new.
      const key = pendingKey.current ?? crypto.randomUUID();
      pendingKey.current = key;
      const response = await createSnapshot(portfolioId, key);
      pendingKey.current = null;
      const snapshot = response.data;
      setNotice(
        snapshot.idempotent_replay
          ? `Snapshot ${formatUtc(snapshot.snapshot_at)} already exists, nothing was duplicated.`
          : `Snapshot ${formatUtc(snapshot.snapshot_at)} captured (${snapshot.valuation_status}).`,
      );
      setReloadKey((k) => k + 1);
    } catch (error) {
      pendingKey.current = null;
      setCaptureError(
        error instanceof ApiRequestError ? error.message : "Could not take a snapshot.",
      );
    } finally {
      setTaking(false);
    }
  }, [portfolioId]);

  return (
    <section aria-label="Snapshot history" className="bg-card border border-line rounded-lg">
      <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-line">
        <div>
          <h2 className="text-[15px] font-semibold">Riwayat Snapshot</h2>
          <p className="text-[11px] text-ink3">
            Snapshots are written only when you ask for one. No scheduled snapshots yet.
          </p>
        </div>
        <button
          type="button"
          onClick={takeSnapshot}
          disabled={taking}
          className="bg-accent-bg text-accent border border-accent-line rounded px-3 py-1.5 text-[12px] font-medium hover:bg-hover disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
        >
          {taking ? "Mengambil..." : "Ambil snapshot"}
        </button>
      </header>
      {notice && (
        <p role="status" className="px-4 py-2 text-[11px] text-gain border-b border-line">
          {notice}
        </p>
      )}
      {captureError && (
        <p role="alert" className="px-4 py-2 text-[11px] text-loss border-b border-line">
          {captureError}
        </p>
      )}
      {listError && (
        <div role="alert" className="px-4 py-3 text-[12px] text-loss">
          {listError.split(".")[0] === "Cannot reach the PIMS backend." ? (
            "Backend is not reachable. Open portfolios once the backend is running on port 8000."
          ) : (
            listError
          )}
          <button type="button" onClick={() => setReloadKey((k) => k + 1)} className="ml-2 underline underline-offset-2">
            Retry
          </button>
        </div>
      )}
      {snapshots === null ? (
        <p aria-live="polite" className="px-4 py-8 text-center text-[12px] text-ink3">
          Loading snapshots...
        </p>
      ) : snapshots.length === 0 ? (
        <p className="px-4 py-8 text-center text-[12px] text-ink2">
          No snapshots yet. &quot;Ambil snapshot&quot; stores the current valuation.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-left text-[10px] text-ink3 border-b border-line">
                <th className="px-4 py-2 font-medium">Waktu</th>
                <th className="px-4 py-2 font-medium">Status</th>
                <th className="px-4 py-2 font-medium text-right">Cash</th>
                <th className="px-4 py-2 font-medium text-right">Invested</th>
                <th className="px-4 py-2 font-medium text-right">Total</th>
                <th className="px-4 py-2 font-medium text-right">Realized</th>
                <th className="px-4 py-2 font-medium text-right">Unrealized</th>
              </tr>
            </thead>
            <tbody>
              {snapshots.map((snapshot) => (
                <tr key={snapshot.id} className="border-b border-line last:border-b-0">
                  <td className="px-4 py-2 text-[11px] text-ink2 whitespace-nowrap">
                    {formatUtc(snapshot.snapshot_at)}
                  </td>
                  <td className="px-4 py-2">
                    <Badge label={snapshot.valuation_status} />
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">
                    <Money value={snapshot.cash_value} />
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">
                    <Money value={snapshot.invested_value} />
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">
                    <Money value={snapshot.total_value} />
                  </td>
                  <td className={`px-4 py-2 text-right font-mono tabular-nums ${pnlTone(snapshot.realized_pnl)}`}>
                    <Pnl value={snapshot.realized_pnl} />
                  </td>
                  <td className={`px-4 py-2 text-right font-mono tabular-nums ${pnlTone(snapshot.unrealized_pnl)}`}>
                    <Pnl value={snapshot.unrealized_pnl} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {snapshots !== null && snapshots.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2 border-t border-line">
          <p className="text-[10px] text-ink3">
            Currency {snapshots[0].reporting_currency}. Values the valuation could not produce are shown as unavailable, never as zero.
          </p>
          {hasMore && (
            <button
              type="button"
              onClick={() => void loadMore()}
              disabled={loadingMore}
              className="border border-line rounded px-3 py-1 text-[11px] text-ink2 hover:bg-hover disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
            >
              {loadingMore ? "Memuat..." : "Muat lagi"}
            </button>
          )}
        </div>
      )}
    </section>
  );
}

function TransactionsTable({ transactions }: { transactions: Transaction[] }) {
  return (
    <section aria-label="Transactions" className="bg-card border border-line rounded-lg">
      <header className="px-4 py-3 border-b border-line">
        <h2 className="text-[15px] font-semibold">Transactions</h2>
        <p className="text-[11px] text-ink3">Recorded history; holdings and cash replay from these rows.</p>
      </header>
      {transactions.length === 0 ? (
        <p className="px-4 py-8 text-center text-[12px] text-ink2">No transactions recorded yet.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-left text-[10px] text-ink3 border-b border-line">
                <th className="px-4 py-2 font-medium">Type</th>
                <th className="px-4 py-2 font-medium text-right">Detail</th>
                <th className="px-4 py-2 font-medium text-right">Fee</th>
                <th className="px-4 py-2 font-medium">Executed</th>
                <th className="px-4 py-2 font-medium">Idempotency key</th>
              </tr>
            </thead>
            <tbody>
              {transactions.map((tx) => (
                <tr key={tx.id} className="border-b border-line last:border-b-0">
                  <td className="px-4 py-2">
                    <Badge label={tx.transaction_type} mono />
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">
                    {tx.transaction_type === "BUY" || tx.transaction_type === "SELL"
                      ? `${formatMoneyString(tx.quantity)} @ ${formatMoneyString(tx.price)} = ${formatMoneyString(tx.gross_amount)}`
                      : formatMoneyString(tx.gross_amount)}
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{formatMoneyString(tx.fee)}</td>
                  <td className="px-4 py-2 text-[11px] text-ink2">{formatUtc(tx.executed_at)}</td>
                  <td className="px-4 py-2 font-mono text-[10px] text-ink3">{tx.idempotency_key ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function TransactionForm({
  portfolioId,
  currency,
  onRecorded,
}: {
  portfolioId: string;
  currency: string;
  onRecorded: () => void;
}) {
  const [type, setType] = useState<string>("DEPOSIT");
  const [asset, setAsset] = useState<AssetSummary | null>(null);
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [grossAmount, setGrossAmount] = useState("");
  const [fee, setFee] = useState("0");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isAssetType = ASSET_TYPES.includes(type);
  const hasAsset = asset !== null;

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (isAssetType && !hasAsset) {
        setError("Pilih aset terlebih dahulu.");
        return;
      }
      setSubmitting(true);
      setError(null);
      setMessage(null);
      try {
        await createTransaction({
          portfolio_id: portfolioId,
          transaction_type: type,
          ...(isAssetType
            ? { asset_id: asset!.id, quantity, price }
            : { gross_amount: grossAmount }),
          ...(fee !== "" ? { fee } : {}),
        });
        setMessage(`${type} recorded.`);
        setAsset(null);
        setQuantity("");
        setPrice("");
        setGrossAmount("");
        setFee("0");
        onRecorded();
      } catch (err) {
        setError(
          err instanceof ApiRequestError ? err.message : "Transaction failed unexpectedly.",
        );
      } finally {
        setSubmitting(false);
      }
    },
    [portfolioId, type, isAssetType, hasAsset, asset, quantity, price, grossAmount, fee, onRecorded],
  );

  return (
    <form
      onSubmit={submit}
      aria-label="Record transaction"
      className="bg-card border border-line rounded-lg px-4 py-3 flex flex-col gap-3"
    >
      <h3 className="text-[13px] font-semibold">Record Transaction</h3>
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-[11px] text-ink2">
          Type
          <select
            value={type}
            onChange={(event) => setType(event.target.value)}
            className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink focus-visible:outline focus-visible:outline-accent"
          >
            {TRANSACTION_TYPES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>
        {isAssetType && (
          <AssetPicker
            value={asset}
            onChange={setAsset}
            disabled={submitting}
          />
        )}
        {isAssetType && (
          <>
            <label className="flex flex-col gap-1 text-[11px] text-ink2">
              Quantity
              <input
                required
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
                inputMode="decimal"
                className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink w-[120px] font-mono focus-visible:outline focus-visible:outline-accent"
              />
            </label>
            <label className="flex flex-col gap-1 text-[11px] text-ink2">
              Price
              <input
                required
                value={price}
                onChange={(event) => setPrice(event.target.value)}
                inputMode="decimal"
                className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink w-[120px] font-mono focus-visible:outline focus-visible:outline-accent"
              />
            </label>
          </>
        )}
        {!isAssetType && (
          <label className="flex flex-col gap-1 text-[11px] text-ink2">
            Amount
            <input
              required
              value={grossAmount}
              onChange={(event) => setGrossAmount(event.target.value)}
              inputMode="decimal"
              className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink w-[140px] font-mono focus-visible:outline focus-visible:outline-accent"
            />
          </label>
        )}
        <label className="flex flex-col gap-1 text-[11px] text-ink2">
          Fee
          <input
            value={fee}
            onChange={(event) => setFee(event.target.value)}
            inputMode="decimal"
            className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink w-[100px] font-mono focus-visible:outline focus-visible:outline-accent"
          />
        </label>
        <button
          type="submit"
          disabled={submitting || (isAssetType && !hasAsset)}
          className="bg-accent-bg text-accent border border-accent-line rounded px-3 py-1.5 text-[12px] font-medium hover:bg-hover disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
        >
          {submitting ? "Recording…" : "Record"}
        </button>
      </div>
      {message && (
        <p role="status" className="text-[12px] text-gain">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="text-[12px] text-loss">
          {error}
        </p>
      )}
      <p className="text-[10px] text-ink3">
        Currency {currency}. BUY/SELL fees: added to cost on BUY, subtracted from proceeds on SELL.
      </p>
    </form>
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

function Money({ value }: { value: string | null }) {
  if (value === null) return <UnavailableValue />;
  return <span className="text-ink">{formatMoneyString(value)}</span>;
}

function Pnl({ value }: { value: string | null }) {
  if (value === null) return <UnavailableValue />;
  return <span className={pnlTone(value)}>{formatSignedMoneyString(value)}</span>;
}

function UnavailableCell() {
  return <span className="text-ink3" title="Not available from backend">not available</span>;
}

function UnavailableValue() {
  return <span className="text-ink3 text-[12px] font-sans font-normal">not available</span>;
}