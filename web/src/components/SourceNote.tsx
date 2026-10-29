import type { MunicipalityPage } from "@/lib/contract";
import { formatDate } from "@/lib/format";
import { hr } from "@/messages/hr";
import styles from "./SourceNote.module.css";

/**
 * "Where does this number come from?" (D10): the fetch runs behind a section, linked
 * to the page's source list, which names the file, publisher, licence and date.
 */
export function SourceNote({
  page,
  runIds,
}: {
  page: MunicipalityPage;
  runIds: string[];
}) {
  const runs = page.sources.filter((run) => runIds.includes(run.id));
  if (!runs.length) return null;
  return (
    <p className={styles.note}>
      {hr.figure.source}:{" "}
      {runs.map((run, i) => (
        <span key={run.id}>
          {i > 0 ? "; " : null}
          <a href={`#izvor-${run.id}`}>
            {hr.figure.sourceLink(run.title, formatDate(run.fetchedAt))}
          </a>
        </span>
      ))}
    </p>
  );
}
