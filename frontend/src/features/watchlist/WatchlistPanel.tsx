"use client";

import { useCallback, useEffect, useState } from "react";

import AssetPicker from "@/features/portfolio/AssetPicker";
import {
  ApiRequestError,
  addWatchlistItem,
  createWatchlist,
  getWatchlist,
  listWatchlists,
} from "@/services/api";
import type { AssetSummary, Watchlist, WatchlistDetail } from "@/types/api";

/**
 * Watchlist panel (api-spec A17). List comes from GET /watchlists; items only
 * from the detail endpoint. Selecting a watchlist loads its items. Membership
 * never touches portfolio holdings.
 */
export default function WatchlistPanel() {
  const [rows, setRows] = useState<Watchlist[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [activeId, setActiveId] = useState<string | null>(null);
  const [detail, setDetail] = useState<WatchlistDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailKey, setDetailKey] = useState(0);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [asset, setAsset] = useState<AssetSummary | null>(null);
  const [adding, setAdding] = useState(false);

  const fetchRows = useCallback(async (): Promise<Watchlist[]> => {
    const envelope = await listWatchlists();
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
            error instanceof ApiRequestError ? error.message : "Unexpected error loading watchlists.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [fetchRows]);

  useEffect(() => {
    if (activeId === null) {
      setDetail(null);
      setDetailError(null);
      return;
    }
    let cancelled = false;
    getWatchlist(activeId)
      .then((envelope) => {
        if (!cancelled) {
          setDetail(envelope.data);
          setDetailError(null);
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setDetail(null);
          setDetailError(
            error instanceof ApiRequestError ? error.message : "Could not load watchlist items.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [activeId, detailKey]);

  const submitCreate = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setCreating(true);
      setFormError(null);
      try {
        const created = await createWatchlist({ name, description: description || undefined });
        setName("");
        setDescription("");
        setActiveId(created.data.id);
        setDetailKey((key) => key + 1);
        setRows(await fetchRows());
        setLoadError(null);
      } catch (error) {
        setFormError(
          error instanceof ApiRequestError ? error.message : "Watchlist creation failed unexpectedly.",
        );
      } finally {
        setCreating(false);
      }
    },
    [name, description, fetchRows],
  );

  const submitAddItem = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      if (activeId === null || asset === null) return;
      setAdding(true);
      setFormError(null);
      try {
        await addWatchlistItem(activeId, asset.id);
        setAsset(null);
        setDetailKey((key) => key + 1);
        setRows(await fetchRows());
      } catch (error) {
        setFormError(
          error instanceof ApiRequestError ? error.message : "Adding the asset failed unexpectedly.",
        );
      } finally {
        setAdding(false);
      }
    },
    [activeId, asset, fetchRows],
  );

  return (
    <section aria-label="Watchlists" className="flex flex-col gap-5">
      <div className="bg-card border border-line rounded-lg">
        <header className="px-4 py-3 border-b border-line">
          <h2 className="text-[15px] font-semibold">Watchlists</h2>
          <p className="text-[11px] text-ink3">
            Tracked instruments. Membership never affects portfolio holdings.
          </p>
        </header>

        {loadError !== null && (
          <div role="alert" className="mx-4 my-3 rounded border border-loss-line bg-loss-bg px-3 py-2 text-[12px] text-loss">
            {loadError}
            <button
              type="button"
              onClick={() => {
                fetchRows()
                  .then((data) => {
                    setRows(data);
                    setLoadError(null);
                  })
                  .catch((error: unknown) => {
                    setLoadError(
                      error instanceof ApiRequestError ? error.message : "Unexpected error loading watchlists.",
                    );
                  });
              }}
              className="ml-2 underline underline-offset-2"
            >
              Retry
            </button>
          </div>
        )}

        {rows === null && loadError === null && (
          <div className="px-4 py-10 text-center text-[12px] text-ink3" aria-live="polite">
            Loading watchlists...
          </div>
        )}

        {rows !== null && rows.length === 0 && (
          <div className="px-4 py-10 text-center">
            <p className="text-[13px] text-ink2">No watchlists yet. Create one below.</p>
          </div>
        )}

        {rows !== null && rows.length > 0 && (
          <ul className="divide-y divide-line">
            {rows.map((row) => (
              <li key={row.id}>
                <button
                  type="button"
                  onClick={() => setActiveId(row.id)}
                  aria-pressed={activeId === row.id}
                  className={`flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-hover focus-visible:outline focus-visible:outline-accent ${
                    activeId === row.id ? "bg-hover" : ""
                  }`}
                >
                  <div className="min-w-0">
                    <span className="text-[13px] font-semibold">{row.name}</span>
                    {row.description && (
                      <span className="ml-2 text-[11px] text-ink3 truncate">{row.description}</span>
                    )}
                  </div>
                  <span className="text-[11px] text-ink2 font-mono shrink-0">
                    {row.item_count} {row.item_count === 1 ? "item" : "items"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {activeId !== null && (
        <div className="bg-card border border-line rounded-lg">
          <header className="px-4 py-3 border-b border-line">
            <h2 className="text-[15px] font-semibold">{detail?.name ?? "Watchlist"} items</h2>
          </header>

          {detailError !== null && (
            <div role="alert" className="mx-4 my-3 rounded border border-loss-line bg-loss-bg px-3 py-2 text-[12px] text-loss">
              {detailError}
            </div>
          )}

          {detail === null && detailError === null && (
            <div className="px-4 py-8 text-center text-[12px] text-ink3" aria-live="polite">
              Loading items...
            </div>
          )}

          {detail !== null && detail.items.length === 0 && (
            <div className="px-4 py-8 text-center text-[13px] text-ink2">
              No instruments yet. Add one below.
            </div>
          )}

          {detail !== null && detail.items.length > 0 && (
            <ul className="divide-y divide-line">
              {detail.items.map((item) => (
                <li key={item.asset_id} className="flex items-center justify-between gap-3 px-4 py-2.5">
                  <span className="font-mono text-[13px] font-semibold">{item.symbol ?? "-"}</span>
                  <span className="text-[12px] text-ink2 truncate">{item.name ?? ""}</span>
                </li>
              ))}
            </ul>
          )}

          <form
            onSubmit={submitAddItem}
            aria-label="Add instrument"
            className="px-4 py-3 border-t border-line flex flex-wrap items-end gap-3"
          >
            <AssetPicker value={asset} onChange={setAsset} disabled={adding} />
            <button
              type="submit"
              disabled={adding || asset === null}
              className="bg-accent-bg text-accent border border-accent-line rounded px-3 py-1.5 text-[12px] font-medium hover:bg-hover disabled:opacity-50 focus-visible:outline focus-visible:outline-accent"
            >
              {adding ? "Adding..." : "Add"}
            </button>
          </form>
        </div>
      )}

      <form
        onSubmit={submitCreate}
        aria-label="Create watchlist"
        className="bg-card border border-line rounded-lg px-4 py-3 flex flex-col gap-3"
      >
        <h3 className="text-[13px] font-semibold">Create Watchlist</h3>
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
            {creating ? "Adding..." : "Tambah"}
          </button>
        </div>
        {formError && (
          <p role="alert" className="text-[12px] text-loss">
            {formError}
          </p>
        )}
      </form>
    </section>
  );
}
