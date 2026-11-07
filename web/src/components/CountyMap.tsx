import { loadBoundaries } from "@/lib/data";
import { projectBoundaries } from "@/lib/geo";
import { municipalityHref } from "@/lib/paths";
import type { Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";
import styles from "./CountyMap.module.css";

type Props = {
  locale: Locale;
  /** The municipality to mark (locator map on its own page). */
  highlight?: string;
  /** Visible heading and accessible name of the map. */
  title: string;
  width?: number;
};

// Label size in map units and a rough width per character, to keep labels inside.
const LABEL_SIZE = 18;
const CHAR_WIDTH = LABEL_SIZE * 0.6;
const LABEL_PAD = 6;

/**
 * The county's municipalities as an SVG map, rendered at build time (D3).
 *
 * Every municipality with a page is a real link, so the map works without
 * JavaScript and with a keyboard (Tab moves between municipalities in
 * alphabetical order). It is an extra: the same links are always in a list.
 *
 * H6: hovering or focusing a municipality shows its name on the map. The names sit
 * in their own layer after every shape, so a neighbour drawn later never covers
 * them; a small stylesheet pairs each link with its name (CSS only, no JavaScript).
 * A legend explains the marked unit and units without data.
 */
export function CountyMap({ locale, highlight, title, width = 480 }: Props) {
  const msg = getMessages(locale);
  const map = projectBoundaries(loadBoundaries(), width);
  const shapes = [...map.shapes].sort((a, b) =>
    a.name.localeCompare(b.name, "hr"),
  );
  const marked = shapes.find((s) => s.slug === highlight);
  const anyMissing = shapes.some((s) => !s.hasData);

  // Keep a centred label inside the map's box.
  const labelX = (x: number, name: string) => {
    const half = (name.length * CHAR_WIDTH) / 2 + LABEL_PAD;
    return Math.min(Math.max(x, half), map.width - half);
  };

  const hoverRules = shapes
    .filter((s) => s.hasData && s.slug !== highlight)
    .map(
      (s) =>
        `.${styles.map} a[data-unit="${s.slug}"]:is(:hover,:focus-visible)~.${styles.names} [data-unit="${s.slug}"]{visibility:visible}`,
    )
    .join("");

  const legend = [
    marked
      ? { key: "here", swatch: styles.highlight, label: marked.name }
      : null,
    marked || anyMissing
      ? {
          key: "unit",
          swatch: styles.unit,
          label: marked ? msg.map.legendOthers : msg.map.legendUnit,
        }
      : null,
    anyMissing
      ? { key: "missing", swatch: styles.noData, label: msg.map.noData }
      : null,
  ].filter((item) => item !== null);

  return (
    <figure className={styles.figure}>
      <figcaption className={styles.caption}>{title}</figcaption>
      {hoverRules ? <style>{hoverRules}</style> : null}
      <svg
        className={highlight ? `${styles.map} ${styles.locator}` : styles.map}
        viewBox={`0 0 ${map.width} ${map.height}`}
        role="group"
        aria-label={title}
      >
        {shapes.map((shape) => {
          const className =
            shape.slug === highlight ? styles.highlight : styles.unit;
          if (!shape.hasData) {
            return (
              <path
                key={shape.slug}
                className={`${className} ${styles.noData}`}
                d={shape.d}
              >
                <title>{`${shape.name}: ${msg.map.noData}`}</title>
              </path>
            );
          }
          return (
            <a
              key={shape.slug}
              href={municipalityHref(locale, shape.slug)}
              aria-label={shape.name}
              aria-current={shape.slug === highlight ? "page" : undefined}
              data-unit={shape.slug}
            >
              <title>{shape.name}</title>
              <path className={className} d={shape.d} />
            </a>
          );
        })}
        {/* Names: the marked unit's always, the others' on hover or focus. */}
        <g className={styles.names} aria-hidden="true">
          {shapes
            .filter((s) => s.hasData || s.slug === highlight)
            .map((s) => (
              <text
                key={s.slug}
                data-unit={s.slug}
                className={
                  s.slug === highlight
                    ? `${styles.label} ${styles.labelShown}`
                    : styles.label
                }
                x={labelX(s.labelX, s.name)}
                y={s.labelY}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {s.name}
              </text>
            ))}
        </g>
      </svg>
      {legend.length > 0 ? (
        <ul className={styles.legend} aria-label={msg.map.legend}>
          {legend.map((item) => (
            <li key={item.key}>
              <svg
                className={styles.swatch}
                viewBox="0 0 16 12"
                aria-hidden="true"
              >
                <rect
                  className={item.swatch}
                  x="1"
                  y="1"
                  width="14"
                  height="10"
                />
              </svg>
              {item.label}
            </li>
          ))}
        </ul>
      ) : null}
    </figure>
  );
}
