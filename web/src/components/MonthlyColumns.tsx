import { formatEurShort, formatMonth, formatMonthShort } from "@/lib/format";
import { hr } from "@/messages/hr";
import styles from "./MonthlyColumns.module.css";

type Props = {
  /** Calendar months in order, "YYYY-MM"; a month without data stays as a visible gap. */
  months: string[];
  totals: Map<string, number>;
};

const WIDTH = 720;
const HEIGHT = 220;
const TOP = 16;
const BOTTOM = 28;
const GAP = 2; // surface gap between adjacent columns

/**
 * Twelve monthly columns as SVG, rendered on the server. The SVG is decorative
 * (aria-hidden); the figure's summary and table carry the same data. Each column
 * has a native tooltip (<title>) with the exact amount.
 */
export function MonthlyColumns({ months, totals }: Props) {
  const max = Math.max(...months.map((m) => totals.get(m) ?? 0), 0);
  const slot = WIDTH / months.length;
  const plot = HEIGHT - TOP - BOTTOM;

  return (
    // On narrow screens the chart keeps a minimum width and scrolls sideways, so
    // its month labels never shrink below a readable size.
    <div className={styles.scroll}>
      <svg
        className={styles.chart}
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="presentation"
        aria-hidden="true"
        focusable="false"
      >
        <line
          className={styles.baseline}
          x1={0}
          x2={WIDTH}
          y1={TOP + plot}
          y2={TOP + plot}
        />
        {months.map((month, i) => {
          const value = totals.get(month);
          const x = i * slot + GAP;
          const width = slot - GAP * 2;
          const labelX = i * slot + slot / 2;
          if (value === undefined) {
            return (
              <g key={month}>
                <title>{`${formatMonth(month)}: ${hr.payments.missingMonth}`}</title>
                <text
                  className={styles.missing}
                  x={labelX}
                  y={TOP + plot - 6}
                  textAnchor="middle"
                >
                  –
                </text>
                <text
                  className={styles.axis}
                  x={labelX}
                  y={HEIGHT - 8}
                  textAnchor="middle"
                >
                  {formatMonthShort(month)}
                </text>
              </g>
            );
          }
          // A net-negative month (refunds) sits on the baseline; the table shows the amount.
          const height =
            max > 0 ? Math.max((Math.max(value, 0) / max) * plot, 1) : 1;
          const y = TOP + plot - height;
          const r = Math.min(4, height / 2, width / 2);
          // Rounded at the data end (top), square on the baseline.
          const path = `M${x},${y + height} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${y + height} Z`;
          return (
            <g key={month}>
              <title>{`${formatMonth(month)}: ${formatEurShort(value)}`}</title>
              <path className={styles.column} d={path} />
              <text
                className={styles.axis}
                x={labelX}
                y={HEIGHT - 8}
                textAnchor="middle"
              >
                {formatMonthShort(month)}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
