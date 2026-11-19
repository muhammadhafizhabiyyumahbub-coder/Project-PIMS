"use client";

import { useCallback, useEffect, useState } from "react";

import { marketWs, type ConnectionState, type WsMessage } from "@/services/ws";

export interface MarketQuoteData {
  asset_id: string;
  symbol: string;
  last_price: string | null;
  currency: string;
  provider: string;
  freshness: string;
  freshness_status: string;
  feed_status: string;
  data_timestamp: string | null;
  is_realtime: boolean;
  source: string;
  poll_interval_seconds: number;
}

export interface MarketCandleData {
  asset_id: string;
  symbol: string;
  timeframe: string;
  candle: {
    time: number;
    open: string;
    high: string;
    low: string;
    close: string;
    volume: string;
  } | null;
  is_closed: boolean | null;
  freshness: string;
  is_realtime: boolean;
  source: string;
  feed_status?: string;
  data_timestamp: string | null;
}

export interface MarketFeedState {
  connection: ConnectionState;
  quote: MarketQuoteData | null;
  candle: MarketCandleData | null;
  reconnect: () => void;
}

/**
 * One shared WebSocket for the whole tab (services/ws.ts). This hook only maps
 * the two market subscriptions for one symbol onto React state; it never
 * computes prices or statuses — those come from the backend messages.
 */
export function useMarketFeed(symbol: string, timeframe: string): MarketFeedState {
  const [connection, setConnection] = useState<ConnectionState>(marketWs.getStatus());
  const [quote, setQuote] = useState<MarketQuoteData | null>(null);
  const [candle, setCandle] = useState<MarketCandleData | null>(null);

  useEffect(() => marketWs.onStatusChange(setConnection), []);

  useEffect(() => {
    const onQuote = (msg: WsMessage) => {
      const next = msg.data as unknown as MarketQuoteData;
      setQuote((prev) =>
        prev &&
        prev.last_price === next.last_price &&
        prev.data_timestamp === next.data_timestamp &&
        prev.feed_status === next.feed_status
          ? prev
          : next,
      );
    };
    const onCandle = (msg: WsMessage) => {
      const next = msg.data as unknown as MarketCandleData;
      setCandle((prev) => {
        const a = prev?.candle;
        const b = next.candle;
        if (a && b && a.time === b.time && a.close === b.close && prev?.is_closed === next.is_closed) {
          return prev;
        }
        if (!a && !b) return prev;
        return next;
      });
    };

    const offQuote = marketWs.subscribe("market.quote", { symbol }, onQuote);
    const offCandle = marketWs.subscribe("market.candle", { symbol, timeframe }, onCandle);
    return () => {
      offQuote();
      offCandle();
    };
  }, [symbol, timeframe]);

  const reconnect = useCallback(() => marketWs.reconnect(), []);
  return { connection, quote, candle, reconnect };
}
