import type { ReactNode } from "react";

import type { Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";
import styles from "./Figure.module.css";

export type Column<Row> = {
  header: string;
  cell: (row: Row) => ReactNode;
  numeric?: boolean;
};

type Props<Row> = {
  locale: Locale;
  title: string;
  /** One plain sentence that says what the chart shows (every chart has one). */
  summary?: string;
  /** The chart; omitted for table-only figures. */
  children?: ReactNode;
  /** The same data as a table: every chart has one (SPEC: accessibility). */
  rows: Row[];
  columns: Column<Row>[];
  note?: ReactNode;
};

export function Figure<Row>({
  locale,
  title,
  summary,
  children,
  rows,
  columns,
  note,
}: Props<Row>) {
  const msg = getMessages(locale);
  const table = (
    <table>
      <thead>
        <tr>
          {columns.map((column) => (
            <th
              key={column.header}
              scope="col"
              className={column.numeric ? "num" : undefined}
            >
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, index) => (
          <tr key={index}>
            {columns.map((column) => (
              <td
                key={column.header}
                className={column.numeric ? "num" : undefined}
              >
                {column.cell(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );

  return (
    <figure className={styles.figure}>
      <h3 className={styles.title}>{title}</h3>
      {summary ? (
        <figcaption className={styles.summary}>{summary}</figcaption>
      ) : null}
      {!children ? (
        <div
          className="table-scroll"
          role="region"
          aria-label={title}
          tabIndex={0}
        >
          {table}
        </div>
      ) : (
        <>
          {children}
          <details className={styles.details}>
            <summary>{msg.figure.showTable}</summary>
            <div
              className="table-scroll"
              role="region"
              aria-label={title}
              tabIndex={0}
            >
              {table}
            </div>
          </details>
        </>
      )}
      {note ? <p className={styles.note}>{note}</p> : null}
    </figure>
  );
}
