import { BarList } from "@/components/BarList";
import { Figure } from "@/components/Figure";
import { Notice } from "@/components/Notice";
import { SourceNote } from "@/components/SourceNote";
import type { MunicipalityPage } from "@/lib/contract";
import { getFormat } from "@/lib/format";
import { dataLang, type Locale } from "@/lib/i18n";
import { getMessages } from "@/messages";

export function ProcurementSection({
  locale,
  page,
}: {
  locale: Locale;
  page: MunicipalityPage;
}) {
  const msg = getMessages(locale);
  const fmt = getFormat(locale);
  const procurement = page.procurement;
  if (!procurement) return <Notice>{msg.missing.procurement}</Notice>;
  const cols = msg.procurement.columns;
  const top = procurement.topSuppliers[0];

  return (
    <>
      <p>
        {msg.procurement.intro(
          procurement.contractCount,
          fmt.integer(procurement.contractCount),
          procurement.dataFrom ? fmt.date(procurement.dataFrom) : "–",
          procurement.dataTo ? fmt.date(procurement.dataTo) : "–",
        )}
      </p>
      <p>
        {msg.procurement.total}:{" "}
        <strong>{fmt.eur(procurement.totalValueEur)}</strong>
      </p>

      {top ? (
        <Figure
          locale={locale}
          title={msg.procurement.topSuppliers}
          summary={
            // A share only makes sense of a positive total (amounts can be unpublished).
            procurement.totalValueEur > 0
              ? msg.procurement.topSuppliersSummary(
                  top.name,
                  fmt.share(top.totalEur / procurement.totalValueEur),
                )
              : msg.procurement.topSupplierName(top.name)
          }
          rows={procurement.topSuppliers}
          columns={[
            { header: cols.supplier, cell: (s) => s.name },
            {
              header: cols.contracts,
              cell: (s) => fmt.integer(s.contracts),
              numeric: true,
            },
            {
              header: cols.total,
              cell: (s) => fmt.eur(s.totalEur),
              numeric: true,
            },
          ]}
        >
          <BarList
            label={msg.procurement.topSuppliers}
            bars={procurement.topSuppliers.map((s, i) => ({
              key: `${s.oib ?? s.name}-${i}`,
              label: s.name,
              value: s.totalEur,
              display: fmt.eur(s.totalEur),
              detail: msg.procurement.contractCount(
                s.contracts,
                fmt.integer(s.contracts),
              ),
            }))}
          />
        </Figure>
      ) : null}

      {procurement.recentAwards.length ? (
        <Figure
          locale={locale}
          title={msg.procurement.recent}
          rows={procurement.recentAwards}
          columns={[
            {
              header: cols.date,
              cell: (a) => (a.signedOn ? fmt.date(a.signedOn) : "–"),
            },
            {
              header: cols.subject,
              cell: (a) => <span lang={dataLang(locale)}>{a.subject}</span>,
            },
            { header: cols.supplier, cell: (a) => a.supplierName },
            {
              header: cols.value,
              cell: (a) =>
                a.valueEur == null
                  ? msg.procurement.noValue
                  : fmt.eur(a.valueEur),
              numeric: true,
            },
          ]}
        />
      ) : null}
      <SourceNote
        locale={locale}
        page={page}
        runIds={procurement.sourceRunIds}
      />
    </>
  );
}
