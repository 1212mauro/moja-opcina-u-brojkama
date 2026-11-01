import styles from "./BarList.module.css";

export type Bar = {
  key: string;
  label: string;
  /** The label's language when it differs from the page's. */
  lang?: string;
  value: number;
  /** The formatted value shown next to the bar. */
  display: string;
  /** Secondary text under the value, e.g. a per-resident figure. */
  detail?: string;
  /** The municipality this page is about: blue, bold, and named as such in text. */
  highlight?: boolean;
};

/**
 * Horizontal bars as plain HTML: each row is real text (label and value), so it reads
 * correctly without CSS, without JavaScript and in a screen reader; the bar itself is
 * decorative. Bars start at zero, one value axis, rounded only at the data end.
 */
export function BarList({
  bars,
  label,
  compare = false,
}: {
  bars: Bar[];
  label: string;
  /** Peer comparison: only the highlighted bar is blue, the others grey. */
  compare?: boolean;
}) {
  const max = Math.max(...bars.map((bar) => Math.abs(bar.value)), 0);
  return (
    <ul
      className={`${styles.list} ${compare ? styles.compare : styles.single}`}
      aria-label={label}
    >
      {bars.map((bar) => {
        const width = max > 0 ? (Math.max(bar.value, 0) / max) * 100 : 0;
        return (
          <li
            key={bar.key}
            className={
              bar.highlight ? `${styles.row} ${styles.highlight}` : styles.row
            }
          >
            <span className={styles.label} lang={bar.lang}>
              {bar.label}
            </span>
            <span className={styles.track} aria-hidden="true">
              <span className={styles.bar} style={{ width: `${width}%` }} />
            </span>
            <span className={styles.value}>
              {bar.display}
              {bar.detail ? (
                <span className={styles.detail}>{bar.detail}</span>
              ) : null}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
