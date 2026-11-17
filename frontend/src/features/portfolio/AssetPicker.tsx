"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiRequestError, searchAssets } from "@/services/api";
import type { AssetSummary } from "@/types/api";

interface AssetPickerProps {
  value: AssetSummary | null;
  onChange: (asset: AssetSummary | null) => void;
  disabled?: boolean;
}

/**
 * Pemilih aset via GET /assets/search (api-spec §11). Hanya identitas internal
 * (id + symbol) yang dipakai; simbol provider (Bybit/Yahoo) tidak pernah
 * muncul sebagai identitas aset.
 */
export default function AssetPicker({
  value,
  onChange,
  disabled = false,
}: AssetPickerProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AssetSummary[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const next = event.target.value;
    setQuery(next);
    // Editing the query invalidates any previous selection: the choice must
    // follow what is typed right now.
    if (next.trim().length > 0 && next !== value?.symbol) {
      onChange(null);
    }
    setError(null);
  }, [value?.symbol, onChange]);

  useEffect(() => {
    const trimmed = query.trim();
    const timer = setTimeout(() => {
      if (trimmed.length < 2) return;
      setSearching(true);
      searchAssets(trimmed)
        .then((envelope) => {
          setResults(envelope.data);
          setError(null);
        })
        .catch((err) => {
          setResults(null);
          setError(
            err instanceof ApiRequestError ? err.message : "Asset search failed.",
          );
        })
        .finally(() => {
          setSearching(false);
        });
    }, 250);
    return () => clearTimeout(timer);
  }, [query]);

  if (results === null && !searching && !error && query.trim().length === 0) {
    return (
      <label className="flex flex-col gap-1 text-[11px] text-ink2">
        Asset
        <input
          disabled={disabled}
          value={query}
          onChange={handleChange}
          placeholder="Cari simbol atau nama aset (mis. BTCUSDT)"
          className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink font-mono w-[300px] focus-visible:outline focus-visible:outline-accent"
        />
      </label>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="flex flex-col gap-1 text-[11px] text-ink2">
        Asset
        <input
          disabled={disabled}
          value={query}
          onChange={handleChange}
          placeholder="Cari simbol atau nama aset (mis. BTCUSDT)"
          className="bg-recessed border border-line rounded px-2 py-1.5 text-[12px] text-ink font-mono w-[300px] focus-visible:outline focus-visible:outline-accent"
        />
      </label>

      {error && (
        <p role="alert" className="text-[12px] text-loss">{error}</p>
      )}

      {(searching || (results !== null && results.length > 0)) && (
        <div className="border border-line rounded-lg bg-card max-h-[220px] overflow-y-auto z-10">
          {searching && (
            <div className="px-2 py-2 text-[12px] text-ink3">Mencari aset…</div>
          )}
          {results !== null && results.length === 0 && !searching && (
            <div className="px-2 py-2 text-[12px] text-ink3">
              Tidak ada aset yang cocok dengan “{query}”.
            </div>
          )}
          {results !== null &&
            results.map((asset) => (
              <button
                key={asset.id}
                type="button"
                disabled={disabled}
                onClick={() => {
                  onChange(asset);
                }}
                className="flex items-center justify-between gap-2 px-2 py-1.5 hover:bg-hover text-left"
              >
                <div className="min-w-0">
                  <span className="font-mono font-semibold text-[12px]">
                    {asset.symbol}
                  </span>
                  <p className="text-[11px] text-ink3 truncate">
                    {asset.name}
                  </p>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-ink2 shrink-0">
                  {asset.market ? <span>{asset.market}</span> : null}
                  {asset.exchange && asset.exchange !== asset.market ? (
                    <span>{asset.exchange}</span>
                  ) : null}
                  {asset.quote_currency ? (
                    <span className="font-mono">{asset.quote_currency}</span>
                  ) : null}
                </div>
              </button>
            ))}
        </div>
      )}

      {value !== null && (
        <div className="flex items-center gap-2 px-2 py-1 rounded bg-hover border border-line">
          <span className="font-mono text-[12px] font-semibold">{value.symbol}</span>
          <span className="text-[12px] text-ink2">{value.name}</span>
          {value.market && <span className="text-[11px] text-ink3">{value.market}</span>}
          {value.quote_currency && (
            <span className="text-[11px] text-ink3 font-mono">{value.quote_currency}</span>
          )}
          <button
            type="button"
            disabled={disabled}
            onClick={() => onChange(null)}
            className="text-[11px] text-ink2 underline underline-offset-2 hover:text-ink"
          >
            Hapus
          </button>
        </div>
      )}
    </div>
  );
}
