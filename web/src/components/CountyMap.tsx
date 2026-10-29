import { loadBoundaries } from "@/lib/data";
import { projectBoundaries } from "@/lib/geo";
import { municipalityHref } from "@/lib/paths";
import { hr } from "@/messages/hr";
import styles from "./CountyMap.module.css";

type Props = {
  /** The municipality to mark (locator map on its own page). */
  highlight?: string;
  /** Visible heading and accessible name of the map. */
  title: string;
  width?: number;
};

/**
 * The county's municipalities as an SVG map, rendered at build time (D3).
 *
 * Every municipality with a page is a real link, so the map works without
 * JavaScript and with a keyboard (Tab moves between municipalities in
 * alphabetical order). It is an extra: the same links are always in a list.
 */
export function CountyMap({ highlight, title, width = 800 }: Props) {
  const map = projectBoundaries(loadBoundaries(), width);
  const shapes = [...map.shapes].sort((a, b) =>
    a.name.localeCompare(b.name, "hr"),
  );
  const marked = shapes.find((s) => s.slug === highlight);

  return (
    <figure className={styles.figure}>
      <figcaption className={styles.caption}>{title}</figcaption>
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
                <title>{`${shape.name}: ${hr.map.noData}`}</title>
              </path>
            );
          }
          return (
            <a
              key={shape.slug}
              href={municipalityHref(shape.slug)}
              aria-label={shape.name}
              aria-current={shape.slug === highlight ? "page" : undefined}
            >
              <title>{shape.name}</title>
              <path className={className} d={shape.d} />
            </a>
          );
        })}
        {marked ? (
          <text
            className={styles.label}
            x={marked.labelX}
            y={marked.labelY}
            textAnchor="middle"
            dominantBaseline="middle"
            aria-hidden="true"
          >
            {marked.name}
          </text>
        ) : null}
      </svg>
    </figure>
  );
}
