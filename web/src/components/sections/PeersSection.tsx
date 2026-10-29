import { BarList } from "@/components/BarList";
import { Figure } from "@/components/Figure";
import { Notice } from "@/components/Notice";
import { SourceNote } from "@/components/SourceNote";
import type { MunicipalityPage } from "@/lib/contract";
import { formatEurCents, formatInteger } from "@/lib/format";
import { hr } from "@/messages/hr";

export function PeersSection({ page }: { page: MunicipalityPage }) {
  const peers = page.peers;
  if (!peers) return <Notice>{hr.missing.peers}</Notice>;

  const intro = hr.peers.intro(
    hr.unitTypePlural[page.type],
    hr.band[page.band],
    page.county,
    peers.members.length,
  );
  if (peers.members.length < 2) {
    return (
      <>
        <p>{intro}</p>
        <Notice>{hr.peers.alone}</Notice>
      </>
    );
  }

  const members = [...peers.members].sort(
    (a, b) =>
      (b.expenditurePerResidentEur ?? 0) - (a.expenditurePerResidentEur ?? 0),
  );
  const rank = peers.ranks.find(
    (r) => r.metric === "expenditurePerResidentEur",
  );
  const t = hr.peers.columns;
  const runIds = page.budget ? [page.budget.sourceRunId] : [];

  return (
    <>
      <p>{intro}</p>
      <Figure
        title={`${hr.peers.chartTitle}, ${peers.year}.`}
        summary={
          rank
            ? hr.peers.summary(page.name, hr.peers.rank(rank.rank, rank.of))
            : ""
        }
        rows={members}
        columns={[
          {
            header: t.name,
            cell: (m) =>
              m.slug === page.slug ? (
                <strong>{m.name}</strong>
              ) : (
                <a href={`../${m.slug}/`}>{m.name}</a>
              ),
          },
          {
            header: t.population,
            cell: (m) => formatInteger(m.population),
            numeric: true,
          },
          {
            header: t.revenue,
            cell: (m) =>
              m.revenuePerResidentEur == null
                ? "–"
                : formatEurCents(m.revenuePerResidentEur),
            numeric: true,
          },
          {
            header: t.expenditure,
            cell: (m) =>
              m.expenditurePerResidentEur == null
                ? "–"
                : formatEurCents(m.expenditurePerResidentEur),
            numeric: true,
          },
        ]}
        note={hr.peers.context}
      >
        <BarList
          label={hr.peers.chartTitle}
          bars={members.map((m) => ({
            key: m.slug,
            label:
              m.slug === page.slug ? `${m.name} ${hr.peers.thisUnit}` : m.name,
            value: m.expenditurePerResidentEur ?? 0,
            display:
              m.expenditurePerResidentEur == null
                ? "–"
                : formatEurCents(m.expenditurePerResidentEur),
            highlight: m.slug === page.slug,
          }))}
        />
      </Figure>
      <SourceNote page={page} runIds={runIds} />
    </>
  );
}
