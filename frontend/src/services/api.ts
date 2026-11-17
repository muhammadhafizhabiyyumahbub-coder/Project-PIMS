"Centralized REST client. Unwraps the {data, meta} envelope; throws ApiRequestError on error envelopes.";

import type {
  Candle,
  CandlesResponse,
  Envelope,
  Holding,
  Opportunity,
  Portfolio,
  ResearchJob,
  ResearchReport,
  ScannerRunSummary,
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

export type { Candle, CandlesResponse, Opportunity, ResearchJob, ResearchReport, ScannerRunSummary };
