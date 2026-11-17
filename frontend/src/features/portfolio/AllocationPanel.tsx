"use client";

import { useCallback, useEffect, useState } from "react";

import { Badge } from "@/components/Badge";
import { formatMoneyString, formatUtc } from "@/lib/format";
import { ApiRequestError, getAllocation } from "@/services/api";
import type {
  AllocationConcentration,
  AllocationCoverage,
  AllocationIndividualAsset,
  AllocationSlice,
  PortfolioAllocation,
  UnpricedPosition,
} from "@/types/api";

/**
 * Allocation panel (Stage J). Pure presentation over the backend allocation
 * endpoint. Weights/money/percentages are rendered verbatim as strings; the
 * client never does arithmetic, never renormalises weights, and never
 * computes a market value or HHI that the API did not provide.
 */
export default function AllocationPanel({ portfolioId }: { portfolioId: string }) {
  const [allocation, setAllocation] = useState<PortfolioAllocation | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getAllocation(portfolioId)
      .then((response) => {
        if (cancelled) return;
        setAllocation(response.data);
        setLoadError(null);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setAllocation(null);
        setLoadError(
          error instanceof ApiRequestError ? error.message : "Could not load allocation.",
        );
      });
    return () => {
      cancelled = true;
    };
  }, [portfolioId, reloadKey]);

  const retry = useCallback(() => setReloadKey((k) => k + 1), []);

  if (loadError !== null) {
    return (
      <section aria-label="Alokasi" className="bg-card border border-line rounded-lg">
        <header className="px-4 py-3 border-b border-line">
          <h2 className="text-[15px] font-semibold">Alokasi</h2>
        </header>
        <div role="alert" className="px-4 py-3 text-[12px] text-loss">
          {loadError.split(".")[0] === "Cannot reach the PIMS backend."
            ? "Backend is not reachable. Open portfolios once the backend is running on port 8000."
            : loadError}
          <button type="button" onClick={retry} className="ml-2 underline underline-offset-2">
            Retry
          </button>
        </div>
      </section>
    );
  }

  if (allocation === null) {
    return (
      <section aria-label="Alokasi" className="bg-card border border-line rounded-lg">
        <header className="px-4 py-3 border-b border-line">
          <h2 className="text-[15px] font-semibold">Alokasi</h2>
        </header>
        <p aria-live="polite" className="px-4 py-8 text-center text-[12px] text-ink3">
          Loading allocation…
        </p>
      </section>
    );
  }

  return (
    <section aria-label="Alokasi" className="bg-card border border-line rounded-lg">
      <header className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 border-b border-line">
        <div>
          <h2 className="text-[15px] font-semibold">Alokasi</h2>
          <p className="text-[11px] text-ink3">
            {allocation.weight_base} — bobot dihitung atas dasar komponen berharga + cash;
            posisi tanpa harga tidak dinormalkan agar terlihat 100%.
          </p>
        </div>
        <Badge label={allocation.data_status} />
      </header>

      {allocation.data_status === "UNAVAILABLE" && (
        <div role="status" className="px-4 py-3 border-b border-line text-[11px] text-ink2">
          {allocation.data_status_reason ?? "Tidak ada data alokasi tersedia untuk portfolio ini."}
        </div>
      )}

      <CoverageSummary coverage={allocation.coverage} />

      <div className="px-4 pb-2 flex flex-wrap items-start gap-4 border-t border-line pt-3">
        <SliceTable title="Asset class" slices={allocation.categories.asset_class} />
        <SliceTable title="Market" slices={allocation.categories.market} />
        <SliceTable title="Currency" slices={allocation.categories.currency} />
      </div>

      <IndividualAssetTable assets={allocation.categories.individual_asset} />
      <CashCard cash={allocation.categories.cash} />
      <UnpricedPositionsTable positions={allocation.unpriced_positions} />
      <ConcentrationPanel concentration={allocation.concentration} />

      {allocation.data_status === "PARTIAL" && allocation.data_status_reason && (
        <p className="px-4 py-2 text-[10px] text-ink2 border-t border-line">
          {allocation.data_status_reason}
        </p>
      )}
      <p className="px-4 pb-3 text-[10px] text-ink3 border-t border-line">
        Nilai diukur pada {formatUtc(allocation.valuation_timestamp)}.
        Angka berasal dari backend; UI tidak menghitung ulang bobot atau nilai.
      </p>
    </section>
  );
}

function CoverageSummary({ coverage }: { coverage: AllocationCoverage }) {
  return (
    <div className="px-4 py-2 border-b border-line">
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px]">
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Posisi berharga</dt>
          <dd className="text-ink tabular-nums">
            {coverage.covered_components} / {coverage.total_components}
          </dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Posisi tanpa harga</dt>
          <dd className="text-ink tabular-nums">{coverage.unvalued_components}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Cakupan posisi (jumlah)</dt>
          <dd className="text-ink tabular-nums">
            {coverage.position_coverage_percentage !== null
              ? `${formatMoneyString(coverage.position_coverage_percentage)}%`
              : "—"}
          </dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Cakupan nilai (diketahui)</dt>
          <dd className="text-ink tabular-nums">
            {coverage.value_known_percentage !== null
              ? `${formatMoneyString(coverage.value_known_percentage)}%`
              : "—"}
          </dd>
        </div>
      </dl>
      <p className="pt-2 text-[10px] text-ink2">
        Cost basis dipakai sebagai proksi nilai untuk posisi tanpa harga — bukan nilai pasar.
      </p>
    </div>
  );
}

function SliceTable({ title, slices }: { title: string; slices: AllocationSlice[] }) {
  if (slices.length === 0) return null;
  return (
    <section className="bg-recessed border border-line rounded-lg">
      <header className="px-3 py-2 border-b border-line flex items-center justify-between">
        <h3 className="text-[12px] font-semibold">{title}</h3>
        <span className="text-[10px] text-ink3">{slices.length} slice</span>
      </header>
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-left text-[10px] text-ink3 border-b border-line">
            <th className="px-3 py-2 font-medium">Kategori</th>
            <th className="px-3 py-2 font-medium text-right">Nilai</th>
            <th className="px-3 py-2 font-medium text-right">Bobot</th>
            <th className="px-3 py-2 font-medium text-right">Posisi</th>
          </tr>
        </thead>
        <tbody>
          {slices.map((s) => (
            <tr key={s.name} className="border-b border-line last:border-b-0">
              <td className="px-3 py-2 font-mono font-semibold">{s.name}</td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">
                {s.market_value === null ? "not available" : formatMoneyString(s.market_value)}
              </td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">
                {s.weight === null ? "not available" : `${formatMoneyString(s.weight)}%`}
              </td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">{s.holdings_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function IndividualAssetTable({ assets }: { assets: AllocationIndividualAsset[] }) {
  if (assets.length === 0) return null;
  return (
    <section className="bg-recessed border border-line rounded-lg">
      <header className="px-3 py-2 border-b border-line flex items-center justify-between">
        <h3 className="text-[12px] font-semibold">Individual asset</h3>
        <span className="text-[10px] text-ink3">{assets.length} aset</span>
      </header>
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-left text-[10px] text-ink3 border-b border-line">
            <th className="px-3 py-2 font-medium">Simbol</th>
            <th className="px-3 py-2 font-medium text-right">Kelas</th>
            <th className="px-3 py-2 font-medium text-right">Market</th>
            <th className="px-3 py-2 font-medium text-right">Currency</th>
            <th className="px-3 py-2 font-medium text-right">Kuantitas</th>
            <th className="px-3 py-2 font-medium text-right">Nilai</th>
            <th className="px-3 py-2 font-medium text-right">Bobot</th>
            <th className="px-3 py-2 font-medium">Harga</th>
          </tr>
        </thead>
        <tbody>
          {assets.map((a) => (
            <tr key={a.asset_id} className="border-b border-line last:border-b-0">
              <td className="px-3 py-2 font-mono font-semibold">{a.symbol}</td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">{a.asset_class}</td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">{a.market}</td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">{a.currency}</td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">
                {a.quantity === null ? "not available" : formatMoneyString(a.quantity)}
              </td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">
                {a.market_value === null ? "not available" : formatMoneyString(a.market_value)}
              </td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">
                {a.weight === null ? "not available" : `${formatMoneyString(a.weight)}%`}
              </td>
              <td className="px-3 py-2">
                <Badge label={a.price_status} mono />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function CashCard({ cash }: { cash: { currency: string; value: string | null; weight: string | null } }) {
  if (!cash) return null;
  return (
    <section className="bg-recessed border border-line rounded-lg px-3 py-2">
      <header className="flex items-center justify-between border-b border-line pb-2">
        <h3 className="text-[12px] font-semibold">Cash</h3>
        <span className="text-[10px] text-ink3">{cash.currency}</span>
      </header>
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px] pt-2">
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Nilai</dt>
          <dd className="text-ink tabular-nums">
            {cash.value === null ? "not available" : formatMoneyString(cash.value)}
          </dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Bobot</dt>
          <dd className="text-ink tabular-nums">
            {cash.weight === null ? "not available" : `${formatMoneyString(cash.weight)}%`}
          </dd>
        </div>
      </dl>
    </section>
  );
}

function UnpricedPositionsTable({ positions }: { positions: UnpricedPosition[] }) {
  if (positions.length === 0) return null;
  return (
    <section className="bg-recessed border border-line rounded-lg">
      <header className="px-3 py-2 border-b border-line flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <h3 className="text-[12px] font-semibold">Posisi tanpa harga</h3>
          <p className="text-[10px] text-warn">
            Cost basis dipakai sebagai proksi; ini bukan nilai pasar dan tidak dihitung ulang di klien.
          </p>
        </div>
        <span className="text-[10px] text-ink3">{positions.length} posisi</span>
      </header>
      <table className="w-full text-[12px]">
        <thead>
          <tr className="text-left text-[10px] text-ink3 border-b border-line">
            <th className="px-3 py-2 font-medium">Simbol</th>
            <th className="px-3 py-2 font-medium text-right">Kuantitas</th>
            <th className="px-3 py-2 font-medium text-right">Cost basis</th>
          </tr>
        </thead>
        <tbody>
          {positions.map((p) => (
            <tr key={p.asset_id} className="border-b border-line last:border-b-0">
              <td className="px-3 py-2 font-mono font-semibold">{p.symbol}</td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">
                {p.quantity === null ? "not available" : formatMoneyString(p.quantity)}
              </td>
              <td className="px-3 py-2 text-right font-mono tabular-nums">
                {p.cost_basis === null ? "not available" : formatMoneyString(p.cost_basis)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ConcentrationPanel({ concentration }: { concentration: AllocationConcentration }) {
  return (
    <section className="bg-recessed border border-line rounded-lg">
      <header className="px-3 py-2 border-b border-line">
        <h3 className="text-[12px] font-semibold">Konsentrasi (top-N)</h3>
        <p className="text-[10px] text-ink3">
          HHI tidak tersedia di spesifikasi allocation dan tidak dihitung di klien.
        </p>
      </header>
      <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px] px-3 py-2">
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Top holding</dt>
          <dd className="text-ink font-mono tabular-nums">
            {concentration.largest_holding_symbol ?? "—"}
          </dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Bobot top holding</dt>
          <dd className="text-ink tabular-nums">
            {concentration.largest_holding_weight !== null
              ? `${formatMoneyString(concentration.largest_holding_weight)}%`
              : "—"}
          </dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Top 3</dt>
          <dd className="text-ink tabular-nums">
            {concentration.top_3_weight !== null
              ? `${formatMoneyString(concentration.top_3_weight)}%`
              : "—"}
          </dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Top 5</dt>
          <dd className="text-ink tabular-nums">
            {concentration.top_5_weight !== null
              ? `${formatMoneyString(concentration.top_5_weight)}%`
              : "—"}
          </dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Top 10</dt>
          <dd className="text-ink tabular-nums">
            {concentration.top_10_weight !== null
              ? `${formatMoneyString(concentration.top_10_weight)}%`
              : "—"}
          </dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Largest market</dt>
          <dd className="text-ink font-mono tabular-nums">{concentration.largest_market ?? "—"}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Largest currency</dt>
          <dd className="text-ink font-mono tabular-nums">{concentration.largest_currency ?? "—"}</dd>
        </div>
        <div className="flex flex-col gap-1">
          <dt className="text-ink3">Largest sector</dt>
          <dd className="text-ink font-mono tabular-nums">{concentration.largest_sector ?? "—"}</dd>
        </div>
      </dl>
      {concentration.largest_sector_reason && (
        <p className="px-3 pb-2 text-[10px] text-ink2">
          {concentration.largest_sector_reason}
        </p>
      )}
    </section>
  );
}
