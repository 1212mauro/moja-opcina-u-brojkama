import type { MunicipalityPage } from "@/lib/contract";

type Metric = "revenuePerResidentEur" | "expenditurePerResidentEur";

/**
 * H5: how one per-resident figure compares with the other similar units.
 *
 * `diff` is the relative difference from the others' average (0.12 = 12 % more).
 * With exactly one other unit, `only` names it, so the sentence says "than Novi Marof"
 * instead of calling one number an average. Null when there is nothing to compare:
 * no peers, a different year, or no other unit with this figure.
 */
export interface PeerComparison {
  diff: number;
  only: string | null;
}

export function compareWithPeers(
  page: MunicipalityPage,
  metric: Metric,
): PeerComparison | null {
  const { budget, peers } = page;
  if (!budget || !peers || peers.year !== budget.year) return null;
  const own = budget[metric];
  const others = peers.members.filter(
    (m) => m.slug !== page.slug && m[metric] != null,
  );
  if (others.length === 0) return null;
  const average =
    others.reduce((sum, m) => sum + (m[metric] ?? 0), 0) / others.length;
  if (average <= 0) return null;
  return {
    diff: own / average - 1,
    only: others.length === 1 ? others[0].name : null,
  };
}
