import { BarList } from "@/components/BarList";
import { Figure } from "@/components/Figure";
import { Notice } from "@/components/Notice";
import { SourceNote } from "@/components/SourceNote";
import type { MunicipalityPage } from "@/lib/contract";
import {
  formatDate,
  formatEur,
  formatInteger,
  formatShare,
} from "@/lib/format";
import { hr } from "@/messages/hr";

export function ProcurementSection({ page }: { page: MunicipalityPage }) {
  const procurement = page.procurement;
  if (!procurement) return <Notice>{hr.missing.procurement}</Notice>;
  const t = hr.procurement.columns;
  const top = procurement.topSuppliers[0];

  return (
    <>
      <p>
        {hr.procurement.intro(
          procurement.contractCount,
          formatInteger(procurement.contractCount),
          procurement.dataFrom ? formatDate(procurement.dataFrom) : "–",
          procurement.dataTo ? formatDate(procurement.dataTo) : "–",
        )}
      </p>
      <p>
        {hr.procurement.total}:{" "}
        <strong>{formatEur(procurement.totalValueEur)}</strong>
      </p>

      {top ? (
        <Figure
          title={hr.procurement.topSuppliers}
          summary={
            // A share only makes sense of a positive total (amounts can be unpublished).
            procurement.totalValueEur > 0
              ? hr.procurement.topSuppliersSummary(
                  top.name,
                  formatShare(top.totalEur / procurement.totalValueEur),
                )
              : hr.procurement.topSupplierName(top.name)
          }
          rows={procurement.topSuppliers}
          columns={[
            { header: t.supplier, cell: (s) => s.name },
            {
              header: t.contracts,
              cell: (s) => formatInteger(s.contracts),
              numeric: true,
            },
            {
              header: t.total,
              cell: (s) => formatEur(s.totalEur),
              numeric: true,
            },
          ]}
        >
          <BarList
            label={hr.procurement.topSuppliers}
            bars={procurement.topSuppliers.map((s, i) => ({
              key: `${s.oib ?? s.name}-${i}`,
              label: s.name,
              value: s.totalEur,
              display: formatEur(s.totalEur),
              detail: hr.procurement.contractCount(
                s.contracts,
                formatInteger(s.contracts),
              ),
            }))}
          />
        </Figure>
      ) : null}

      {procurement.recentAwards.length ? (
        <Figure
          title={hr.procurement.recent}
          rows={procurement.recentAwards}
          columns={[
            {
              header: t.date,
              cell: (a) => (a.signedOn ? formatDate(a.signedOn) : "–"),
            },
            { header: t.subject, cell: (a) => a.subject },
            { header: t.supplier, cell: (a) => a.supplierName },
            {
              header: t.value,
              cell: (a) =>
                a.valueEur == null
                  ? hr.procurement.noValue
                  : formatEur(a.valueEur),
              numeric: true,
            },
          ]}
        />
      ) : null}
      <SourceNote page={page} runIds={procurement.sourceRunIds} />
    </>
  );
}
