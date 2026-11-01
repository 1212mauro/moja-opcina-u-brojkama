"use client";

import Link from "next/link";
import { useId, useState, useSyncExternalStore } from "react";

import type { SearchEntry } from "@/lib/contract";
import { getFormat } from "@/lib/format";
import { municipalityPath } from "@/lib/paths";
import { filterEntries } from "@/lib/search";
import type { Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";
import styles from "./MunicipalitySearch.module.css";

const noSubscription = () => () => {};

/**
 * The full list is in the HTML, so the page works without JavaScript; with it, a
 * search box filters the list by name (diacritics optional) or postcode.
 */
export function MunicipalitySearch({
  locale,
  entries,
  caption,
}: {
  locale: Locale;
  entries: SearchEntry[];
  caption: string;
}) {
  const msg = getMessages(locale);
  const fmt = getFormat(locale);
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
  const cols = msg.home.columns;

  return (
    <div data-search-list>
      {enhanced ? (
        <div className={styles.search} role="search">
          <label htmlFor={inputId} className={styles.label}>
            {msg.home.searchLabel}
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
            {msg.home.searchHint}
          </p>
          <p className={styles.count} role="status" aria-live="polite">
            {shown.length
              ? msg.home.resultsCount(shown.length)
              : msg.home.noResults}
          </p>
        </div>
      ) : null}

      <div className={styles.tableWrap}>
        <table>
          <caption className={styles.caption}>{caption}</caption>
          <thead>
            <tr>
              <th scope="col">{cols.name}</th>
              <th scope="col">{cols.type}</th>
              <th scope="col" className="num">
                {cols.population}
              </th>
              <th scope="col">{cols.postcodes}</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((entry) => (
              <tr key={entry.slug}>
                <td>
                  <Link
                    href={municipalityPath(locale, entry.slug)}
                    className={styles.name}
                  >
                    {entry.name}
                  </Link>
                </td>
                <td>{msg.unitType[entry.type]}</td>
                <td className="num">{fmt.integer(entry.population)}</td>
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
