/**
 * Internal routes, spelled once. next/link adds the base path itself; raw <a>
 * elements (inside SVG) need it added. On GitHub Pages the site lives under
 * /<repository>/, which the deploy sets as NEXT_PUBLIC_BASE_PATH.
 *
 * Each edition has its own prefix; English also translates the path segments.
 */
import type { Locale } from "@/lib/i18n";

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

type Section = "methodology" | "sources" | "accessibility";
export type Route =
  { page: "home" } | { page: Section } | { page: "municipality"; slug: string };

const PREFIX: Record<Locale, string> = {
  hr: "",
  "hr-simple": "/jednostavno",
  en: "/en",
};

const HR_SEGMENTS = {
  methodology: "metodologija",
  sources: "izvori",
  accessibility: "pristupacnost",
  municipality: "opcina",
};
const SEGMENTS: Record<Locale, Record<Section | "municipality", string>> = {
  hr: HR_SEGMENTS,
  "hr-simple": HR_SEGMENTS,
  en: {
    methodology: "methodology",
    sources: "sources",
    accessibility: "accessibility",
    municipality: "municipality",
  },
};

/** A route's path for next/link (which adds the base path itself). */
export function routePath(locale: Locale, route: Route): string {
  const prefix = PREFIX[locale];
  const segments = SEGMENTS[locale];
  if (route.page === "home") return `${prefix}/`;
  if (route.page === "municipality")
    return `${prefix}/${segments.municipality}/${route.slug}/`;
  return `${prefix}/${segments[route.page]}/`;
}

export function municipalityPath(locale: Locale, slug: string): string {
  return routePath(locale, { page: "municipality", slug });
}

/** The same page for a raw <a> (inside SVG), with the base path. */
export function municipalityHref(locale: Locale, slug: string): string {
  return `${BASE_PATH}${municipalityPath(locale, slug)}`;
}

/**
 * Which edition and page a path (without the base path) shows, so the language
 * links can point at the same page in another edition. Null for unknown paths.
 */
export function parsePath(
  pathname: string,
): { locale: Locale; route: Route } | null {
  let parts = pathname.split("/").filter(Boolean);
  let locale: Locale = "hr";
  if (parts[0] === "en") locale = "en";
  else if (parts[0] === "jednostavno") locale = "hr-simple";
  if (locale !== "hr") parts = parts.slice(1);

  const segments = SEGMENTS[locale];
  if (parts.length === 0) return { locale, route: { page: "home" } };
  if (parts.length === 2 && parts[0] === segments.municipality)
    return { locale, route: { page: "municipality", slug: parts[1] } };
  if (parts.length === 1) {
    const section = (Object.keys(segments) as (keyof typeof segments)[]).find(
      (key) => key !== "municipality" && segments[key] === parts[0],
    );
    if (section && section !== "municipality")
      return { locale, route: { page: section } };
  }
  return null;
}
