import React, { useState } from "react";
import * as api from "@/services/api";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, Legend,
} from "recharts";

const BAR_COLORS = ["#2563eb", "#16a34a", "#ea580c", "#9333ea", "#0891b2", "#db2777", "#ca8a04", "#4b5563"];
const num = (v: unknown): number | null => (typeof v === "number" ? v : (v != null && !isNaN(parseFloat(String(v))) ? parseFloat(String(v)) : null));

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
            <>
              <BarChartCard title="Composite score per aset"
                data={Object.entries(result.scores).map(([sym, it]) => ({ symbol: sym, composite: num(it.composite) }))}
                xKey="symbol" yKeys={["composite"]} />
              <FactorTable scores={result.scores} />
            </>
          )}
          {active === "ATTRIBUTION" && result.breakdown && (
            <>
              <div className="text-sm mb-2">Total return: <b>{result.total_return}</b></div>
              <BarChartCard title="Kontribusi per aset"
                data={result.breakdown.map((r) => ({ symbol: r.symbol, contribution: num(r.contribution) }))}
                xKey="symbol" yKeys={["contribution"]} />
            </>
          )}
          {active === "SCENARIO" && result.per_asset && (
            <>
              <div className="text-sm mb-2">Portfolio impact: <b>{result.portfolio_impact}</b></div>
              <BarChartCard title="Impact per aset"
                data={result.per_asset.map((r) => ({ symbol: String(r.symbol), impact: num(r.impact) }))}
                xKey="symbol" yKeys={["impact"]} />
            </>
          )}
          {active === "FUNDAMENTAL" && result.per_asset && (
            <BarChartCard title="Composite score per aset"
              data={result.per_asset.map((r) => ({ symbol: String(r.symbol), composite_score: num(r.composite_score) }))}
              xKey="symbol" yKeys={["composite_score"]} />
          )}
          {active === "SENTIMENT" && result.per_asset && (
            <BarChartCard title="Sentiment score per aset"
              data={result.per_asset.map((r) => ({ symbol: String(r.symbol), sentiment_score: num(r.sentiment_score) }))}
              xKey="symbol" yKeys={["sentiment_score"]} />
          )}
          {active === "CORRELATION" && result.correlation_matrix && (
            <BarChartCard title="Korelasi per pasangan aset"
              data={result.correlation_matrix.map((r) => ({ symbol: String(r.asset ?? r.symbol), correlation: num(r.correlation) }))}
              xKey="symbol" yKeys={["correlation"]} />
          )}
          {active === "BACKTEST" && result.metrics && (
            <BacktestMetrics metrics={result.metrics} />
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
function BarChartCard({ title, data, xKey, yKeys, height = 240 }: {
  title: string;
  data: Array<Record<string, unknown>>;
  xKey: string;
  yKeys: string[];
  height?: number;
}) {
  return (
    <div className="mb-3">
      <div className="text-xs font-semibold text-gray-600 mb-1">{title}</div>
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey={xKey} tick={{ fontSize: 11 }} interval={0} />
          <YAxis tick={{ fontSize: 11 }} width={56} tickFormatter={(v) => (typeof v === "number" ? (Math.abs(v) < 1 ? v.toFixed(3) : v.toFixed(2)) : String(v))} />
          <Tooltip formatter={(v) => [typeof v === "number" ? v.toFixed(5) : String(v)]} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {yKeys.map((k, i) => (
            <Bar key={k} dataKey={k} fill={BAR_COLORS[i % BAR_COLORS.length]} radius={[2, 2, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
function BacktestMetrics({ metrics }: { metrics: Record<string, number | string | null> }) {
  const yKeys = Object.keys(metrics).filter((k) => typeof metrics[k] === "number");
  const data = [{ name: "metrik", ...metrics }];
  return <BarChartCard title="Metrik backtest" data={data} xKey="name" yKeys={yKeys} />;
}
export default AnalyticsM4Panel;
