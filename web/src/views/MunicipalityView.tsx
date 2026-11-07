import type { Metadata } from "next";
import Link from "next/link";

import { CountyMap } from "@/components/CountyMap";
import { BudgetSection } from "@/components/sections/BudgetSection";
import { FacilitiesSection } from "@/components/sections/FacilitiesSection";
import { PaymentsSection } from "@/components/sections/PaymentsSection";
import { PeersSection } from "@/components/sections/PeersSection";
import { ProcurementSection } from "@/components/sections/ProcurementSection";
import { SourcesTable } from "@/components/sections/SourcesSection";
import { loadPage, pageSlugs } from "@/lib/data";
import { compareWithPeers } from "@/lib/peers";
import { getFormat, type Format } from "@/lib/format";
import type { Locale } from "@/lib/i18n";
import { routePath } from "@/lib/paths";
import { getMessages } from "@/messages";
import styles from "./Municipality.module.css";

/** Every municipality page is generated at build time, in every edition. */
export function municipalityParams() {
  return pageSlugs().map((slug) => ({ slug }));
}

export function municipalityMetadata(locale: Locale, slug: string): Metadata {
  const msg = getMessages(locale);
  const page = loadPage(slug);
  return {
    title: `${msg.unitType[page.type]} ${page.name}`,
    description: msg.site.tagline,
  };
}

// Section anchors stay the same in every edition, so shared links keep working.
const SECTIONS = [
  { id: "proracun", key: "budget", Component: BudgetSection },
  { id: "usporedba", key: "peers", Component: PeersSection },
  { id: "javna-nabava", key: "procurement", Component: ProcurementSection },
  { id: "isplate", key: "payments", Component: PaymentsSection },
  { id: "ustanove", key: "facilities", Component: FacilitiesSection },
] as const;

export function MunicipalityView({
  locale,
  slug,
}: {
  locale: Locale;
  slug: string;
}) {
  const msg = getMessages(locale);
  const fmt = getFormat(locale);
  const page = loadPage(slug);
  const { budget, procurement } = page;

  return (
    <article>
      <nav aria-label={msg.page.breadcrumb} className={styles.breadcrumb}>
        <ol>
          <li>
            <Link href={routePath(locale, { page: "home" })}>
              {msg.site.nav.home}
            </Link>
          </li>
          <li>{msg.page.county(page.county)}</li>
          <li aria-current="page">{page.name}</li>
        </ol>
      </nav>

      {/* H2: one header card: who this is, the key figures, where it lies. */}
      <div className={styles.headerCard}>
        <header className={styles.header}>
          <h1>
            <span className={styles.kind}>{msg.unitType[page.type]}</span>{" "}
            {page.name}
          </h1>
          <p className={styles.meta}>
            {msg.page.county(page.county)} ·{" "}
            {msg.page.population(
              fmt.integer(page.population.total),
              page.population.year,
              page.population.kind === "estimate",
            )}
          </p>
        </header>

        <section aria-label={msg.page.keyFigures} className={styles.tiles}>
          {budget ? (
            <>
              <div className={styles.tile}>
                <p className={styles.tileLabel}>
                  {msg.page.revenue(budget.year)}
                </p>
                <p className={styles.tileValue}>
                  {fmt.eurShort(budget.revenueTotalEur)}
                </p>
                <p className={styles.tileDetail}>
                  {msg.page.perResident(
                    fmt.eurCents(budget.revenuePerResidentEur),
                  )}
                </p>
                <VsPeers
                  comparison={compareWithPeers(page, "revenuePerResidentEur")}
                  fmt={fmt}
                  vsPeers={msg.page.vsPeers}
                />
              </div>
              <div className={styles.tile}>
                <p className={styles.tileLabel}>
                  {msg.page.expenditure(budget.year)}
                </p>
                <p className={styles.tileValue}>
                  {fmt.eurShort(budget.expenditureTotalEur)}
                </p>
                <p className={styles.tileDetail}>
                  {msg.page.perResident(
                    fmt.eurCents(budget.expenditurePerResidentEur),
                  )}
                </p>
                <VsPeers
                  comparison={compareWithPeers(
                    page,
                    "expenditurePerResidentEur",
                  )}
                  fmt={fmt}
                  vsPeers={msg.page.vsPeers}
                />
              </div>
            </>
          ) : null}
          {procurement ? (
            <div className={styles.tile}>
              <p className={styles.tileLabel}>{msg.page.contracts}</p>
              <p className={styles.tileValue}>
                {fmt.integer(procurement.contractCount)}
              </p>
              {procurement.dataFrom ? (
                <p className={styles.tileDetail}>
                  {msg.page.contractsSince(fmt.date(procurement.dataFrom))}
                </p>
              ) : null}
            </div>
          ) : null}
        </section>

        <div className={styles.locator}>
          <CountyMap
            locale={locale}
            highlight={page.slug}
            title={msg.map.locator(page.name)}
            width={400}
          />
        </div>
      </div>

      {/* H3: a sticky section menu beside the content on desktop, chips on phones. */}
      <div className={styles.body}>
        <nav aria-labelledby="sadrzaj-stranice" className={styles.toc}>
          <h2 id="sadrzaj-stranice" className={styles.tocTitle}>
            {msg.page.contents}
          </h2>
          <ul>
            {SECTIONS.map((section) => (
              <li key={section.id}>
                <a href={`#${section.id}`}>{msg.sections[section.key]}</a>
              </li>
            ))}
            <li>
              <a href="#izvori">{msg.sections.sources}</a>
            </li>
          </ul>
        </nav>

        <div className={styles.content}>
          {SECTIONS.map(({ id, key, Component }) => (
            <section
              key={id}
              id={id}
              aria-labelledby={`${id}-naslov`}
              className={styles.section}
            >
              <h2 id={`${id}-naslov`}>{msg.sections[key]}</h2>
              <Component locale={locale} page={page} />
            </section>
          ))}

          <section
            id="izvori"
            aria-labelledby="izvori-naslov"
            className={styles.section}
          >
            <h2 id="izvori-naslov">{msg.sections.sources}</h2>
            <p>{msg.sources.intro}</p>
            <SourcesTable locale={locale} runs={page.sources} />
          </section>
        </div>
      </div>
    </article>
  );
}

/**
 * H5: the tile's figure in context, linked to the comparison section. Plain text, no
 * colour: spending more or less than similar units is neither good nor bad in itself.
 */
function VsPeers({
  comparison,
  fmt,
  vsPeers,
}: {
  comparison: ReturnType<typeof compareWithPeers>;
  fmt: Format;
  vsPeers: ReturnType<typeof getMessages>["page"]["vsPeers"];
}) {
  if (!comparison) return null;
  const { diff, only } = comparison;
  const share = fmt.share(Math.abs(diff));
  // Anything that rounds to 0 % reads as "about the same".
  const direction =
    Math.round(Math.abs(diff) * 100) === 0
      ? "same"
      : diff > 0
        ? "more"
        : "less";
  return (
    <p className={styles.tileCompare}>
      <a href="#usporedba">{vsPeers(direction, share, only)}</a>
    </p>
  );
}
