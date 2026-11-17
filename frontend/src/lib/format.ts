"Display formatting. All values come from the backend; nothing is computed or invented here.";

const numberFormat = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactFormat = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatPrice(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return numberFormat.format(value);
}

export function formatPct(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${numberFormat.format(value)}%`;
}

export function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return numberFormat.format(value);
}

export function formatCompact(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return compactFormat.format(value);
}

/** Deterministic UTC formatting: avoids server/client hydration drift. */
export function formatUtc(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}
