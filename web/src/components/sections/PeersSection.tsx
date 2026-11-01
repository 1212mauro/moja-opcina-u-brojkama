import Link from "next/link";

import { BarList } from "@/components/BarList";
import { Figure } from "@/components/Figure";
import { Notice } from "@/components/Notice";
import { SourceNote } from "@/components/SourceNote";
import type { MunicipalityPage } from "@/lib/contract";
import { getFormat } from "@/lib/format";
import { municipalityPath } from "@/lib/paths";
import type { Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";

export function PeersSection({
  locale,
  page,
}: {
  locale: Locale;
  page: MunicipalityPage;
}) {
  const msg = getMessages(locale);
  const fmt = getFormat(locale);
  const peers = page.peers;
  if (!peers) return <Notice>{msg.missing.peers}</Notice>;

  const intro = msg.peers.intro(
    msg.unitTypePlural[page.type],
    msg.band[page.band],
    page.county,
    peers.members.length,
  );
  if (peers.members.length < 2) {
    return (
      <>
        <p>{intro}</p>
        <Notice>{msg.peers.alone}</Notice>
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
  const cols = msg.peers.columns;
  const runIds = page.budget ? [page.budget.sourceRunId] : [];

  return (
    <>
      <p>{intro}</p>
      <Figure
        locale={locale}
        title={`${msg.peers.chartTitle}, ${peers.year}.`}
        summary={
          rank
            ? msg.peers.summary(page.name, msg.peers.rank(rank.rank, rank.of))
            : ""
        }
        rows={members}
        columns={[
          {
            header: cols.name,
            cell: (m) =>
              m.slug === page.slug ? (
                <strong>{m.name}</strong>
              ) : (
                <Link href={municipalityPath(locale, m.slug)}>{m.name}</Link>
              ),
          },
          {
            header: cols.population,
            cell: (m) => fmt.integer(m.population),
            numeric: true,
          },
          {
            header: cols.revenue,
            cell: (m) =>
              m.revenuePerResidentEur == null
                ? "–"
                : fmt.eurCents(m.revenuePerResidentEur),
            numeric: true,
          },
          {
            header: cols.expenditure,
            cell: (m) =>
              m.expenditurePerResidentEur == null
                ? "–"
                : fmt.eurCents(m.expenditurePerResidentEur),
            numeric: true,
          },
        ]}
        note={msg.peers.context}
      >
        <BarList
          compare
          label={msg.peers.chartTitle}
          bars={members.map((m) => ({
            key: m.slug,
            label:
              m.slug === page.slug ? `${m.name} ${msg.peers.thisUnit}` : m.name,
            value: m.expenditurePerResidentEur ?? 0,
            display:
              m.expenditurePerResidentEur == null
                ? "–"
                : fmt.eurCents(m.expenditurePerResidentEur),
            highlight: m.slug === page.slug,
          }))}
        />
      </Figure>
      <SourceNote locale={locale} page={page} runIds={runIds} />
    </>
  );
}
