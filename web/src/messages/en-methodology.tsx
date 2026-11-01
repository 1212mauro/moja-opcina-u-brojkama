import Link from "next/link";

import { routePath } from "@/lib/paths";
import { en } from "@/messages/en";

/** The methodology page's text in English (D11, E1); see hr-methodology.tsx. */
export function MethodologyText({ leadClass }: { leadClass: string }) {
  return (
    <>
      <h1>How we calculate</h1>
      <p className={leadClass}>
        Every number comes from publicly available data. We do not judge whether
        spending is good or bad: we show the figures and comparisons, and leave
        the interpretation to you.
      </p>

      <h2>Where the data comes from</h2>
      <ul>
        <li>
          <strong>Budget:</strong> the financial reports of towns and
          municipalities published by the Ministry of Finance (actual revenue
          and expenditure for the whole year).
        </li>
        <li>
          <strong>Population:</strong> the 2021 Census and the yearly estimates
          of the Croatian Bureau of Statistics.
        </li>
        <li>
          <strong>Public procurement:</strong> the contract registers of the
          Electronic Public Procurement Classifieds (EOJN RH).
        </li>
        <li>
          <strong>Payments:</strong> the monthly reports of payments from the
          budget that towns and municipalities publish under the Instruction
          (Official Gazette 59/23).
        </li>
        <li>
          <strong>Schools, kindergartens and health care:</strong> the registers
          of the Ministry of Science, Education and Youth, and OpenStreetMap.
        </li>
      </ul>
      <p>
        We download the data automatically every night. The list of sources,
        with the date each was last downloaded, is on the{" "}
        <Link href={routePath("en", { page: "sources" })}>
          {en.site.nav.sources}
        </Link>{" "}
        page.
      </p>

      <h2>How we link the data</h2>
      <p>
        Every record is linked to its town or municipality by the official code
        and tax number (OIB), not by name. Contracts and payments of a
        unit&apos;s own institutions (kindergartens, libraries, museums) are
        added to that unit, following the Ministry of Finance register of budget
        users. Schools and hospitals funded by the county or the state are not
        added.
      </p>

      <h2>Amounts per resident</h2>
      <p>
        An amount per resident is the amount divided by the number of residents
        in the same year (the Croatian Bureau of Statistics estimate, or the
        census if there is no estimate). Amounts from before 2023 are converted
        from kuna to euro at the fixed rate of 7.53450 kuna per euro.
      </p>

      <h2>Comparison with similar units</h2>
      <p>
        A town or municipality is compared with units of the same type (towns
        with towns, municipalities with municipalities) in the same county and
        of similar size. The size bands are: fewer than 3,000 residents, 3,000
        to 10,000, 10,000 to 35,000, and more than 35,000.
      </p>
      <p>
        A comparison per resident is not a verdict. Tourist municipalities,
        county seats and units in the middle of a large investment often spend
        more per resident; small municipalities have costs that do not grow with
        the number of residents.
      </p>

      <h2>Expenditure by function</h2>
      <p>
        Expenditure by function (education, environmental protection, culture…)
        is shown as the towns and municipalities classify it in their reports.
        This breakdown does not include money passed to the unit&apos;s own
        institutions, so its total is smaller than total expenditure.
      </p>

      <h2>Public procurement</h2>
      <p>
        Contract values exclude VAT. Amendments change a contract&apos;s total
        value but are not counted as new contracts. Some contracts in the
        register have no published amount; we count them but do not add up their
        value.
      </p>

      <h2>Payments and personal data</h2>
      <p>
        Payments to individuals (salaries, fees, support for residents) are
        shown only as totals by type of expenditure, without names or tax
        numbers. If we cannot confirm that a recipient is a company, association
        or public body, we do not show its name. We do not show payment
        descriptions, because they can contain names.
      </p>
      <p>
        Some towns and municipalities publish their payments only in a form we
        cannot download automatically; for them we show no payments and say so
        clearly on their page.
      </p>

      <h2>If you spot a mistake</h2>
      <p>
        We show the data as it was published. If you think a number is wrong,
        and especially if you represent a town or municipality, let us know and
        we will check the source and correct the display or explain the
        difference.
      </p>
    </>
  );
}
