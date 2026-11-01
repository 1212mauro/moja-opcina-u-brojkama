import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

import { EditionLinks } from "@/components/EditionLinks";
import { HTML_LANG, type Locale } from "@/lib/i18n";
import { routePath } from "@/lib/paths";
import { CONTACT_EMAIL } from "@/lib/site";
import { getMessages } from "@/messages";
import styles from "./SiteLayout.module.css";

export function siteMetadata(locale: Locale): Metadata {
  const msg = getMessages(locale);
  return {
    title: { default: msg.site.name, template: `%s · ${msg.site.name}` },
    description: msg.site.tagline,
  };
}

/**
 * The document around every page of one edition: each edition is its own root
 * layout, so <html lang> is right for it.
 */
export function SiteLayout({
  locale,
  children,
}: {
  locale: Locale;
  children: ReactNode;
}) {
  const msg = getMessages(locale);
  return (
    <html lang={HTML_LANG[locale]}>
      <body>
        <a className={styles.skip} href="#sadrzaj">
          {msg.site.skipToContent}
        </a>
        <header className={styles.header}>
          <div className={styles.inner}>
            <Link
              href={routePath(locale, { page: "home" })}
              className={styles.brand}
            >
              {msg.site.name}
            </Link>
            <nav aria-label={msg.site.nav.label}>
              <ul className={styles.nav}>
                <li>
                  <Link href={routePath(locale, { page: "home" })}>
                    {msg.site.nav.home}
                  </Link>
                </li>
                <li>
                  <Link href={routePath(locale, { page: "methodology" })}>
                    {msg.site.nav.methodology}
                  </Link>
                </li>
                <li>
                  <Link href={routePath(locale, { page: "sources" })}>
                    {msg.site.nav.sources}
                  </Link>
                </li>
              </ul>
            </nav>
            <EditionLinks
              locale={locale}
              label={msg.site.editions.label}
              links={msg.site.editions.links}
            />
          </div>
        </header>
        <main id="sadrzaj" className={styles.main} tabIndex={-1}>
          {children}
        </main>
        <footer className={styles.footer}>
          <div className={styles.inner}>
            <p>{msg.site.footer.about}</p>
            <p className={styles.small}>{msg.site.footer.licence}</p>
            {CONTACT_EMAIL ? (
              <p className={styles.small}>
                <Link href={routePath(locale, { page: "accessibility" })}>
                  {msg.site.nav.accessibility}
                </Link>
              </p>
            ) : null}
          </div>
        </footer>
      </body>
    </html>
  );
}
