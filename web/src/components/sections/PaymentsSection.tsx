import { BarList } from "@/components/BarList";
import { Figure } from "@/components/Figure";
import { MonthlyColumns } from "@/components/MonthlyColumns";
import { Notice } from "@/components/Notice";
import { SourceNote } from "@/components/SourceNote";
import type { MunicipalityPage } from "@/lib/contract";
import {
  formatEur,
  formatInteger,
  formatMonth,
  monthWindow,
} from "@/lib/format";
import { hr } from "@/messages/hr";

export function PaymentsSection({ page }: { page: MunicipalityPage }) {
  const payments = page.payments;
  if (!payments || !payments.months.length)
    return <Notice>{hr.missing.payments}</Notice>;

  const totals = new Map(payments.months.map((m) => [m.month, m.totalEur]));
  const window = monthWindow(payments.months[payments.months.length - 1].month);
  const sum = payments.months.reduce((acc, m) => acc + m.totalEur, 0);
  const t = hr.payments.columns;

  return (
    <>
      <p>
        {hr.payments.intro(
          formatMonth(window[0]),
          formatMonth(window[window.length - 1]),
        )}
      </p>
      <Figure
        title={hr.payments.monthly}
        summary={hr.payments.monthlySummary(
          formatEur(sum),
          payments.months.length,
        )}
        rows={window}
        columns={[
          { header: t.month, cell: (m) => formatMonth(m) },
          {
            header: t.amount,
            cell: (m) =>
              totals.has(m)
                ? formatEur(totals.get(m)!)
                : hr.payments.missingMonth,
            numeric: true,
          },
        ]}
      >
        <MonthlyColumns months={window} totals={totals} />
      </Figure>

      {payments.byCategory.length ? (
        <Figure
          title={hr.payments.categories}
          summary={hr.payments.categoriesSummary(payments.byCategory[0].label)}
          rows={payments.byCategory}
          columns={[
            { header: t.category, cell: (c) => c.label },
            {
              header: t.amount,
              cell: (c) => formatEur(c.amountEur),
              numeric: true,
            },
          ]}
        >
          <BarList
            label={hr.payments.categories}
            bars={payments.byCategory.map((c) => ({
              key: c.label,
              label: c.label,
              value: c.amountEur,
              display: formatEur(c.amountEur),
            }))}
          />
        </Figure>
      ) : null}

      {payments.topRecipients.length ? (
        <Figure
          title={hr.payments.recipients}
          summary={hr.payments.recipientsSummary(
            payments.topRecipients[0].name,
            formatEur(payments.topRecipients[0].amountEur),
          )}
          rows={payments.topRecipients}
          columns={[
            { header: t.recipient, cell: (r) => r.name },
            {
              header: t.payments,
              cell: (r) => formatInteger(r.payments),
              numeric: true,
            },
            {
              header: t.amount,
              cell: (r) => formatEur(r.amountEur),
              numeric: true,
            },
          ]}
        >
          <BarList
            label={hr.payments.recipients}
            bars={payments.topRecipients.map((r, i) => ({
              key: `${r.oib ?? r.name}-${i}`,
              label: r.name,
              value: r.amountEur,
              display: formatEur(r.amountEur),
            }))}
          />
        </Figure>
      ) : null}
      <p>{hr.payments.privacy}</p>
      <SourceNote page={page} runIds={[payments.sourceRunId]} />
    </>
  );
}
