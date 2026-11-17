"use client";

import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  HistogramSeries,
  createChart,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";

import type { Candle, CandlesResponse } from "@/types/api";

export interface ValidatedBar {
  time: UTCTimestamp;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/** Chart data adapter: validate per chart-engine-spec 18.1 before rendering. */
export function toBars(candles: Candle[]): ValidatedBar[] {
  const seen = new Set<number>();
  const bars: ValidatedBar[] = [];
  for (const candle of candles) {
    const time = Math.floor(Date.parse(candle.open_time) / 1000);
    const { open, high, low, close } = candle;
    if (
      !Number.isFinite(time) ||
      !Number.isFinite(open) ||
      !Number.isFinite(high) ||
      !Number.isFinite(low) ||
      !Number.isFinite(close) ||
      open <= 0 ||
      high < Math.max(open, close) ||
      low > Math.min(open, close) ||
      high < low
    ) {
      continue;
    }
    if (seen.has(time)) continue;
    seen.add(time);
    bars.push({ time: time as UTCTimestamp, open, high, low, close, volume: candle.volume ?? 0 });
  }
  bars.sort((a, b) => a.time - b.time);
  return bars;
}

const UP_COLOR = "#3fb950";
const DOWN_COLOR = "#f85149";

export default function CandleChart({
  candlesResponse,
  loading,
  error,
  className,
}: {
  candlesResponse: CandlesResponse | null;
  loading: boolean;
  error: string | null;
  className?: string;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { color: "transparent" },
        textColor: "#94a0b8",
        fontFamily: "var(--font-mono), monospace",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "#1f2633" },
        horzLines: { color: "#1f2633" },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#1f2633" },
      timeScale: { borderColor: "#1f2633", timeVisible: true, secondsVisible: false },
    });
    chartRef.current = chart;

    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: UP_COLOR,
      downColor: DOWN_COLOR,
      wickUpColor: UP_COLOR,
      wickDownColor: DOWN_COLOR,
      borderVisible: false,
    });
    const volumeSeries = chart.addSeries(
      HistogramSeries,
      { priceFormat: { type: "volume" }, priceScaleId: "" },
      1,
    );
    volumeSeries.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });

    if (candlesResponse) {
      const bars = toBars(candlesResponse.candles);
      candleSeries.setData(bars);
      volumeSeries.setData(
        bars.map((bar) => ({
          time: bar.time,
          value: bar.volume,
          color: bar.close >= bar.open ? "rgba(63,185,80,0.5)" : "rgba(248,81,73,0.5)",
        })),
      );
      chart.timeScale().fitContent();
    }

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [candlesResponse]);

  return (
    <div className={`bg-card border border-line rounded-lg overflow-hidden ${className ?? ""}`}>
      <div
        ref={containerRef}
        className="h-[420px] w-full"
        role="img"
        aria-label={`Candlestick chart${candlesResponse ? ` for ${candlesResponse.symbol}, ${candlesResponse.timeframe}` : ""}`}
      />
      <div className="flex items-center justify-between gap-2 border-t border-line px-3 py-2 text-[10px] text-ink3">
        {loading ? (
          <span>Loading candles…</span>
        ) : error ? (
          <span className="text-loss">{error}</span>
        ) : candlesResponse ? (
          <>
            <span>
              Provider feed: REST_PUBLIC · {candlesResponse.candles.length} candles loaded
            </span>
            <span>
              Data status {candlesResponse.freshness_status} · last candle {candlesResponse.data_timestamp ?? "—"}
            </span>
          </>
        ) : (
          <span>No candle data loaded.</span>
        )}
      </div>
    </div>
  );
}
