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

// --- Portfolio domain (api-spec §8–§10) -------------------------------------
// All monetary fields are decimal strings from the backend (api-spec §5.3).
// They must never be converted to Number for arithmetic or comparison.

export interface Portfolio {
  id: string;
  name: string;
  description: string | null;
  base_currency: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Transaction {
  id: string;
  portfolio_id: string;
  asset_id: string | null;
  transaction_type: string;
  quantity: string | null;
  price: string | null;
  gross_amount: string | null;
  fee: string | null;
  currency: string;
  executed_at: string;
  idempotency_key: string | null;
  notes: string | null;
  created_at: string;
}

export interface Holding {
  asset_id: string;
  symbol: string;
  quantity: string | null;
  average_cost: string | null;
  cost_basis: string | null;
  market_price: string | null;
  market_value: string | null;
  unrealized_pnl: string | null;
  realized_pnl: string | null;
  price_status: string;
  price_time: string | null;
  currency: string;
  valuation_timestamp: string;
}

export interface ValuationPosition {
  asset_id: string;
  symbol: string;
  quantity: string | null;
  average_cost: string | null;
  cost_basis: string | null;
  market_price: string | null;
  market_value: string | null;
  price_status: string;
  unrealized_pnl: string | null;
}

export interface Valuation {
  portfolio_id: string;
  valuation_status: string;
  reporting_currency: string;
  cash_value: string | null;
  invested_value: string | null;
  total_value: string | null;
  realized_pnl: string | null;
  unrealized_pnl: string | null;
  valued_at: string;
  positions: ValuationPosition[];
}

// --- Portfolio snapshots (technical-decisions §7.9) -------------------------
// Values the valuation could not produce are null; never treated as zero.

export interface SnapshotPosition {
  asset_id: string;
  symbol: string;
  quantity: string | null;
  market_price: string | null;
  market_value: string | null;
  price_status: string;
}

export interface PortfolioSnapshot {
  id: string;
  portfolio_id: string;
  snapshot_at: string;
  total_value: string | null;
  cash_value: string | null;
  invested_value: string | null;
  reporting_currency: string;
  valuation_status: string;
  status_reason: string | null;
  realized_pnl: string | null;
  unrealized_pnl: string | null;
  positions: SnapshotPosition[];
  created_at: string;
}

export interface SnapshotCreated extends PortfolioSnapshot {
  /** True when the backend returned an existing row for the same idempotency key. */
  idempotent_replay: boolean;
}

// --- Portfolio performance (technical-decisions §7.10, spec §10) ------------
// Returns are decimal fractions as strings (e.g. "0.25" = 25%), fixed 12 dp.
// A null return means UNAVAILABLE: the paired *_reason explains why. The UI
// must never render null as 0 and never recompute a return on the client.

export interface PortfolioPerformance {
  portfolio_id: string;
  reporting_currency: string;
  period_start: string | null;
  period_end: string | null;
  period_days: number | null;
  return_status: string;
  twr: string | null;
  twr_reason: string | null;
  simple_return: string | null;
  simple_return_reason: string | null;
  sub_period_count: number;
  cagr: string | null;
  cagr_reason: string | null;
  realized_pnl: string | null;
  unrealized_pnl: string | null;
}

// --- Portfolio allocation (allocation-engine-spec, Stage J) -----------------
// Weights and percentages are already-percentage decimal strings. The client
// renders them verbatim and never does arithmetic on them.

export interface AllocationSlice {
  name: string;
  market_value: string | null;
  weight: string | null;
  holdings_count: number;
}

export interface AllocationIndividualAsset {
  asset_id: string;
  symbol: string;
  name: string | null;
  asset_class: string;
  market: string;
  currency: string;
  quantity: string | null;
  market_price: string | null;
  price_status: string;
  price_time: string | null;
  market_value: string | null;
  weight: string | null;
}

/** A holding with no price. cost_basis is a proxy, not a market value. */
export interface UnpricedPosition {
  asset_id: string;
  symbol: string;
  quantity: string | null;
  cost_basis: string | null;
}

export interface AllocationCoverage {
  total_components: number;
  covered_components: number;
  unvalued_components: number;
  coverage_percentage: string | null;
  position_coverage_percentage: string | null;
  value_known_percentage: string | null;
}

export interface AllocationConcentration {
  largest_holding_symbol: string | null;
  largest_holding_weight: string | null;
  top_3_weight: string | null;
  top_5_weight: string | null;
  top_10_weight: string | null;
  largest_market: string | null;
  largest_currency: string | null;
  largest_sector: string | null;
  largest_sector_reason: string | null;
}

export interface PortfolioAllocation {
  weight_base: string;
  portfolio_id: string;
  reporting_currency: string;
  valuation_timestamp: string;
  data_status: string;
  data_status_reason: string | null;
  total_value: string | null;
  cash_value: string | null;
  invested_value: string | null;
  coverage: AllocationCoverage;
  unpriced_positions: UnpricedPosition[];
  categories: {
    asset_class: AllocationSlice[];
    market: AllocationSlice[];
    sector: { status: string; reason: string | null; allocation: AllocationSlice[] };
    currency: AllocationSlice[];
    individual_asset: AllocationIndividualAsset[];
    cash: { currency: string; value: string | null; weight: string | null };
  };
  concentration: AllocationConcentration;
}

// --- Asset summary (api-spec §11) -------------------------------------------
// id and symbol are internal identity; provider symbols are never surfaced here.

export interface AssetSummary {
  id: string;
  symbol: string;
  name: string;
  market: string | null;
  exchange: string | null;
  quote_currency: string | null;
  asset_type: string;
  base_currency: string | null;
}
