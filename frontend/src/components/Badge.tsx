import type { ReactElement } from "react";

const TONES: Record<string, string> = {
  // Verified-good states
  PASSED: "bg-gain-bg text-gain border-gain-line",
  QUALIFIED: "bg-gain-bg text-gain border-gain-line",
  LIVE: "bg-gain-bg text-gain border-gain-line",
  COMPLETED: "bg-gain-bg text-gain border-gain-line",
  COMPLETE: "bg-gain-bg text-gain border-gain-line",
  // Feed states that are not a live stream
  DELAYED: "bg-warn-bg text-warn border-warn-line",
  CONNECTED: "bg-accent-bg text-accent border-accent-line",
  CONNECTING: "bg-recessed text-ink2 border-line",
  RECONNECTING: "bg-recessed text-ink2 border-line",
  DISCONNECTED: "bg-recessed text-ink2 border-line",
  ERROR: "bg-loss-bg text-loss border-loss-line",
  // Failure states
  FAILED: "bg-loss-bg text-loss border-loss-line",
  NOT_QUALIFIED: "bg-loss-bg text-loss border-loss-line",
  BLOCKED: "bg-loss-bg text-loss border-loss-line",
  // Warning / staleness
  STALE: "bg-warn-bg text-warn border-warn-line",
  // In-progress / partial
  PARTIAL: "bg-accent-bg text-accent border-accent-line",
  RUNNING: "bg-accent-bg text-accent border-accent-line",
  // Absent data — always muted, never colored as good or bad
  "NOT AVAILABLE": "bg-recessed text-ink3 border-line",
  UNAVAILABLE: "bg-recessed text-ink3 border-line",
  PENDING: "bg-recessed text-ink2 border-line",
  WAITING_FOR_ENGINES: "bg-recessed text-ink2 border-line",
  READY_FOR_AI: "bg-recessed text-ink2 border-line",
  VALIDATING_CONTEXT: "bg-recessed text-ink2 border-line",
  VALIDATING_OUTPUT: "bg-recessed text-ink2 border-line",
};

export function Badge({ label, mono = false }: { label: string; mono?: boolean }) {
  const tone = TONES[label] ?? "bg-recessed text-ink2 border-line";
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded border text-[11px] font-medium tracking-wide whitespace-nowrap ${tone} ${mono ? "font-mono" : ""}`}
    >
      {label}
    </span>
  );
}

export function DeltaText({ value }: { value: number | null | undefined }): ReactElement {
  if (value === null || value === undefined) {
    return <span className="text-ink3 tabular-nums">—</span>;
  }
  const tone = value > 0 ? "text-gain" : value < 0 ? "text-loss" : "text-ink2";
  const sign = value > 0 ? "+" : "";
  return (
    <span className={`font-mono tabular-nums ${tone}`}>
      {sign}
      {value.toFixed(2)}%
    </span>
  );
}
