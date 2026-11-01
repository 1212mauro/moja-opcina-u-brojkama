/**
 * The site's editions (E1, E2): Croatian, Croatian in simple language, and English.
 *
 * Each edition is a set of static pages under its own URL prefix (see paths.ts),
 * so every edition works without JavaScript and can be linked to directly.
 * Components receive the locale as a prop and look up their text and number
 * formats from it.
 */
export const LOCALES = ["hr", "hr-simple", "en"] as const;
export type Locale = (typeof LOCALES)[number];

/** The value of <html lang>: simple language is still Croatian. */
export const HTML_LANG: Record<Locale, string> = {
  hr: "hr",
  "hr-simple": "hr",
  en: "en",
};

/**
 * The lang attribute for text from the data (payment categories, contract
 * subjects, source titles), which is always Croatian: set only where the page
 * itself is in another language, so screen readers switch pronunciation.
 */
export function dataLang(locale: Locale): string | undefined {
  return HTML_LANG[locale] === "hr" ? undefined : "hr";
}
