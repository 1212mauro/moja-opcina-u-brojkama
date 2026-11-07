import type { Metadata } from "next";

import { loadSourceStatus } from "@/lib/data";
import { getFormat } from "@/lib/format";
import { dataLang, type Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";
import styles from "./prose.module.css";

export function sourcesMetadata(locale: Locale): Metadata {
  return { title: getMessages(locale).site.nav.sources };
}

/** F3: every source and when it was last fetched. */
export function SourcesView({ locale }: { locale: Locale }) {
  const msg = getMessages(locale);
  const fmt = getFormat(locale);
  const { runs, generatedAt } = loadSourceStatus();
  const t = msg.sources.columns;
  return (
    <article className={styles.prose}>
      <h1>{msg.site.nav.sources}</h1>
      <p className={styles.lead}>{msg.sources.intro}</p>
      <p>{msg.sources.generated(fmt.date(generatedAt))}</p>
      <div
        className={`table-scroll ${styles.wide}`}
        role="region"
        aria-label={msg.site.nav.sources}
        tabIndex={0}
      >
        <table className="stack-table" role="table">
          <thead role="rowgroup">
            <tr role="row">
              <th role="columnheader" scope="col">
                {t.source}
              </th>
              <th role="columnheader" scope="col">
                {t.publisher}
              </th>
              <th role="columnheader" scope="col">
                {t.fetched}
              </th>
              <th role="columnheader" scope="col" className="num">
                {t.rows}
              </th>
              <th role="columnheader" scope="col">
                {t.licence}
              </th>
            </tr>
          </thead>
          <tbody role="rowgroup">
            {runs.map((run) => (
              <tr role="row" key={run.id}>
                <td role="cell" data-label={t.source}>
                  {/* One element, so the stacked layout keeps it in one column. */}
                  <span>
                    <a href={run.url} rel="external" lang={dataLang(locale)}>
                      {run.title}
                    </a>
                    {run.status !== "ok" ? (
                      <span className={styles.warning}>
                        {" "}
                        — {msg.sources.status[run.status]}
                      </span>
                    ) : null}
                  </span>
                </td>
                <td role="cell" data-label={t.publisher}>
                  {run.publisher}
                </td>
                <td role="cell" data-label={t.fetched}>
                  {run.status === "ok" || run.rowCount
                    ? fmt.date(run.fetchedAt)
                    : "–"}
                </td>
                <td role="cell" className="num" data-label={t.rows}>
                  {run.rowCount ? fmt.integer(run.rowCount) : "–"}
                </td>
                <td role="cell" data-label={t.licence}>
                  {msg.sources.licences[run.source] ?? run.licence}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
