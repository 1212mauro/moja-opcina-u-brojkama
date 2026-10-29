import type { SourceRun } from "@/lib/contract";
import { formatDate } from "@/lib/format";
import { hr } from "@/messages/hr";

/** Every source behind the page, each with an anchor that the SourceNotes link to (D10). */
export function SourcesTable({ runs }: { runs: SourceRun[] }) {
  const t = hr.sources.columns;
  return (
    <div style={{ overflowX: "auto" }}>
      <table>
        <thead>
          <tr>
            <th scope="col">{t.source}</th>
            <th scope="col">{t.publisher}</th>
            <th scope="col">{t.fetched}</th>
            <th scope="col">{t.licence}</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} id={`izvor-${run.id}`}>
              <td>
                <a href={run.url} rel="external">
                  {run.title}
                </a>
              </td>
              <td>{run.publisher}</td>
              <td>{formatDate(run.fetchedAt)}</td>
              <td>{run.licence}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
