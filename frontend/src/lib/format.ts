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

// --- Portfolio money formatting (decimal strings, api-spec §5.3) -------------
// Backend sends money as decimal strings. These helpers format the string
// directly: no Number conversion, no toFixed — precision is never lost.

/** Group the integer part with commas; fraction digits stay exactly as sent. */
function groupDigits(digits: string): string {
  return digits.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * Format a decimal money string for display without precision loss.
 * null/undefined → "—" (callers should show the reason next to it).
 * "-8" → "-8.00" style is NOT applied: fraction digits come from the source
 * string verbatim (e.g. "50.061728394506" stays fully precise).
 */
export function formatMoneyString(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const sign = value.startsWith("-") ? "-" : "";
  const digits = value.startsWith("-") || value.startsWith("+") ? value.slice(1) : value;
  const [intPart, fracPart] = digits.split(".");
  const int = intPart === "" ? "0" : groupDigits(intPart);
  return `${sign}${int}${fracPart !== undefined ? `.${fracPart}` : ""}`;
}

/** Signed P&L display from a decimal string: only the sign character is read. */
export function formatSignedMoneyString(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  if (value.startsWith("-")) return `-${formatMoneyString(value.slice(1))}`;
  return `+${formatMoneyString(value)}`;
}

/** P&L text tone class; reads only the sign character, no numeric parsing. */
export function pnlTone(value: string | null | undefined): string {
  if (value === null || value === undefined) return "text-ink3";
  if (value.startsWith("-")) return "text-loss";
  return "text-gain";
}
