import { BarList } from "@/components/BarList";
import { Figure } from "@/components/Figure";
import { Notice } from "@/components/Notice";
import { SourceNote } from "@/components/SourceNote";
import type { BudgetItem, MunicipalityPage } from "@/lib/contract";
import { formatEur, formatEurCents, formatShare } from "@/lib/format";
import { hr } from "@/messages/hr";

function BudgetFigure({
  title,
  items,
  summary,
  note,
}: {
  title: string;
  items: BudgetItem[];
  summary: (top: string, share: string) => string;
  note?: string;
}) {
  const sorted = [...items].sort((a, b) => b.amountEur - a.amountEur);
  const total = sorted.reduce((sum, item) => sum + item.amountEur, 0);
  const top = sorted[0];
  const t = hr.budget.columns;
  return (
    <Figure
      title={title}
      summary={summary(top.label, formatShare(top.amountEur / total))}
      rows={sorted}
      columns={[
        { header: t.item, cell: (item) => item.label },
        {
          header: t.amount,
          cell: (item) => formatEur(item.amountEur),
          numeric: true,
        },
        {
          header: t.perResident,
          cell: (item) => formatEurCents(item.perResidentEur),
          numeric: true,
        },
        {
          header: t.share,
          cell: (item) => formatShare(item.amountEur / total),
          numeric: true,
        },
      ]}
      note={note}
    >
      <BarList
        label={title}
        bars={sorted.map((item) => ({
          key: item.code,
          label: item.label,
          value: item.amountEur,
          display: formatEur(item.amountEur),
          detail: hr.page.perResident(formatEurCents(item.perResidentEur)),
        }))}
      />
    </Figure>
  );
}

export function BudgetSection({ page }: { page: MunicipalityPage }) {
  const budget = page.budget;
  if (!budget) return <Notice>{hr.missing.budget}</Notice>;
  return (
    <>
      <p>{hr.budget.intro(budget.year)}</p>
      {budget.revenueByType.length ? (
        <BudgetFigure
          title={hr.budget.revenueByType}
          items={budget.revenueByType}
          summary={hr.budget.revenueSummary}
        />
      ) : null}
      {budget.expenditureByFunction.length ? (
        <BudgetFigure
          title={hr.budget.expenditureByFunction}
          items={budget.expenditureByFunction}
          summary={hr.budget.functionSummary}
          note={hr.budget.functionNote}
        />
      ) : null}
      <SourceNote page={page} runIds={[budget.sourceRunId]} />
    </>
  );
}
