"use client";

import { useCallback, useState } from "react";

import { Badge } from "@/components/Badge";
import { formatUtc } from "@/lib/format";
import { ApiRequestError, getResearchReport, requestResearch } from "@/services/api";
import type { ResearchJob, ResearchReport } from "@/types/api";

export default function ResearchPanel({ symbol, timeframe }: { symbol: string; timeframe: string }) {
  const [job, setJob] = useState<ResearchJob | null>(null);
  const [report, setReport] = useState<ResearchReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trigger = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const envelope = await requestResearch(symbol, timeframe);
      const currentJob = envelope.data.job;
      setJob(currentJob);
      if (currentJob.status === "COMPLETED" && currentJob.report_id) {
        const reportEnv = await getResearchReport(currentJob.report_id);
        setReport(reportEnv.data);
      } else {
        setReport(null);
      }
    } catch (err) {
      setError(err instanceof ApiRequestError ? err.message : "Failed to initiate AI research.");
    } finally {
      setBusy(false);
    }
  }, [symbol, timeframe]);

  return (
    <section aria-label="AI Research panel" className="bg-card border border-line rounded-lg p-4 flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-3">
        <div>
          <h2 className="text-[15px] font-semibold">AI Research Assistant</h2>
          <p className="text-[11px] text-ink3">
            Controlled orchestration. Requires all deterministic engines to pass before running.
          </p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => void trigger()}
          className="px-3 py-1.5 rounded text-[12px] font-medium border bg-accent-bg text-accent border-accent-line hover:border-accent disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
        >
          {busy ? "Running Research…" : "Generate AI Research"}
        </button>
      </header>

      {error && (
        <div role="alert" className="rounded border border-loss-line bg-loss-bg px-3 py-2 text-[12px] text-loss">
          {error}
        </div>
      )}

      {job === null && !busy && (
        <div className="py-6 text-center text-[12px] text-ink3">
          No AI research report generated yet for {symbol} ({timeframe}). Click above to run gated orchestration.
        </div>
      )}

      {job && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-2 bg-recessed border border-line rounded px-3 py-2 text-[11px]">
            <div className="flex items-center gap-2">
              <span className="text-ink3">Status</span>
              <Badge label={job.status} />
              {job.provider && <span className="text-ink2">Provider: {job.provider} ({job.model ?? "default"})</span>}
            </div>
            <span className="text-ink3">Attempts: {job.attempts}/{job.max_retries}</span>
          </div>

          {job.engine_readiness && (
            <div className="flex flex-col gap-1 text-[11px]">
              <span className="text-ink3 font-medium">Engine Readiness Checklist</span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {Object.entries(job.engine_readiness).map(([engine, info]) => (
                  <div key={engine} className="flex items-center justify-between bg-recessed border border-line rounded px-2.5 py-1.5">
                    <span className="font-mono text-ink2">{engine}</span>
                    <Badge label={String(info.label)} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {job.status === "BLOCKED" && (
            <div className="rounded border border-loss-line bg-loss-bg p-3 text-[12px]">
              <p className="font-semibold text-loss">Research Blocked by Engine Gate</p>
              <p className="text-loss mt-0.5">{job.error_message}</p>
              <p className="text-[11px] text-ink3 mt-2">
                All required engines (TECHNICAL, MARKET_REGIME, RISK, SCANNER) must have non-stale PASSED outputs before AI interpretation can proceed.
              </p>
            </div>
          )}

          {job.status === "FAILED" && (
            <div className="rounded border border-loss-line bg-loss-bg p-3 text-[12px]">
              <p className="font-semibold text-loss">Research Request Failed [{job.error_code}]</p>
              <p className="text-loss mt-0.5">{job.error_message}</p>
            </div>
          )}
        </div>
      )}

      {report && (
        <article className="flex flex-col gap-4 border-t border-line pt-4">
          <header className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-[14px] font-semibold">{report.title ?? `${symbol} Research Report`}</h3>
            <span className="text-[11px] text-ink3">Generated {formatUtc(report.generated_at)}</span>
          </header>

          <ReportContent content={report.report_content} />

          <footer className="border-t border-line pt-2 text-[10px] text-ink3">
            Disclaimer: AI Research outputs are analytical interpretations of deterministic engine data. They do not constitute factual claims, financial advice, or automated trade signals.
          </footer>
        </article>
      )}
    </section>
  );
}

function ReportContent({ content }: { content: Record<string, unknown> }) {
  return (
    <div className="flex flex-col gap-3.5 text-[12px]">
      {Object.entries(content).map(([key, value]) => {
        const title = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        return (
          <section key={key} className="flex flex-col gap-1">
            <h4 className="font-semibold text-ink2 text-[12px]">{title}</h4>
            <ValueDisplay value={value} />
          </section>
        );
      })}
    </div>
  );
}

function ValueDisplay({ value }: { value: unknown }) {
  if (typeof value === "string") {
    return <p className="text-ink text-[12px] leading-relaxed">{value}</p>;
  }
  if (Array.isArray(value)) {
    return (
      <ul className="list-disc list-inside flex flex-col gap-1 text-ink pl-1">
        {value.map((item, index) => (
          <li key={index}>{typeof item === "string" ? item : JSON.stringify(item)}</li>
        ))}
      </ul>
    );
  }
  if (typeof value === "object" && value !== null) {
    return (
      <pre className="bg-recessed border border-line rounded p-2 font-mono text-[11px] text-ink2 overflow-x-auto">
        {JSON.stringify(value, null, 2)}
      </pre>
    );
  }
  return <span className="text-ink">{String(value)}</span>;
}
