/**
 * Internal URLs for places where next/link cannot be used (links inside SVG).
 * next/link adds the base path itself; on GitHub Pages the site lives under
 * /<repository>/, which the deploy sets as NEXT_PUBLIC_BASE_PATH.
 */
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export function municipalityHref(slug: string): string {
  return `${BASE_PATH}/opcina/${slug}/`;
}
