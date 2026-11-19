"Centralized REST client. Unwraps the {data, meta} envelope; throws ApiRequestError on error envelopes.";

import type {
  AnalyticsRun,
  AnalyticsRunDetail,
  AnalyticsType,
  AssetSummary,
  Candle,
  CandlesResponse,
  Envelope,
  Holding,
  Opportunity,
  Portfolio,
  PortfolioAllocation,
  PortfolioPerformance,
  PortfolioRisk,
  PortfolioSnapshot,
  ResearchJob,
  ResearchReport,
  ScannerRunSummary,
  ScannerQualification,
  SnapshotCreated,
  Transaction,
  Valuation,
} from "@/types/api";

export class ApiRequestError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<Envelope<T>> {
  let response: Response;
  try {
    response = await fetch(path, { cache: "no-store", ...init });
  } catch {
    throw new ApiRequestError("NETWORK_ERROR", "Cannot reach the PIMS backend.", 0);
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiRequestError(
      "BAD_RESPONSE",
      `Backend returned non-JSON response (HTTP ${response.status}).`,
      response.status,
    );
  }
  const record = body as Record<string, unknown>;
  if (record && typeof record === "object" && "error" in record) {
    const err = record.error as { code?: string; message?: string };
    throw new ApiRequestError(
      err.code ?? "UNKNOWN",
      err.message ?? "Request failed.",
      response.status,
    );
  }
  if (!response.ok || !record || typeof record !== "object" || !("data" in record)) {
    throw new ApiRequestError(
      "BAD_RESPONSE",
      `Unexpected response from backend (HTTP ${response.status}).`,
      response.status,
    );
  }
  return record as unknown as Envelope<T>;
}

export function getOpportunities(params: {
  market?: string;
  qualification?: string;
  sort?: string;
}): Promise<Envelope<Opportunity[]>> {
  const query = new URLSearchParams();
  if (params.market && params.market !== "ALL") query.set("market", params.market);
  if (params.qualification && params.qualification !== "ALL") {
    query.set("qualification", params.qualification);
  }
  if (params.sort) query.set("sort", params.sort);
  const suffix = query.toString();
  return request<Opportunity[]>(`/api/v1/dashboard/instrument-opportunities${suffix ? `?${suffix}` : ""}`);
}

export function getCandles(symbol: string, timeframe: string, limit = 300): Promise<Envelope<CandlesResponse>> {
  return request<CandlesResponse>(
    `/api/v1/market-data/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`,
  );
}

export function refreshMarketData(timeframe: string, symbol?: string): Promise<Envelope<{ refreshed_candles: Record<string, number> }>> {
  const suffix = symbol ? `&symbol=${encodeURIComponent(symbol)}` : "";
  return request(`/api/v1/market-data/refresh?timeframe=${encodeURIComponent(timeframe)}${suffix}`, {
    method: "POST",
  });
}

export function runScanner(timeframe: string): Promise<Envelope<ScannerRunSummary>> {
  return request<ScannerRunSummary>(`/api/v1/scanner/run?timeframe=${encodeURIComponent(timeframe)}`, {
    method: "POST",
  });
}

/** Qualification detail for one stored scanner result (api-spec §12). */
export function getQualification(resultId: string): Promise<Envelope<ScannerQualification>> {
  return request<ScannerQualification>(
    `/api/v1/scanner/results/${encodeURIComponent(resultId)}/qualification`,
  );
}

export function requestResearch(
  symbol: string,
  timeframe: string,
): Promise<Envelope<{ action: string; job: ResearchJob }>> {
  return request(`/api/v1/research/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ symbol, timeframe }),
  });
}

export function searchAssets(query: string, limit = 8): Promise<Envelope<AssetSummary[]>> {
  return request<AssetSummary[]>(`/api/v1/assets/search?query=${encodeURIComponent(query)}&limit=${limit}`);
}

export function getResearchReport(reportId: string): Promise<Envelope<ResearchReport>> {
  return request<ResearchReport>(`/api/v1/research/reports/${encodeURIComponent(reportId)}`);
}

// --- Portfolio API (api-spec §8–§10) -----------------------------------------

export function listPortfolios(): Promise<Envelope<Portfolio[]>> {
  return request<Portfolio[]>(`/api/v1/portfolios`);
}

export function getPortfolio(portfolioId: string): Promise<Envelope<Portfolio>> {
  return request<Portfolio>(`/api/v1/portfolios/${encodeURIComponent(portfolioId)}`);
}

export function createPortfolio(body: { name: string; description?: string; base_currency: string }): Promise<Envelope<Portfolio>> {
  return request(`/api/v1/portfolios`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function updatePortfolio(
  portfolioId: string,
  body: { name?: string; description?: string | null; status?: string },
): Promise<Envelope<Portfolio>> {
  return request(`/api/v1/portfolios/${encodeURIComponent(portfolioId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function getHoldings(portfolioId: string): Promise<Envelope<Holding[]>> {
  return request<Holding[]>(`/api/v1/portfolios/${encodeURIComponent(portfolioId)}/holdings`);
}

export function getValuation(portfolioId: string): Promise<Envelope<Valuation>> {
  return request<Valuation>(`/api/v1/portfolios/${encodeURIComponent(portfolioId)}/valuation`);
}

export function listTransactions(
  portfolioId: string,
  cursor?: string,
): Promise<Envelope<Transaction[]>> {
  const suffix = cursor ? `&cursor=${encodeURIComponent(cursor)}` : "";
  return request<Transaction[]>(
    `/api/v1/transactions?portfolio_id=${encodeURIComponent(portfolioId)}&limit=50${suffix}`,
  );
}

export function createTransaction(body: {
  portfolio_id: string;
  transaction_type: string;
  asset_id?: string;
  quantity?: string;
  price?: string;
  gross_amount?: string;
  fee?: string;
}): Promise<Envelope<Transaction>> {
  return request(`/api/v1/transactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function createSnapshot(
  portfolioId: string,
  idempotencyKey?: string,
): Promise<Envelope<SnapshotCreated>> {
  return request<SnapshotCreated>(`/api/v1/portfolios/${encodeURIComponent(portfolioId)}/snapshots`, {
    method: "POST",
    headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {},
  });
}

export function listSnapshots(
  portfolioId: string,
  cursor?: string,
): Promise<Envelope<PortfolioSnapshot[]>> {
  const suffix = cursor ? `&cursor=${encodeURIComponent(cursor)}` : "";
  return request<PortfolioSnapshot[]>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/snapshots?limit=50${suffix}`,
  );
}

/** Window start is the only thing the UI picks; the backend reports the period
 * it actually measured (and returns UNAVAILABLE if no snapshot bounds it). */
export function getPerformance(
  portfolioId: string,
  params?: { start?: string },
): Promise<Envelope<PortfolioPerformance>> {
  const query = new URLSearchParams();
  if (params?.start) query.set("start", params.start);
  const suffix = query.toString();
  return request<PortfolioPerformance>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/performance${suffix ? `?${suffix}` : ""}`,
  );
}

export function getAllocation(portfolioId: string): Promise<Envelope<PortfolioAllocation>> {
  return request<PortfolioAllocation>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/allocation`,
  );
}

/** Risk window is the only knob; the backend decides the measured period and
 * returns UNAVAILABLE + reason when the stored candles cannot support it. */
export function getRisk(portfolioId: string, windowDays: number): Promise<Envelope<PortfolioRisk>> {
  return request<PortfolioRisk>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/risk?window=${windowDays}`,
  );
}

// --- Stored analytics runs (technical-decisions §7.12, Stage R) --------------

/** Manual trigger: compute now and persist a run + its results. */
export function createAnalyticsRun(
  portfolioId: string,
  body: { analysis_type: AnalyticsType; window_days?: number; start?: string },
): Promise<Envelope<AnalyticsRunDetail>> {
  return request<AnalyticsRunDetail>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/analytics/runs`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

/** Newest first; meta.pagination.next_cursor drives "Muat lagi". */
export function listAnalyticsRuns(
  portfolioId: string,
  cursor?: string,
): Promise<Envelope<AnalyticsRun[]>> {
  const suffix = cursor ? `&cursor=${encodeURIComponent(cursor)}` : "";
  return request<AnalyticsRun[]>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/analytics/runs?limit=50${suffix}`,
  );
}

export function getAnalyticsRun(
  portfolioId: string,
  runId: string,
): Promise<Envelope<AnalyticsRunDetail>> {
  return request<AnalyticsRunDetail>(
    `/api/v1/portfolios/${encodeURIComponent(portfolioId)}/analytics/runs/${encodeURIComponent(runId)}`,
  );
}

export type { Candle, CandlesResponse, Opportunity, ResearchJob, ResearchReport, ScannerRunSummary };