"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { formatUtc } from "@/lib/format";
import { ApiRequestError, createPortfolio, listPortfolios } from "@/services/api";
import type { Portfolio } from "@/types/api";

const CURRENCIES = ["USD", "EUR", "IDR"] as const;

export default function PortfolioList() {
  const [rows, setRows] = useState<Portfolio[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState<string>("USD");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchRows = useCallback(async (): Promise<Portfolio[]> => {
    const envelope = await listPortfolios();
    return envelope.data;
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchRows()
      .then((data) => {
        if (!cancelled) {
          setRows(data);
          setLoadError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setRows(null);
          setLoadError(
            error instanceof ApiRequestError ? error.message : "Unexpected error loading portfolios.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [fetchRows]);

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setCreating(true);
      setFormError(null);
      try {
        await createPortfolio({
          name,
          description: description || undefined,
          base_currency: currency,
        });
        setName("");
        setDescription("");
        setRows(await fetchRows());
        setLoadError(null);
      } catch (error) {
        setFormError(
          error instanceof ApiRequestError ? error.message : "Portfolio creation failed unexpectedly.",
        );
      } finally {
        setCreating(false);
      }
    },
    [name, currency, description, fetchRows],
  );

  return (
    <section aria-label="Portfolios" className="flex flex-col gap-5">
      <div className="bg-card border border-line rounded-lg">
        <header className="px-4 py-3 border-b border-line">
          <h2 className="text-[15px] font-semibold">Your Portfolios</h2>
          <p className="text-[11px] text-ink3">
            Separately tracked portfolios. Values shown on each portfolio&apos;s detail page.
          </p>
        </header>

        {loadError !== null && (
          <div role="alert" className="mx-4 my-3 rounded border border-loss-line bg-loss-bg px-3 py-2 text-[12px] text-loss">
            {loadError}
            <button
              type="button"
              onClick={() => void fetchRows().then((d) => setRows(d))}
              className="ml-2 underline underline-offset-2"
            >
              Retry
            </button>
          </div>
        )}

        {rows === null && loadError === null && (
          <div className="px-4 py-10 text-center text-[12px] text-ink3" aria-live="polite">
            Loading portfolios…
          </div>
        )}

        {rows !== null && rows.length === 0 && (
          <div className="px-4 py-10 text-center">
            <p className="text-[13px] text-ink2">
              No portfolios yet. Create one below to start recording transactions.
            </p>
          </div>
        )}

        {rows !== null && rows.length > 0 && (
          <ul className="divide-y divide-line">
            {rows.map((row) => (
              <li key={row.id}>
                <Link
                  href={`/portfolios/${encodeURIComponent(row.id)}`}
                  className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-hover focus-visible:outline focus-visible:outline-accent"
                >
                  <div className="min-w-0">
                    <span className="text-[13px] font-semibold">{row.name}</span>
                    {row.description && (
                      <span className="ml-2 text-[11px] text-ink3 truncate">{row.description}</span>
                    )}
                    <p className="text-[10px] text-ink3">Created {formatUtc(row.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-[11px] text-ink2 font-mono">{row.base_currency}</span>
                    <Badge label={row.status} />
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      <form
        onSubmit={submit}
        aria-label="Create portfolio"
        className="bg-card border border-line rounded-lg px-4 py-3 flex flex-col gap-3"
      >
        <h3 className="text-[13px] font-semibold">Create Portfolio</h3>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-[11px] text-ink2">
            Name
            <input
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              maxLength={150}
              className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink w-[220px] focus-visible:outline focus-visible:outline-accent"
            />
          </label>
          <label className="flex flex-col gap-1 text-[11px] text-ink2">
            Base currency
            <select
              value={currency}
              onChange={(event) => setCurrency(event.target.value)}
              className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink focus-visible:outline focus-visible:outline-accent"
            >
              {CURRENCIES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 text-[11px] text-ink2">
            Description (optional)
            <input
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink w-[260px] focus-visible:outline focus-visible:outline-accent"
            />
          </label>
          <button
            type="submit"
            disabled={creating || name.trim().length === 0}
            className="bg-accent-bg text-accent border border-accent-line rounded px-3 py-1.5 text-[12px] font-medium hover:bg-hover disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
          >
            {creating ? "Creating…" : "Create"}
          </button>
        </div>
        {formError && (
          <p role="alert" className="text-[12px] text-loss">
            {formError}
          </p>
        )}
        <p className="text-[10px] text-ink3">
          Reporting currency is fixed after creation: all transactions must use it.
        </p>
      </form>
    </section>
  );
}
