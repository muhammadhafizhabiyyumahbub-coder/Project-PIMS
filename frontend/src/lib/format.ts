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

/**
 * Return fraction string ("0.25") → percent string ("25%").
 * The backend sends returns as decimal fractions (technical-decisions §7.10).
 * This is pure string surgery: the decimal point is shifted two places right,
 * so the value is never parsed as a Number and no float rounding is introduced.
 * null/undefined → "—" (callers show the paired reason instead).
 */
export function formatReturnPct(value: string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const negative = value.startsWith("-");
  const magnitude = value.startsWith("-") || value.startsWith("+") ? value.slice(1) : value;
  const dot = magnitude.indexOf(".");
  const digits = magnitude.replace(".", "");
  const cut = (dot === -1 ? digits.length : dot) + 2;
  const padded = digits.length < cut ? digits.padEnd(cut, "0") : digits;
  const intPart = padded.slice(0, cut).replace(/^0+(?=\d)/, "");
  const fracPart = padded.slice(cut).replace(/0+$/, "");
  const body = fracPart === "" ? groupDigits(intPart) : `${groupDigits(intPart)}.${fracPart}`;
  return `${negative ? "-" : ""}${body}%`;
}

/** P&L text tone class; reads only the sign character, no numeric parsing. */
export function pnlTone(value: string | null | undefined): string {
  if (value === null || value === undefined) return "text-ink3";
  if (value.startsWith("-")) return "text-loss";
  return "text-gain";
}
