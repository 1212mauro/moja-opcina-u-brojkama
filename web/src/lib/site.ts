/** Facts about the project itself, shown on several pages. */

/**
 * Where readers report errors and accessibility problems. The accessibility
 * statement (E7) is published only once this is set: then rename the route
 * folders `_pristupacnost` / `_accessibility` (Next skips folders starting with
 * "_") and the footer links to the statement.
 */
export const CONTACT_EMAIL: string | null = null;

export function contactEmail(): string {
  if (!CONTACT_EMAIL)
    throw new Error("CONTACT_EMAIL is not set (src/lib/site.ts)");
  return CONTACT_EMAIL;
}

/** When the accessibility statement was prepared and last reviewed (E7), "YYYY-MM-DD". */
export const ACCESSIBILITY_STATEMENT_DATE = "2026-11-01";

/** The public address of the site, named in the accessibility statement. */
export const SITE_URL = "https://1212mauro.github.io/moja-opcina-u-brojkama/";
