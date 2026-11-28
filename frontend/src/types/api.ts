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
  /** Identifies the scanner result row this opportunity came from; used to load
   * qualification detail via GET /scanner/results/{id}/qualification. */
  scanner_result_id: string;
  instrument: { symbol: string; name: string; asset_type: string };
  market: string | null;
  current_price: number | null;
  daily_change_pct: number | null;
  quote_currency: string | null;
  data_currency: string | null;
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

/** GET /scanner/results/{id}/qualification response body. */
export interface ScannerQualification {
  scanner_result_id: string;
  instrument: string;
  approval_status: string;
  passed_by: string[];
  engine_readiness: Record<string, EngineReadiness>;
  data_status: string;
  updated_at: string;
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

// --- Portfolio risk (technical-decisions §7.11, Stage L) ---------------------
// Metric values are decimal fractions as strings ("-0.034" = -3.4%), and so is
// risk_free_rate. A null metric means UNAVAILABLE with the reason in
// metric_reasons; the UI never renders null as 0 and never computes a metric.
// method is current_weights_buy_and_hold_approximation: a proxy from today's
// composition, not realized historical performance.

export interface RiskHolding {
  asset_id: string;
  symbol: string;
  /** Already a percentage string, as in the allocation endpoint. */
  weight: string | null;
}

export interface RiskMetrics {
  volatility: string | null;
  annualized_volatility: string | null;
  max_drawdown: string | null;
  sharpe: string | null;
  sortino: string | null;
  var_95: string | null;
  var_99: string | null;
  cvar_95: string | null;
  cvar_99: string | null;
}

export interface PortfolioRisk {
  portfolio_id: string;
  reporting_currency: string;
  window_days: number;
  observation_start: string | null;
  observation_end: string | null;
  return_count: number;
  method: string;
  weight_base: string;
  annualization: string;
  annualization_factor: number;
  risk_free_rate: string | null;
  data_status: string;
  data_status_reason: string | null;
  price_source: string;
  metrics: RiskMetrics;
  metric_reasons: Record<string, string>;
  holdings: RiskHolding[];
}

// --- Stored analytics runs (technical-decisions §7.12, Stage R) --------------
// A run and its stored result rows, exactly as persisted. Decimal strings keep
// the backend's precision; a null metric is UNAVAILABLE and is shown as such,
// never as 0. results length and window/period come from input_metadata.

export interface StoredPerformanceResult {
  id: string;
  analytics_run_id: string;
  portfolio_id: string;
  period_start: string;
  period_end: string;
  total_return: string | null;
  daily_return: string | null;
  realized_pnl: string | null;
  unrealized_pnl: string | null;
  cagr: string | null;
  reporting_currency: string;
  methodology: string;
  result_metadata: Record<string, unknown>;
}

export interface StoredRiskResult {
  id: string;
  analytics_run_id: string;
  portfolio_id: string | null;
  observation_period: string | null;
  volatility: string | null;
  max_drawdown: string | null;
  value_at_risk: string | null;
  confidence_level: string | null;
  risk_classification: string | null;
  result_metadata: Record<string, unknown>;
}

export interface StoredAllocationResult {
  id: string;
  analytics_run_id: string;
  portfolio_id: string;
  allocation_type: string;
  allocation_key: string;
  market_value: string | null;
  allocation_percentage: string | null;
  reporting_currency: string;
  result_metadata: Record<string, unknown>;
}

export interface AnalyticsRun {
  id: string;
  engine_type: string;
  portfolio_id: string | null;
  observation_start: string | null;
  observation_end: string | null;
  calculation_version: string;
  execution_status: string;
  started_at: string | null;
  completed_at: string | null;
  input_metadata: Record<string, unknown>;
  error_message: string | null;
}

export type AnalyticsType = "performance" | "risk" | "allocation" | "correlation" | "backtest" | "factor" | "attribution" | "scenario" | "fundamental" | "sentiment";

export interface CorrelationMatrixItem {
  asset_a: string;
  asset_b: string;
  correlation: number | null;
  observation_count: number;
  rolling: number[] | null;
  status: string;
}

export interface CorrelationResponse {
  portfolio_id: string;
  timeframe: string;
  return_method: string;
  calculation_status: string;
  calculation_version: string;
  correlation_matrix: CorrelationMatrixItem[];
  pairs_computed: number;
  series_used: number;
  analytics_run_id: string;
}

export interface BacktestRequest {
  symbols: string[];
  strategy: "BUY_HOLD" | "STATIC_WEIGHT";
  weights?: Record<string, number> | null;
  timeframe: string;
  limit: number;
  rebalance_every?: number;
  fee_bps?: number;
  slippage_bps?: number;
}

export interface BacktestResponse {
  run_id: string;
  strategy: string;
  calculation_status: string;
  metrics: Record<string, number | string | null>;
  walkforward: {
    in_sample_periods: number;
    out_of_sample_periods: number;
  };
  calculation_version: string;
  observation_start: string;
  observation_end: string;
}

export interface FactorRequest {
  symbols: string[];
  factors: string[];
  normalization: "ZSCORE" | "RANK";
  weighting: "EQUAL";
  timeframe: string;
  limit: number;
}

export interface FactorScoreItem {
  raw: Record<string, number | null>;
  z: Record<string, number | null>;
  composite: number | null;
}

export interface FactorResponse {
  run_id: string;
  calculation_status: string;
  strategy: string;
  factors: string[];
  normalization: string;
  weighting: string;
  universe_size: number;
  assets_included: number;
  excluded_assets: string[];
  calculation_version: string;
  scores: Record<string, FactorScoreItem>;
}

export interface AttributionRequest {
  portfolio_id: string;
  benchmark_asset_id?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  timeframe: string;
}

export interface AttributionBreakdownItem {
  symbol: string;
  contribution: string | null;
  active_contribution: string | null;
}

export interface AttributionResponse {
  run_id: string;
  portfolio_id: string;
  total_return: string | null;
  active_return: string | null;
  status: string;
  breakdown: AttributionBreakdownItem[];
}

export interface ScenarioRequest {
  portfolio_id: string;
  scenario_type: "SENSITIVITY" | "HISTORICAL" | "HYPOTHETICAL";
  asset_id?: string | null;
  shock?: number | null;
  period_start?: string | null;
  period_end?: string | null;
  timeframe: string;
  limit?: number;
}

export interface ScenarioAssetItem {
  symbol: string;
  shock: string | null;
  impact: string | null;
  correlated_impact: string | null;
}

export interface ScenarioResponse {
  run_id: string;
  portfolio_id: string;
  scenario_type: string;
  portfolio_impact: string | null;
  per_asset: ScenarioAssetItem[];
  status: string;
}

export interface FundamentalRequest {
  symbols: string[];
  timeframe: string;
}

export interface FundamentalAssetItem {
  symbol: string;
  pe: number | null;
  roe: number | null;
  revenue_growth: number | null;
  composite_score: number | null;
  rank: number | null;
  status: string;
  reason: string | null;
}

export interface FundamentalResponse {
  run_id: string;
  status: string;
  per_asset: FundamentalAssetItem[];
}

export interface SentimentRequest {
  symbols: string[];
  timeframe: string;
}

export interface SentimentAssetItem {
  symbol: string;
  sentiment_score: number | null;
  label: string;
  confidence: number | null;
  headline_count: number;
  status: string;
  reason?: string | null;
}

export interface SentimentResponse {
  run_id: string;
  status: string;
  per_asset?: SentimentAssetItem[];
}

export interface StoredCorrelationResult {
  id: string;
  analytics_run_id: string;
  asset_a_id: string;
  asset_b_id: string;
  correlation_value: number;
  observation_count: number;
  observation_period: string;
  calculation_method: string;
  result_metadata: Record<string, unknown>;
}

export interface StoredBacktestResult {
  id: string;
  analytics_run_id: string;
  metric: string;
  value: number | null;
  detail: Record<string, unknown>;
}

export interface StoredFactorResult {
  id: string;
  analytics_run_id: string;
  asset_id: string;
  symbol: string;
  raw_factors: Record<string, unknown>;
  z_factors: Record<string, unknown>;
  composite_score: number | null;
  excluded: boolean;
  result_metadata: Record<string, unknown>;
}

export interface StoredAttributionResult {
  id: string;
  analytics_run_id: string;
  asset_id: string | null;
  symbol: string;
  contribution: number | null;
  active_contribution: number | null;
  result_metadata: Record<string, unknown>;
}

export interface StoredScenarioResult {
  id: string;
  analytics_run_id: string;
  asset_id: string | null;
  symbol: string | null;
  scenario_type: string;
  shock: number | null;
  impact: number | null;
  correlated_impact: number | null;
  result_metadata: Record<string, unknown>;
}

export interface StoredFundamentalResult {
  id: string;
  analytics_run_id: string;
  asset_id: string | null;
  symbol: string;
  pe: number | null;
  roe: number | null;
  revenue_growth: number | null;
  composite_score: number | null;
  rank: number | null;
  result_metadata: Record<string, unknown>;
}

export interface StoredSentimentResult {
  id: string;
  analytics_run_id: string;
  asset_id: string | null;
  symbol: string;
  sentiment_score: number | null;
  label: string | null;
  confidence: number | null;
  headline_count: number | null;
  result_metadata: Record<string, unknown>;
}

/** A stored analytics run plus its result rows (POST returns this too). */
export interface AnalyticsRunDetail {
  run: AnalyticsRun;
  results: Array<
    | StoredPerformanceResult
    | StoredRiskResult
    | StoredAllocationResult
    | StoredCorrelationResult
    | StoredBacktestResult
    | StoredFactorResult
    | StoredAttributionResult
    | StoredScenarioResult
    | StoredFundamentalResult
    | StoredSentimentResult
  >;
}

// --- Watchlists (api-spec §17) ----------------------------------------------
// Membership carries no valuation: an item is identity only (asset_id/symbol).
// item_count comes from the backend; the UI never computes it.

export interface Watchlist {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  item_count: number;
}

export interface WatchlistItem {
  asset_id: string;
  symbol: string | null;
  name: string | null;
  added_at: string;
}

export interface WatchlistDetail extends Watchlist {
  items: WatchlistItem[];
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
