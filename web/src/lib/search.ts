import type { SearchEntry } from "@/lib/contract";

// Combining diacritical marks (U+0300-U+036F), left over after NFKD decomposition.
const COMBINING_MARKS = new RegExp("[\\u0300-\\u036f]", "g");

/** Lower case without diacritics, like the pipeline's ascii_fold: "Đurđevac" -> "durdevac". */
export function fold(text: string): string {
  return text
    .replace(/đ/g, "d")
    .replace(/Đ/g, "D")
    .normalize("NFKD")
    .replace(COMBINING_MARKS, "")
    .toLowerCase()
    .trim();
}

/** Entries whose name contains the query, or one of whose postcodes starts with it. */
export function filterEntries(
  entries: SearchEntry[],
  query: string,
): SearchEntry[] {
  const q = fold(query);
  if (!q) return entries;
  if (/^\d+$/.test(q))
    return entries.filter((e) => e.postcodes.some((p) => p.startsWith(q)));
  return entries.filter(
    (e) => e.nameAscii.includes(q) || fold(e.name).includes(q),
  );
}
