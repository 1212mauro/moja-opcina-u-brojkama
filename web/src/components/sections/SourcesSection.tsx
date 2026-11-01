import type { SourceRun } from "@/lib/contract";
import { getFormat } from "@/lib/format";
import { dataLang, type Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";

/** Every source behind the page, each with an anchor that the SourceNotes link to (D10). */
export function SourcesTable({
  locale,
  runs,
}: {
  locale: Locale;
  runs: SourceRun[];
}) {
  const msg = getMessages(locale);
  const fmt = getFormat(locale);
  const cols = msg.sources.columns;
  return (
    <div style={{ overflowX: "auto" }}>
      <table>
        <thead>
          <tr>
            <th scope="col">{cols.source}</th>
            <th scope="col">{cols.publisher}</th>
            <th scope="col">{cols.fetched}</th>
            <th scope="col">{cols.licence}</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} id={`izvor-${run.id}`}>
              <td>
                <a href={run.url} rel="external" lang={dataLang(locale)}>
                  {run.title}
                </a>
              </td>
              <td>{run.publisher}</td>
              <td>{fmt.date(run.fetchedAt)}</td>
              <td>{msg.sources.licences[run.source] ?? run.licence}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
