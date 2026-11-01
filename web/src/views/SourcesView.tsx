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
      <div className={styles.wide}>
        <table>
          <thead>
            <tr>
              <th scope="col">{t.source}</th>
              <th scope="col">{t.publisher}</th>
              <th scope="col">{t.fetched}</th>
              <th scope="col" className="num">
                {t.rows}
              </th>
              <th scope="col">{t.licence}</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>
                  <a href={run.url} rel="external" lang={dataLang(locale)}>
                    {run.title}
                  </a>
                  {run.status !== "ok" ? (
                    <span className={styles.warning}>
                      {" "}
                      — {msg.sources.status[run.status]}
                    </span>
                  ) : null}
                </td>
                <td>{run.publisher}</td>
                <td>
                  {run.status === "ok" || run.rowCount
                    ? fmt.date(run.fetchedAt)
                    : "–"}
                </td>
                <td className="num">
                  {run.rowCount ? fmt.integer(run.rowCount) : "–"}
                </td>
                <td>{msg.sources.licences[run.source] ?? run.licence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
