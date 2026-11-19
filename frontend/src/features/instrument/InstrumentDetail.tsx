"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge, DeltaText } from "@/components/Badge";
import CandleChart, { toBars, type ValidatedBar } from "@/features/charts/CandleChart";
import ResearchPanel from "@/features/research/ResearchPanel";
import { useMarketFeed } from "@/hooks/useMarketFeed";
import { formatPrice, formatUtc } from "@/lib/format";
import { ApiRequestError, getCandles, getOpportunities, refreshMarketData } from "@/services/api";
import type { CandlesResponse, Opportunity } from "@/types/api";


const TIMEFRAMES = ["1h", "4h", "1d"] as const;
type Timeframe = (typeof TIMEFRAMES)[number];

export default function InstrumentDetail({ symbol, timeframe: initialTimeframe }: { symbol: string; timeframe?: string }) {
  const [timeframe, setTimeframe] = useState<Timeframe>(
    (TIMEFRAMES as readonly string[]).includes(initialTimeframe ?? "") ? (initialTimeframe as Timeframe) : "1h",
  );
  const feed = useMarketFeed(symbol, timeframe);

  return (
    <main className="mx-auto max-w-[1700px] px-4 py-6 sm:px-6 flex flex-col gap-5">
      <Link href="/" className="text-[12px] text-ink2 hover:text-ink focus-visible:outline focus-visible:outline-accent self-start">
        ← Back to dashboard
      </Link>
      <InstrumentHeader symbol={symbol} timeframe={timeframe} feed={feed} />
      <CandleSection symbol={symbol} timeframe={timeframe} onTimeframeChange={setTimeframe} feed={feed} />
      <ResearchPanel symbol={symbol} timeframe={timeframe} />
    </main>
  );
}

function InstrumentHeader({
  symbol,
  timeframe,
  feed,
}: {
  symbol: string;
  timeframe: string;
  feed: ReturnType<typeof useMarketFeed>;
}) {
  const [opportunity, setOpportunity] = useState<Opportunity | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getOpportunities({ sort: "scanner_score" })
      .then((envelope) => {
        if (!cancelled) {
          setOpportunity(envelope.data.find((row) => row.instrument.symbol === symbol) ?? null);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof ApiRequestError ? err.message : "Failed to load instrument summary.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [symbol]);

  return (
    <header className="bg-card border border-line rounded-lg px-4 py-3.5">
      {error && (
        <div role="alert" className="text-[12px] text-loss mb-2">
          {error}
        </div>
      )}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-mono text-[20px] font-bold">{symbol}</h1>
            {opportunity && <Badge label={opportunity.approval_status} />}
            {opportunity && <Badge label={opportunity.data_status} />}
          </div>
          <p className="text-[12px] text-ink3">
            {opportunity ? `${opportunity.instrument.name} · ${opportunity.market ?? "UNKNOWN"} · ${timeframe}` : `Instrument summary unavailable (no scanner result for ${symbol}).`}
          </p>
        </div>
        <div className="flex items-baseline gap-3">
          <span className="font-mono text-[24px] font-semibold tabular-nums">{formatPrice(opportunity?.current_price ?? null)}</span>
          <span className="text-[13px]">
            <DeltaText value={opportunity?.daily_change_pct ?? null} />
          </span>
        </div>
      </div>
      <MarketFeedRow feed={feed} />
    </header>
  );
}

/**
 * Feed state comes straight from the backend message (feed_status) or from the
 * client connection state. Nothing here is inferred or promoted to LIVE: the
 * server has no stream, so the best honest value is DELAYED.
 */
function MarketFeedRow({ feed }: { feed: ReturnType<typeof useMarketFeed> }) {
  const connection = feed.connection;
  const label = connection === "READY" ? (feed.quote?.feed_status ?? "UNAVAILABLE") : connection;
  const source = feed.quote?.source ?? "rest_poll";
  const interval = feed.quote?.poll_interval_seconds;
  const lastData = feed.quote?.data_timestamp ?? null;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-line pt-2.5 text-[11px] text-ink2">
      <span className="flex items-center gap-2">
        <span className="text-ink3">Feed</span>
        <Badge label={label} mono />
      </span>
      <span>
        Data terakhir <span className="font-mono">{formatUtc(lastData)}</span>
      </span>
      <span className="text-ink3">
        Sumber {source}
        {interval ? ` · polling DB tiap ${interval}s` : ""} · bukan stream realtime
      </span>
      {(connection === "DISCONNECTED" || connection === "ERROR") && (
        <button
          type="button"
          onClick={feed.reconnect}
          className="rounded border border-line px-2 py-0.5 text-[11px] text-ink2 hover:bg-hover focus-visible:outline focus-visible:outline-accent"
        >
          Reconnect feed
        </button>
      )}
    </div>
  );
}

function CandleSection({
  symbol,
  timeframe,
  onTimeframeChange,
  feed,
}: {
  symbol: string;
  timeframe: Timeframe;
  onTimeframeChange: (timeframe: Timeframe) => void;
  feed: ReturnType<typeof useMarketFeed>;
}) {
  const [candles, setCandles] = useState<CandlesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const loading = candles === null && error === null;

  const feedBar = useMemo<ValidatedBar | null>(() => {
    const fed = feed.candle?.candle;
    if (!fed) return null;
    const [bar] = toBars([
      {
        open_time: new Date(fed.time * 1000).toISOString(),
        close_time: null,
        open: Number(fed.open),
        high: Number(fed.high),
        low: Number(fed.low),
        close: Number(fed.close),
        volume: Number(fed.volume),
      },
    ]);
    return bar ?? null;
  }, [feed.candle]);

  const fetchCandles = useCallback(async (): Promise<CandlesResponse> => {
    const envelope = await getCandles(symbol, timeframe);
    return envelope.data;
  }, [symbol, timeframe]);

  useEffect(() => {
    let cancelled = false;
    fetchCandles()
      .then((data) => {
        if (!cancelled) {
          setCandles(data);
          setError(null);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setCandles(null);
          setError(err instanceof ApiRequestError ? err.message : "Failed to load candles.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [fetchCandles]);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refreshMarketData(timeframe, symbol);
      setCandles(await fetchCandles());
      setError(null);
    } catch (err) {
      setError(err instanceof ApiRequestError ? `Refresh failed: ${err.message}` : "Refresh failed.");
    } finally {
      setRefreshing(false);
    }
  }, [fetchCandles, symbol, timeframe]);

  return (
    <section aria-label="Price chart" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div role="group" aria-label="Timeframe selector" className="flex items-center gap-1">
          {TIMEFRAMES.map((candidate) => (
            <button
              key={candidate}
              type="button"
              aria-pressed={timeframe === candidate}
              onClick={() => onTimeframeChange(candidate)}
              disabled={refreshing}
              className={
                timeframe === candidate
                  ? "px-2.5 py-1 rounded text-[11px] font-medium border bg-accent-bg text-accent border-accent-line focus-visible:outline focus-visible:outline-accent"
                  : "px-2.5 py-1 rounded text-[11px] font-medium border border-line text-ink2 hover:bg-hover focus-visible:outline focus-visible:outline-accent"
              }
            >
              {candidate}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={refreshing}
          className="px-2.5 py-1 rounded text-[11px] font-medium border border-line text-ink2 hover:bg-hover disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
        >
          {refreshing ? "Refreshing…" : "Refresh Data"}
        </button>
      </div>
      <CandleChart candlesResponse={candles} loading={loading} error={error} updateBar={feedBar} />
    </section>
  );
}

