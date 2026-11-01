/**
 * Number, money and date formatting per locale: Croatian ("1.234.567 €",
 * "12. 3. 2026.") and English ("€1,234,567", "12 March 2026").
 */
import type { Locale } from "@/lib/i18n";

export type Format = {
  /** Whole euros: "79.710.828 €" / "€79,710,828". */
  eur: (value: number) => string;
  /** Euros with cents, for per-resident figures: "1.800,03 €" / "€1,800.03". */
  eurCents: (value: number) => string;
  /** Short form for headlines: "79,7 mil. €" / "€79.7 million". */
  eurShort: (value: number) => string;
  integer: (value: number) => string;
  /** A share of a whole: 0.342 -> "34 %" / "34%". */
  share: (fraction: number) => string;
  /** "2026-04-14" -> "14. 4. 2026." / "14 April 2026". */
  date: (iso: string) => string;
  /** "2026-04" -> "travanj 2026." / "April 2026". */
  month: (month: string) => string;
  /** "2026-04" -> "tra" / "Apr" (axis labels). */
  monthShort: (month: string) => string;
};

const HR_MONTHS = [
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
const HR_MONTHS_SHORT = [
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
const EN_MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

function parts(iso: string): [number, number, number] {
  const [year, month, day] = iso.slice(0, 10).split("-").map(Number);
  return [year, month, day ?? 1];
}

function numberFormats(intlLocale: string) {
  return {
    euro: new Intl.NumberFormat(intlLocale, {
      style: "currency",
      currency: "EUR",
      maximumFractionDigits: 0,
    }),
    euroCents: new Intl.NumberFormat(intlLocale, {
      style: "currency",
      currency: "EUR",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }),
    integer: new Intl.NumberFormat(intlLocale, { maximumFractionDigits: 0 }),
    oneDecimal: new Intl.NumberFormat(intlLocale, {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }),
    percent: new Intl.NumberFormat(intlLocale, {
      style: "percent",
      maximumFractionDigits: 0,
    }),
  };
}

const hrNumbers = numberFormats("hr-HR");
const hrFormat: Format = {
  eur: (v) => hrNumbers.euro.format(v),
  eurCents: (v) => hrNumbers.euroCents.format(v),
  eurShort: (v) => {
    const abs = Math.abs(v);
    if (abs >= 1_000_000)
      return `${hrNumbers.oneDecimal.format(v / 1_000_000)} mil. €`;
    if (abs >= 10_000) return `${hrNumbers.integer.format(v / 1_000)} tis. €`;
    return hrNumbers.euro.format(v);
  },
  integer: (v) => hrNumbers.integer.format(v),
  share: (f) => hrNumbers.percent.format(f),
  date: (iso) => {
    const [year, month, day] = parts(iso);
    return `${day}. ${month}. ${year}.`;
  },
  month: (m) => {
    const [year, month] = parts(m);
    return `${HR_MONTHS[month - 1]} ${year}.`;
  },
  monthShort: (m) => HR_MONTHS_SHORT[parts(m)[1] - 1],
};

// en-IE: euro amounts with the symbol in front ("€1,234"), as Irish and EU English do.
const enNumbers = numberFormats("en-IE");
const enFormat: Format = {
  eur: (v) => enNumbers.euro.format(v),
  eurCents: (v) => enNumbers.euroCents.format(v),
  eurShort: (v) => {
    const abs = Math.abs(v);
    if (abs >= 1_000_000)
      return `€${enNumbers.oneDecimal.format(v / 1_000_000)} million`;
    if (abs >= 10_000) return `€${enNumbers.integer.format(v / 1_000)}k`;
    return enNumbers.euro.format(v);
  },
  integer: (v) => enNumbers.integer.format(v),
  share: (f) => enNumbers.percent.format(f),
  date: (iso) => {
    const [year, month, day] = parts(iso);
    return `${day} ${EN_MONTHS[month - 1]} ${year}`;
  },
  month: (m) => {
    const [year, month] = parts(m);
    return `${EN_MONTHS[month - 1]} ${year}`;
  },
  monthShort: (m) => EN_MONTHS[parts(m)[1] - 1].slice(0, 3),
};

const FORMATS: Record<Locale, Format> = {
  hr: hrFormat,
  "hr-simple": hrFormat,
  en: enFormat,
};

export function getFormat(locale: Locale): Format {
  return FORMATS[locale];
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
