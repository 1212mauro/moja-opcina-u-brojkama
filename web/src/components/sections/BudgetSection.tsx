import { BarList } from "@/components/BarList";
import { Figure } from "@/components/Figure";
import { Notice } from "@/components/Notice";
import { SourceNote } from "@/components/SourceNote";
import type { BudgetItem, MunicipalityPage } from "@/lib/contract";
import { getFormat } from "@/lib/format";
import type { Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";

function BudgetFigure({
  locale,
  title,
  items,
  labels,
  summary,
  note,
}: {
  locale: Locale;
  title: string;
  items: BudgetItem[];
  /** This edition's wording by code; the data's official label otherwise. */
  labels: Record<string, string>;
  summary: (top: string, share: string) => string;
  note?: string;
}) {
  const msg = getMessages(locale);
  const fmt = getFormat(locale);
  const sorted = [...items]
    .sort((a, b) => b.amountEur - a.amountEur)
    .map((item) => ({ ...item, label: labels[item.code] ?? item.label }));
  const total = sorted.reduce((sum, item) => sum + item.amountEur, 0);
  const top = sorted[0];
  const cols = msg.budget.columns;
  return (
    <Figure
      locale={locale}
      title={title}
      summary={summary(top.label, fmt.share(top.amountEur / total))}
      rows={sorted}
      columns={[
        { header: cols.item, cell: (item) => item.label },
        {
          header: cols.amount,
          cell: (item) => fmt.eur(item.amountEur),
          numeric: true,
        },
        {
          header: cols.perResident,
          cell: (item) => fmt.eurCents(item.perResidentEur),
          numeric: true,
        },
        {
          header: cols.share,
          cell: (item) => fmt.share(item.amountEur / total),
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
          display: fmt.eur(item.amountEur),
          detail: msg.page.perResident(fmt.eurCents(item.perResidentEur)),
        }))}
      />
    </Figure>
  );
}

export function BudgetSection({
  locale,
  page,
}: {
  locale: Locale;
  page: MunicipalityPage;
}) {
  const msg = getMessages(locale);
  const budget = page.budget;
  if (!budget) return <Notice>{msg.missing.budget}</Notice>;
  return (
    <>
      <p>{msg.budget.intro(budget.year)}</p>
      {budget.revenueByType.length ? (
        <BudgetFigure
          locale={locale}
          title={msg.budget.revenueByType}
          items={budget.revenueByType}
          labels={msg.budget.revenueLabels}
          summary={msg.budget.revenueSummary}
        />
      ) : null}
      {budget.expenditureByFunction.length ? (
        <BudgetFigure
          locale={locale}
          title={msg.budget.expenditureByFunction}
          items={budget.expenditureByFunction}
          labels={msg.budget.functionLabels}
          summary={msg.budget.functionSummary}
          note={msg.budget.functionNote}
        />
      ) : null}
      <SourceNote locale={locale} page={page} runIds={[budget.sourceRunId]} />
    </>
  );
}
