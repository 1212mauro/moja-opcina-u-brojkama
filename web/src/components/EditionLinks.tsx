"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { HTML_LANG, type Locale } from "@/lib/i18n";
import { parsePath, routePath } from "@/lib/paths";
import styles from "./EditionLinks.module.css";

/**
 * Links to the same page in the other editions (simple language, English).
 * A client component only to read the current path; the static export renders
 * it per page, so the links are right in the HTML without JavaScript.
 */
export function EditionLinks({
  locale,
  label,
  links,
}: {
  locale: Locale;
  label: string;
  links: Partial<Record<Locale, string>>;
}) {
  // Unknown paths (the 404 page) link to the other editions' home pages.
  const route = parsePath(usePathname())?.route ?? { page: "home" as const };
  return (
    <nav aria-label={label}>
      <ul className={styles.list}>
        {(Object.entries(links) as [Locale, string][]).map(([target, text]) => {
          const lang =
            HTML_LANG[target] === HTML_LANG[locale]
              ? undefined
              : HTML_LANG[target];
          return (
            <li key={target}>
              <Link
                href={routePath(target, route)}
                lang={lang}
                hrefLang={HTML_LANG[target]}
              >
                {text}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
