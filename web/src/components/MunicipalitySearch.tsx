"use client";

import Link from "next/link";
import { useId, useState, useSyncExternalStore } from "react";

import type { SearchEntry } from "@/lib/contract";
import { formatInteger } from "@/lib/format";
import { filterEntries } from "@/lib/search";
import { hr } from "@/messages/hr";
import styles from "./MunicipalitySearch.module.css";

const noSubscription = () => () => {};

/**
 * The full list is in the HTML, so the page works without JavaScript; with it, a
 * search box filters the list by name (diacritics optional) or postcode.
 */
export function MunicipalitySearch({
  entries,
  caption,
}: {
  entries: SearchEntry[];
  caption: string;
}) {
  const [query, setQuery] = useState("");
  // false while rendering on the server, true once hydrated in the browser
  const enhanced = useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );
  const inputId = useId();
  const hintId = useId();
  const shown = filterEntries(entries, query);
  const t = hr.home.columns;

  return (
    <div>
      {enhanced ? (
        <div className={styles.search} role="search">
          <label htmlFor={inputId} className={styles.label}>
            {hr.home.searchLabel}
          </label>
          <input
            id={inputId}
            type="search"
            className={styles.input}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            aria-describedby={hintId}
            autoComplete="off"
          />
          <p id={hintId} className={styles.hint}>
            {hr.home.searchHint}
          </p>
          <p className={styles.count} role="status" aria-live="polite">
            {shown.length
              ? hr.home.resultsCount(shown.length)
              : hr.home.noResults}
          </p>
        </div>
      ) : null}

      <div className={styles.tableWrap}>
        <table>
          <caption className={styles.caption}>{caption}</caption>
          <thead>
            <tr>
              <th scope="col">{t.name}</th>
              <th scope="col">{t.type}</th>
              <th scope="col" className="num">
                {t.population}
              </th>
              <th scope="col">{t.postcodes}</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((entry) => (
              <tr key={entry.slug}>
                <td>
                  <Link href={`/opcina/${entry.slug}/`} className={styles.name}>
                    {entry.name}
                  </Link>
                </td>
                <td>{hr.unitType[entry.type]}</td>
                <td className="num">{formatInteger(entry.population)}</td>
                <td className={styles.postcodes}>
                  {entry.postcodes.join(", ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
