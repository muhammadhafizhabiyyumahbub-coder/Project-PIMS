import React, { useState } from "react";
import * as api from "@/services/api";
import {
  FundamentalRequest,
  FundamentalResponse,
  SentimentRequest,
  SentimentResponse,
} from "@/types/api";

export const AnalyticsM4Panel: React.FC = () => {
  const [activeEngine, setActiveEngine] = useState<string>("FUNDAMENTAL");
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const runAnalysis = async () => {
    setLoading(true);
    try {
      let res;
      if (activeEngine === "FUNDAMENTAL") {
        res = await api.runFundamental({ symbols: ["AAPL", "GOOGL"], timeframe: "1d" });
      } else if (activeEngine === "SENTIMENT") {
        res = await api.runSentiment({ symbols: ["AAPL"], timeframe: "1d" });
      }
      setResults(res?.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 bg-white rounded shadow">
      <h2 className="text-xl font-bold mb-4">Analytics M4</h2>
      <div className="flex space-x-4 mb-4">
        {["FUNDAMENTAL", "SENTIMENT"].map((e) => (
          <button
            key={e}
            onClick={() => setActiveEngine(e)}
            className={`p-2 rounded ${activeEngine === e ? "bg-blue-500 text-white" : "bg-gray-200"}`}
          >
            {e}
          </button>
        ))}
      </div>
      <button
        onClick={runAnalysis}
        className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
        disabled={loading}
      >
        {loading ? "Running..." : `Run ${activeEngine}`}
      </button>

      {results && (
        <div className="mt-4 overflow-x-auto">
          <pre className="text-xs bg-gray-100 p-2 rounded">
            {JSON.stringify(results, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};
