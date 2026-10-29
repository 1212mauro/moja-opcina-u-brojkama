/**
 * Internal routes, spelled once. next/link adds the base path itself; raw <a>
 * elements (inside SVG) need it added. On GitHub Pages the site lives under
 * /<repository>/, which the deploy sets as NEXT_PUBLIC_BASE_PATH.
 */
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

/** The page of one municipality, for next/link (which adds the base path itself). */
export function municipalityPath(slug: string): string {
  return `/opcina/${slug}/`;
}

/** The same page for a raw <a> (inside SVG), with the base path. */
export function municipalityHref(slug: string): string {
  return `${BASE_PATH}${municipalityPath(slug)}`;
}
