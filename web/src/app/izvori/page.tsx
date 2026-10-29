import type { Metadata } from "next";

import { loadSourceStatus } from "@/lib/data";
import { formatDate, formatInteger } from "@/lib/format";
import { hr } from "@/messages/hr";
import styles from "../prose.module.css";

export const metadata: Metadata = { title: hr.site.nav.sources };

/** F3: every source and when it was last fetched. */
export default function Sources() {
  const { runs, generatedAt } = loadSourceStatus();
  const t = hr.sources.columns;
  return (
    <article className={styles.prose}>
      <h1>{hr.site.nav.sources}</h1>
      <p className={styles.lead}>{hr.sources.intro}</p>
      <p>{hr.sources.generated(formatDate(generatedAt))}</p>
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
                  <a href={run.url} rel="external">
                    {run.title}
                  </a>
                  {run.status !== "ok" ? (
                    <span className={styles.warning}>
                      {" "}
                      — {hr.sources.status[run.status]}
                    </span>
                  ) : null}
                </td>
                <td>{run.publisher}</td>
                <td>
                  {run.status === "ok" || run.rowCount
                    ? formatDate(run.fetchedAt)
                    : "–"}
                </td>
                <td className="num">
                  {run.rowCount ? formatInteger(run.rowCount) : "–"}
                </td>
                <td>{run.licence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
