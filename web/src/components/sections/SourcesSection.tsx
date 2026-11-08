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
    <div
      className="table-scroll"
      role="region"
      aria-label={msg.sections.sources}
      tabIndex={0}
    >
      <table className="stack-table" role="table">
        <thead role="rowgroup">
          <tr role="row">
            <th role="columnheader" scope="col">
              {cols.source}
            </th>
            <th role="columnheader" scope="col">
              {cols.publisher}
            </th>
            <th role="columnheader" scope="col">
              {cols.fetched}
            </th>
            <th role="columnheader" scope="col">
              {cols.licence}
            </th>
          </tr>
        </thead>
        <tbody role="rowgroup">
          {runs.map((run) => (
            <tr role="row" key={run.id} id={`izvor-${run.id}`}>
              <td role="cell" data-label={cols.source}>
                <a href={run.url} rel="external" lang={dataLang(locale)}>
                  {run.title}
                </a>
              </td>
              <td role="cell" data-label={cols.publisher}>
                {run.publisher}
              </td>
              <td role="cell" className="nowrap" data-label={cols.fetched}>
                {fmt.date(run.fetchedAt)}
              </td>
              <td role="cell" data-label={cols.licence}>
                {msg.sources.licences[run.source] ?? run.licence}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
