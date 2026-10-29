import type { Metadata } from "next";
import Link from "next/link";

import { BudgetSection } from "@/components/sections/BudgetSection";
import { FacilitiesSection } from "@/components/sections/FacilitiesSection";
import { PaymentsSection } from "@/components/sections/PaymentsSection";
import { PeersSection } from "@/components/sections/PeersSection";
import { ProcurementSection } from "@/components/sections/ProcurementSection";
import { SourcesTable } from "@/components/sections/SourcesSection";
import { loadPage, pageSlugs } from "@/lib/data";
import {
  formatDate,
  formatEurCents,
  formatEurShort,
  formatInteger,
} from "@/lib/format";
import { hr } from "@/messages/hr";
import styles from "./page.module.css";

// Every municipality page is generated at build time; anything else is a 404.
export const dynamicParams = false;

export function generateStaticParams() {
  return pageSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: PageProps<"/opcina/[slug]">): Promise<Metadata> {
  const page = loadPage((await params).slug);
  return {
    title: `${hr.unitType[page.type]} ${page.name}`,
    description: hr.site.tagline,
  };
}

const SECTIONS = [
  { id: "proracun", title: hr.sections.budget, Component: BudgetSection },
  { id: "usporedba", title: hr.sections.peers, Component: PeersSection },
  {
    id: "javna-nabava",
    title: hr.sections.procurement,
    Component: ProcurementSection,
  },
  { id: "isplate", title: hr.sections.payments, Component: PaymentsSection },
  {
    id: "ustanove",
    title: hr.sections.facilities,
    Component: FacilitiesSection,
  },
] as const;

export default async function MunicipalityPage({
  params,
}: PageProps<"/opcina/[slug]">) {
  const page = loadPage((await params).slug);
  const { budget, procurement } = page;

  return (
    <article>
      <nav aria-label={hr.page.breadcrumb} className={styles.breadcrumb}>
        <ol>
          <li>
            <Link href="/">{hr.site.nav.home}</Link>
          </li>
          <li>{hr.page.county(page.county)}</li>
          <li aria-current="page">{page.name}</li>
        </ol>
      </nav>

      <header className={styles.header}>
        <h1>
          <span className={styles.kind}>{hr.unitType[page.type]}</span>{" "}
          {page.name}
        </h1>
        <p className={styles.meta}>
          {hr.page.county(page.county)} ·{" "}
          {hr.page.population(
            formatInteger(page.population.total),
            page.population.year,
            page.population.kind === "estimate",
          )}
        </p>
      </header>

      <section aria-label={hr.page.keyFigures} className={styles.tiles}>
        {budget ? (
          <>
            <div className={styles.tile}>
              <p className={styles.tileLabel}>{hr.page.revenue(budget.year)}</p>
              <p className={styles.tileValue}>
                {formatEurShort(budget.revenueTotalEur)}
              </p>
              <p className={styles.tileDetail}>
                {hr.page.perResident(
                  formatEurCents(budget.revenuePerResidentEur),
                )}
              </p>
            </div>
            <div className={styles.tile}>
              <p className={styles.tileLabel}>
                {hr.page.expenditure(budget.year)}
              </p>
              <p className={styles.tileValue}>
                {formatEurShort(budget.expenditureTotalEur)}
              </p>
              <p className={styles.tileDetail}>
                {hr.page.perResident(
                  formatEurCents(budget.expenditurePerResidentEur),
                )}
              </p>
            </div>
          </>
        ) : null}
        {procurement ? (
          <div className={styles.tile}>
            <p className={styles.tileLabel}>{hr.page.contracts}</p>
            <p className={styles.tileValue}>
              {formatInteger(procurement.contractCount)}
            </p>
            {procurement.dataFrom ? (
              <p className={styles.tileDetail}>
                {hr.page.contractsSince(formatDate(procurement.dataFrom))}
              </p>
            ) : null}
          </div>
        ) : null}
      </section>

      <nav aria-labelledby="sadrzaj-stranice" className={styles.toc}>
        <h2 id="sadrzaj-stranice" className={styles.tocTitle}>
          {hr.page.contents}
        </h2>
        <ul>
          {SECTIONS.map((section) => (
            <li key={section.id}>
              <a href={`#${section.id}`}>{section.title}</a>
            </li>
          ))}
          <li>
            <a href="#izvori">{hr.sections.sources}</a>
          </li>
        </ul>
      </nav>

      {SECTIONS.map(({ id, title, Component }) => (
        <section
          key={id}
          id={id}
          aria-labelledby={`${id}-naslov`}
          className={styles.section}
        >
          <h2 id={`${id}-naslov`}>{title}</h2>
          <Component page={page} />
        </section>
      ))}

      <section
        id="izvori"
        aria-labelledby="izvori-naslov"
        className={styles.section}
      >
        <h2 id="izvori-naslov">{hr.sections.sources}</h2>
        <p>{hr.sources.intro}</p>
        <SourcesTable runs={page.sources} />
      </section>
    </article>
  );
}
