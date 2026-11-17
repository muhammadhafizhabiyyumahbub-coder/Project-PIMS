"API response types matching the backend api-spec.md envelope.";

export type EngineLabel =
  | "PASSED"
  | "FAILED"
  | "PENDING"
  | "RUNNING"
  | "BLOCKED"
  | "STALE"
  | "READY"
  | "NOT AVAILABLE";

export interface EngineReadiness {
  state: EngineLabel | string;
  label: EngineLabel | string;
}

export interface Opportunity {
  instrument: { symbol: string; name: string; asset_type: string };
  market: string | null;
  current_price: number | null;
  daily_change_pct: number | null;
  quote_currency: string | null;
  scanner_score: number | null;
  scanner_rank: number | null;
  market_regime: string | null;
  risk_status: string | null;
  approval_status: string;
  passed_by: string[];
  engine_readiness: Record<string, EngineReadiness>;
  updated_at: string | null;
  data_status: string;
}

export interface Candle {
  open_time: string;
  close_time: string | null;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number | null;
}

export interface CandlesResponse {
  symbol: string;
  timeframe: string;
  freshness_status: string;
  data_timestamp: string | null;
  candles: Candle[];
}

export interface ScannerRunSummary {
  scanner_run_id: string;
  execution_status: string;
  universe_size: number | null;
  eligible_count: number | null;
  result_count: number | null;
  completed_at: string | null;
}

export interface ResearchJob {
  job_id: string;
  request_id: string;
  status: string;
  attempts: number;
  max_retries: number;
  engine_readiness: Record<string, EngineReadiness> | null;
  provider: string | null;
  model: string | null;
  report_id: string | null;
  error_code: string | null;
  error_message: string | null;
}

export interface ResearchReport {
  report_id: string;
  title: string | null;
  research_type: string;
  provider: string;
  model: string;
  execution_status: string;
  generated_at: string | null;
  report_content: Record<string, unknown>;
}

export interface Envelope<T> {
  data: T;
  meta: Record<string, unknown>;
}

export interface ApiError {
  error: { code: string; message: string; details?: unknown[] };
}
