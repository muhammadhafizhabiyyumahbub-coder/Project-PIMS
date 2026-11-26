import React, { useState } from "react";
import * as api from "@/services/api";

type Engine =
  | "CORRELATION" | "BACKTEST" | "FACTOR"
  | "ATTRIBUTION" | "SCENARIO" | "FUNDAMENTAL" | "SENTIMENT";

// Generic shape of M4 engine responses (varies by engine; typed loosely).
type M4Result = {
  status?: string;
  calculation_status?: string;
  total_return?: number;
  metrics?: Record<string, number>;
  scores?: Record<string, { composite?: number; raw?: Record<string, number> }>;
  breakdown?: Array<{ symbol: string; contribution?: number; active_contribution?: number }>;
  per_asset?: Array<Record<string, number | string | null | undefined>>;
  portfolio_impact?: number;
  correlation_matrix?: Array<{ asset?: string; symbol?: string; correlation?: number }>;
  [k: string]: unknown;
};

const ENGINES: { id: Engine; label: string }[] = [
  { id: "CORRELATION", label: "Correlation" },
  { id: "BACKTEST", label: "Backtest" },
  { id: "FACTOR", label: "Factor" },
  { id: "ATTRIBUTION", label: "Attribution" },
  { id: "SCENARIO", label: "Scenario" },
  { id: "FUNDAMENTAL", label: "Fundamental" },
  { id: "SENTIMENT", label: "Sentiment" },
];

export const AnalyticsM4Panel: React.FC<{ portfolioId: string }> = ({ portfolioId }) => {
  const [active, setActive] = useState<Engine>("ATTRIBUTION");
  const [symbols, setSymbols] = useState("BTCUSDT, ETHUSDT, SOLUSDT");
  const [timeframe, setTimeframe] = useState("1d");
  const [limit, setLimit] = useState(300);
  const [scenarioType, setScenarioType] = useState<"SENSITIVITY" | "HISTORICAL">("HISTORICAL");
  const [shock, setShock] = useState("-0.1");
  const [result, setResult] = useState<M4Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const symList = symbols.split(",").map((s) => s.trim()).filter(Boolean);

  async function run() {
    setLoading(true); setError(null); setResult(null);
    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let data: any;
      switch (active) {
        case "CORRELATION":
          data = (await api.getCorrelation({ portfolio_id: portfolioId, timeframe, return_method: "SIMPLE", limit })).data; break;
        case "BACKTEST":
          data = (await api.runBacktest({ symbols: symList, strategy: "BUY_HOLD", timeframe, limit })).data; break;
        case "FACTOR":
          data = (await api.runFactor({ symbols: symList, factors: ["MOMENTUM", "VOLATILITY", "REVERSAL", "SIZE"], normalization: "ZSCORE", weighting: "EQUAL", timeframe, limit })).data; break;
        case "ATTRIBUTION":
          data = (await api.runAttribution({ portfolio_id: portfolioId, timeframe })).data; break;
        case "SCENARIO":
          data = (await api.runScenario({ portfolio_id: portfolioId, scenario_type: scenarioType, shock: scenarioType === "SENSITIVITY" ? parseFloat(shock) : undefined, timeframe, limit })).data; break;
        case "FUNDAMENTAL":
          data = (await api.runFundamental({ symbols: symList, timeframe })).data; break;
        case "SENTIMENT":
          data = (await api.runSentiment({ symbols: symList, timeframe })).data; break;
      }
      setResult(data);
    } catch (e) {
      const err = e as {
        data?: { error?: { code?: string; message?: string } };
        error?: { code?: string; message?: string };
        message?: string;
      };
      const code = err?.data?.error?.code || err?.error?.code;
      const msg = err?.data?.error?.message || err?.message || "Unknown error";
      setError(code ? `[${code}] ${msg}` : msg);
    } finally {
      setLoading(false);
    }
  }

  const status = result?.status || result?.calculation_status;
  const isDataGap = !!status && /UNAVAILABLE|INSUFFICIENT|INVALID/.test(status);

  return (
    <div className="p-4 bg-white rounded shadow">
      <h2 className="text-lg font-bold mb-3">Analytics M4</h2>
      <div className="flex flex-wrap gap-2 mb-3">
        {ENGINES.map((e) => (
          <button key={e.id} onClick={() => setActive(e.id)}
            className={`px-3 py-1.5 rounded text-sm ${active === e.id ? "bg-blue-600 text-white" : "bg-gray-100 hover:bg-gray-200"}`}>
            {e.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
        {["BACKTEST", "FACTOR", "FUNDAMENTAL", "SENTIMENT"].includes(active) && (
          <label className="col-span-2">
            Symbols (comma-separated)
            <input value={symbols} onChange={(e) => setSymbols(e.target.value)} className="w-full border rounded p-1.5 mt-1" />
          </label>
        )}
        {["ATTRIBUTION", "SCENARIO", "CORRELATION"].includes(active) && (
          <span className="text-gray-500">portfolio: {portfolioId.slice(0, 8)}…</span>
        )}
        {active === "SCENARIO" && (
          <label>Type
            <select value={scenarioType} onChange={(e) => setScenarioType(e.target.value as "SENSITIVITY" | "HISTORICAL")} className="w-full border rounded p-1.5 mt-1">
              <option value="HISTORICAL">Historical</option>
              <option value="SENSITIVITY">Sensitivity</option>
            </select>
          </label>
        )}
        {active === "SCENARIO" && scenarioType === "SENSITIVITY" && (
          <label>Shock (return)
            <input value={shock} onChange={(e) => setShock(e.target.value)} className="w-full border rounded p-1.5 mt-1" />
          </label>
        )}
        <label>Timeframe
          <select value={timeframe} onChange={(e) => setTimeframe(e.target.value)} className="w-full border rounded p-1.5 mt-1">
            <option value="1h">1h</option><option value="4h">4h</option><option value="1d">1d</option>
          </select>
        </label>
        <label>Limit
          <input type="number" value={limit} onChange={(e) => setLimit(parseInt(e.target.value) || 300)} className="w-full border rounded p-1.5 mt-1" />
        </label>
      </div>

      <button onClick={run} disabled={loading}
        className="px-4 py-2 bg-green-600 text-white rounded text-sm disabled:opacity-50">
        {loading ? "Running…" : `Run ${active}`}
      </button>

      {error && <div className="mt-3 p-2 rounded bg-amber-50 border border-amber-300 text-sm text-amber-800">{error}</div>}

      {result && (
        <div className="mt-3">
          {isDataGap && (
            <div className="mb-2 p-2 rounded bg-gray-50 border text-xs text-gray-600">
              Status: <b>{status}</b> — data tidak tersedia untuk input ini (bukan error). Ubah symbols/periode/timeframe.
            </div>
          )}
          {active === "FACTOR" && result.scores && (
            <FactorTable scores={result.scores} />
          )}
          {active === "ATTRIBUTION" && result.breakdown && (
            <>
              <div className="text-sm mb-2">Total return: <b>{result.total_return}</b></div>
              <Table rows={result.breakdown as unknown as Array<Record<string, number | string | null | undefined>>} cols={["symbol", "contribution", "active"]}
                render={(row) => [row.symbol, row.contribution, row.active_contribution]} />
            </>
          )}
          {active === "SCENARIO" && result.per_asset && (
            <>
              <div className="text-sm mb-2">Portfolio impact: <b>{result.portfolio_impact}</b></div>
              <Table rows={result.per_asset} cols={["symbol", "shock", "impact", "correlated"]}
                render={(row) => [row.symbol, row.shock, row.impact, row.correlated_impact]} />
            </>
          )}
          {active === "FUNDAMENTAL" && result.per_asset && (
            <Table rows={result.per_asset} cols={["symbol", "pe", "roe", "rev_growth", "score", "rank", "status"]}
              render={(row) => [row.symbol, row.pe, row.roe, row.revenue_growth, row.composite_score, row.rank, row.status]} />
          )}
          {active === "SENTIMENT" && result.per_asset && (
            <Table rows={result.per_asset} cols={["symbol", "score", "label", "confidence", "headlines", "status"]}
              render={(row) => [row.symbol, row.sentiment_score, row.label, row.confidence, row.headline_count, row.status]} />
          )}
          {active === "CORRELATION" && result.correlation_matrix && (
            <Table rows={result.correlation_matrix as unknown as Array<Record<string, number | string | null | undefined>>} cols={["asset", "corr"]}
              render={(row) => [row.asset ?? row.symbol, row.correlation]} />
          )}
          {active === "BACKTEST" && result.metrics && (
            <div className="text-sm space-y-1">
              {Object.entries(result.metrics).map(([k, v]) => (
                <div key={k} className="flex justify-between"><span>{k}</span><b>{typeof v === "number" ? v.toFixed(6) : JSON.stringify(v)}</b></div>
              ))}
            </div>
          )}
          {!(
            (active === "FACTOR" && result.scores) ||
            (active === "ATTRIBUTION" && result.breakdown) ||
            (active === "SCENARIO" && result.per_asset) ||
            (active === "FUNDAMENTAL" && result.per_asset) ||
            (active === "SENTIMENT" && result.per_asset) ||
            (active === "CORRELATION" && result.correlation_matrix) ||
            (active === "BACKTEST" && result.metrics)
          ) && (
            <pre className="text-xs bg-gray-100 p-2 rounded overflow-x-auto">{JSON.stringify(result, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
};

function Table({ rows, cols, render }: {
  rows: Array<Record<string, number | string | null | undefined>>;
  cols: string[];
  render: (row: Record<string, number | string | null | undefined>, i?: number) => (number | string | null | undefined)[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead><tr>{cols.map((c) => <th key={c} className="border p-1.5 text-left bg-gray-50">{c}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>{render(row, i).map((cell, j) => (
              <td key={j} className="border p-1.5">{cell == null ? <span className="text-gray-400">—</span> : cell}</td>
            ))}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function FactorTable({ scores }: { scores: M4Result["scores"] }) {
  const entries = Object.entries(scores ?? {});
  const cols = ["symbol", "MOMENTUM", "VOLATILITY", "REVERSAL", "SIZE", "composite"];
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs border-collapse">
        <thead><tr>{cols.map((c) => <th key={c} className="border p-1.5 text-left bg-gray-50">{c}</th>)}</tr></thead>
        <tbody>
          {entries.map(([sym, item]) => (
            <tr key={sym}>
              <td className="border p-1.5">{sym}</td>
              <td className="border p-1.5">{item.raw?.MOMENTUM ?? "—"}</td>
              <td className="border p-1.5">{item.raw?.VOLATILITY ?? "—"}</td>
              <td className="border p-1.5">{item.raw?.REVERSAL ?? "—"}</td>
              <td className="border p-1.5">{item.raw?.SIZE ?? "—"}</td>
              <td className="border p-1.5">{item.composite ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export default AnalyticsM4Panel;
