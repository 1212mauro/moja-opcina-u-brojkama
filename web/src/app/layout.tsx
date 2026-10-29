import type { Metadata } from "next";
import Link from "next/link";

import { hr } from "@/messages/hr";
import "./globals.css";
import styles from "./layout.module.css";

export const metadata: Metadata = {
  title: { default: hr.site.name, template: `%s · ${hr.site.name}` },
  description: hr.site.tagline,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="hr">
      <body>
        <a className={styles.skip} href="#sadrzaj">
          {hr.site.skipToContent}
        </a>
        <header className={styles.header}>
          <div className={styles.inner}>
            <Link href="/" className={styles.brand}>
              {hr.site.name}
            </Link>
            <nav aria-label="Glavna navigacija">
              <ul className={styles.nav}>
                <li>
                  <Link href="/">{hr.site.nav.home}</Link>
                </li>
                <li>
                  <Link href="/metodologija/">{hr.site.nav.methodology}</Link>
                </li>
                <li>
                  <Link href="/izvori/">{hr.site.nav.sources}</Link>
                </li>
              </ul>
            </nav>
          </div>
        </header>
        <main id="sadrzaj" className={styles.main} tabIndex={-1}>
          {children}
        </main>
        <footer className={styles.footer}>
          <div className={styles.inner}>
            <p>{hr.site.footer.about}</p>
            <p className={styles.small}>{hr.site.footer.licence}</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
