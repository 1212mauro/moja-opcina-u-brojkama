import type { MunicipalityPage } from "@/lib/contract";
import { getFormat } from "@/lib/format";
import type { Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";
import styles from "./SourceNote.module.css";

/**
 * "Where does this number come from?" (D10): the fetch runs behind a section, linked
 * to the page's source list, which names the file, publisher, licence and date.
 */
export function SourceNote({
  locale,
  page,
  runIds,
}: {
  locale: Locale;
  page: MunicipalityPage;
  runIds: string[];
}) {
  const msg = getMessages(locale);
  const fmt = getFormat(locale);
  const runs = page.sources.filter((run) => runIds.includes(run.id));
  if (!runs.length) return null;
  return (
    <p className={styles.note}>
      {msg.figure.source}:{" "}
      {runs.map((run, i) => (
        <span key={run.id}>
          {i > 0 ? "; " : null}
          <a href={`#izvor-${run.id}`}>
            {msg.figure.sourceLink(run.title, fmt.date(run.fetchedAt))}
          </a>
        </span>
      ))}
    </p>
  );
}
