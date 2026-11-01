import { BarList } from "@/components/BarList";
import { Figure } from "@/components/Figure";
import { MonthlyColumns } from "@/components/MonthlyColumns";
import { Notice } from "@/components/Notice";
import { SourceNote } from "@/components/SourceNote";
import type { MunicipalityPage } from "@/lib/contract";
import { getFormat, monthWindow } from "@/lib/format";
import { dataLang, type Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";

export function PaymentsSection({
  locale,
  page,
}: {
  locale: Locale;
  page: MunicipalityPage;
}) {
  const msg = getMessages(locale);
  const fmt = getFormat(locale);
  const payments = page.payments;
  if (!payments || !payments.months.length)
    return <Notice>{msg.missing.payments}</Notice>;

  const totals = new Map(payments.months.map((m) => [m.month, m.totalEur]));
  const calendar = monthWindow(
    payments.months[payments.months.length - 1].month,
  );
  const sum = payments.months.reduce((acc, m) => acc + m.totalEur, 0);
  const cols = msg.payments.columns;

  return (
    <>
      <p>
        {msg.payments.intro(
          fmt.month(calendar[0]),
          fmt.month(calendar[calendar.length - 1]),
        )}
      </p>
      <Figure
        locale={locale}
        title={msg.payments.monthly}
        summary={msg.payments.monthlySummary(
          fmt.eur(sum),
          payments.months.length,
        )}
        rows={calendar}
        columns={[
          { header: cols.month, cell: (m) => fmt.month(m) },
          {
            header: cols.amount,
            cell: (m) =>
              totals.has(m)
                ? fmt.eur(totals.get(m)!)
                : msg.payments.missingMonth,
            numeric: true,
          },
        ]}
      >
        <MonthlyColumns locale={locale} months={calendar} totals={totals} />
      </Figure>

      {payments.byCategory.length ? (
        <Figure
          locale={locale}
          title={msg.payments.categories}
          summary={msg.payments.categoriesSummary(payments.byCategory[0].label)}
          rows={payments.byCategory}
          note={msg.payments.labelsNote || undefined}
          columns={[
            {
              header: cols.category,
              cell: (c) => <span lang={dataLang(locale)}>{c.label}</span>,
            },
            {
              header: cols.amount,
              cell: (c) => fmt.eur(c.amountEur),
              numeric: true,
            },
          ]}
        >
          <BarList
            label={msg.payments.categories}
            bars={payments.byCategory.map((c) => ({
              key: c.label,
              label: c.label,
              lang: dataLang(locale),
              value: c.amountEur,
              display: fmt.eur(c.amountEur),
            }))}
          />
        </Figure>
      ) : null}

      {payments.topRecipients.length ? (
        <Figure
          locale={locale}
          title={msg.payments.recipients}
          summary={msg.payments.recipientsSummary(
            payments.topRecipients[0].name,
            fmt.eur(payments.topRecipients[0].amountEur),
          )}
          rows={payments.topRecipients}
          columns={[
            { header: cols.recipient, cell: (r) => r.name },
            {
              header: cols.payments,
              cell: (r) => fmt.integer(r.payments),
              numeric: true,
            },
            {
              header: cols.amount,
              cell: (r) => fmt.eur(r.amountEur),
              numeric: true,
            },
          ]}
        >
          <BarList
            label={msg.payments.recipients}
            bars={payments.topRecipients.map((r, i) => ({
              key: `${r.oib ?? r.name}-${i}`,
              label: r.name,
              value: r.amountEur,
              display: fmt.eur(r.amountEur),
            }))}
          />
        </Figure>
      ) : null}
      <p>{msg.payments.privacy}</p>
      <SourceNote locale={locale} page={page} runIds={[payments.sourceRunId]} />
    </>
  );
}
