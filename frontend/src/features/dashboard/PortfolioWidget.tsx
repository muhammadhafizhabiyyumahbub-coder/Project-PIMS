"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { formatSignedMoneyString, formatMoneyString, formatReturnPct, pnlTone } from "@/lib/format";
import { ApiRequestError, getPerformance, getValuation, listPortfolios } from "@/services/api";
import type { Portfolio, PortfolioPerformance, Valuation } from "@/types/api";

const MAX_WIDGET_ROWS = 4;

/** One row per portfolio. Rows are never summed in the UI: cross-portfolio
 * aggregation must come from the backend (portfolio-engine-spec requires a
 * valid aggregation methodology; until it exists, show values as delivered). */
export default function PortfolioWidget() {
  const [portfolios, setPortfolios] = useState<Portfolio[] | null>(null);
  const [valuations, setValuations] = useState<Record<string, Valuation>>({});
  const [performances, setPerformances] = useState<Record<string, PortfolioPerformance>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  const retry = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    let cancelled = false;
    listPortfolios()
      .then(async (listEnvelope) => {
        const list = listEnvelope.data;
        if (cancelled) return;
        setPortfolios(list);
        const results = await Promise.allSettled(
          list.map(async (p) => {
            const [valuation, performance] = await Promise.all([
              getValuation(p.id),
              getPerformance(p.id),
            ]);
            return { valuation: valuation.data, performance: performance.data };
          }),
        );
        if (cancelled) return;
        const valuationMap: Record<string, Valuation> = {};
        const performanceMap: Record<string, PortfolioPerformance> = {};
        results.forEach((result, index) => {
          if (result.status === "fulfilled") {
            valuationMap[list[index].id] = result.value.valuation;
            performanceMap[list[index].id] = result.value.performance;
          }
        });
        setValuations(valuationMap);
        setPerformances(performanceMap);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setPortfolios(null);
        setLoadError(
          error instanceof ApiRequestError ? error.message : "Unexpected error loading portfolio summary.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return (
    <section aria-label="Portfolio summary" className="bg-card border border-line rounded-lg">
      <header className="flex items-center justify-between gap-3 px-4 py-3 border-b border-line">
        <div>
          <h2 className="text-[15px] font-semibold">Portfolios</h2>
          <p className="text-[11px] text-ink3">Value as reported by the Portfolio Engine per portfolio.</p>
        </div>
        <Link href="/portfolios" className="text-[11px] text-accent underline underline-offset-2 focus-visible:outline focus-visible:outline-accent">
          Manage portfolios
        </Link>
      </header>

      {loadError !== null && (
        <div role="alert" className="mx-4 my-3 rounded border border-loss-line bg-loss-bg px-3 py-2 text-[12px] text-loss">
          {loadError}
          <button type="button" onClick={retry} className="ml-2 underline underline-offset-2">
            Retry
          </button>
        </div>
      )}

      {portfolios === null && loadError === null && (
        <div className="px-4 py-8 text-center text-[12px] text-ink3" aria-live="polite">
          Loading portfolio summary…
        </div>
      )}

      {portfolios !== null && portfolios.length === 0 && (
        <div className="px-4 py-8 text-center">
          <p className="text-[13px] text-ink2">
            No portfolios yet.{" "}
            <Link href="/portfolios" className="text-accent underline underline-offset-2">
              Create one
            </Link>{" "}
            to start tracking value and P&amp;L.
          </p>
        </div>
      )}

      {portfolios !== null && portfolios.length > 0 && (
        <ul className="divide-y divide-line">
          {portfolios.slice(0, MAX_WIDGET_ROWS).map((portfolio) => {
            const valuation = valuations[portfolio.id];
            return (
              <li key={portfolio.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                <div className="min-w-0">
                  <Link
                    href={`/portfolios/${encodeURIComponent(portfolio.id)}`}
                    className="text-[13px] font-semibold hover:underline underline-offset-2 focus-visible:outline focus-visible:outline-accent"
                  >
                    {portfolio.name}
                  </Link>
                  <p className="text-[10px] text-ink3 font-mono">{portfolio.base_currency}</p>
                </div>
                {valuation === undefined ? (
                  <span className="text-[11px] text-ink3">loading…</span>
                ) : (
                  <div className="flex flex-wrap items-center gap-3 shrink-0">
                    <span className="text-[13px] font-mono tabular-nums">
                      {valuation.total_value === null ? (
                        <span className="text-ink3 text-[11px]">value not available ({valuation.valuation_status.toLowerCase()})</span>
                      ) : (
                        formatMoneyString(valuation.total_value)
                      )}
                    </span>
                    <span className={`text-[11px] font-mono tabular-nums ${pnlTone(valuation.unrealized_pnl)}`}>
                      {valuation.unrealized_pnl === null ? "—" : formatSignedMoneyString(valuation.unrealized_pnl)}
                    </span>
                    <Badge label={valuation.valuation_status} />
                    <div className="flex flex-col items-end gap-0.5">
                      <span className="text-[10px] text-ink2 font-sans">TWR</span>
                      <span
                        className="text-[11px] font-mono tabular-nums"
                        title={performances[portfolio.id]?.twr_reason ?? undefined}
                      >
                        {performances[portfolio.id]?.twr === null
                          ? "tidak tersedia"
                          : formatReturnPct(performances[portfolio.id]?.twr)}
                      </span>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
