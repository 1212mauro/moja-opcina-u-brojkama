/** Croatian number, money and date formatting ("1.234.567 €", "12. 3. 2026."). */

const LOCALE = "hr-HR";

const euro = new Intl.NumberFormat(LOCALE, {
  style: "currency",
  currency: "EUR",
  maximumFractionDigits: 0,
});
const euroCents = new Intl.NumberFormat(LOCALE, {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const integer = new Intl.NumberFormat(LOCALE, { maximumFractionDigits: 0 });
const oneDecimal = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

/** Whole euros: "79.710.828 €". */
export function formatEur(value: number): string {
  return euro.format(value);
}

/** Euros with cents, for per-resident figures: "1.800,03 €". */
export function formatEurCents(value: number): string {
  return euroCents.format(value);
}

/** Short form for headlines: "79,7 mil. €", "995 tis. €", "640 €". */
export function formatEurShort(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${oneDecimal.format(value / 1_000_000)} mil. €`;
  if (abs >= 10_000) return `${integer.format(value / 1_000)} tis. €`;
  return euro.format(value);
}

export function formatInteger(value: number): string {
  return integer.format(value);
}

const percent = new Intl.NumberFormat(LOCALE, {
  style: "percent",
  maximumFractionDigits: 0,
});

/** A share of a whole: 0.342 -> "34 %". */
export function formatShare(fraction: number): string {
  return percent.format(fraction);
}

/** "2026-04-14" -> "14. 4. 2026." */
export function formatDate(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  return `${day}. ${month}. ${year}.`;
}

const MONTHS = [
  "siječanj",
  "veljača",
  "ožujak",
  "travanj",
  "svibanj",
  "lipanj",
  "srpanj",
  "kolovoz",
  "rujan",
  "listopad",
  "studeni",
  "prosinac",
];
const MONTHS_SHORT = [
  "sij",
  "velj",
  "ožu",
  "tra",
  "svi",
  "lip",
  "srp",
  "kol",
  "ruj",
  "lis",
  "stu",
  "pro",
];

/** "2026-04" -> "travanj 2026." */
export function formatMonth(month: string): string {
  const [year, m] = month.split("-").map(Number);
  return `${MONTHS[m - 1]} ${year}.`;
}

/** "2026-04" -> "tra" (axis labels). */
export function formatMonthShort(month: string): string {
  return MONTHS_SHORT[Number(month.split("-")[1]) - 1];
}

/** The 12 calendar months ending with ``last`` ("YYYY-MM"), oldest first. */
export function monthWindow(last: string, count = 12): string[] {
  const [year, month] = last.split("-").map(Number);
  const months: string[] = [];
  for (let i = count - 1; i >= 0; i--) {
    const index = year * 12 + (month - 1) - i;
    months.push(
      `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}`,
    );
  }
  return months;
}
