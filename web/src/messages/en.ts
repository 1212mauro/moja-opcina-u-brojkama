/**
 * English UI text (E1), the same shape as hr.ts. Names from the data (municipalities,
 * suppliers, contract subjects, payment categories, source titles) stay in Croatian,
 * as published.
 */
import type { Messages } from "@/messages/hr";

/** Counties in English, by the Croatian adjective the data uses ("Varaždinska"). */
const COUNTIES: Record<string, string> = {
  Zagrebačka: "Zagreb County",
  "Krapinsko-zagorska": "Krapina-Zagorje County",
  "Sisačko-moslavačka": "Sisak-Moslavina County",
  Karlovačka: "Karlovac County",
  Varaždinska: "Varaždin County",
  "Koprivničko-križevačka": "Koprivnica-Križevci County",
  "Bjelovarsko-bilogorska": "Bjelovar-Bilogora County",
  "Primorsko-goranska": "Primorje-Gorski Kotar County",
  "Ličko-senjska": "Lika-Senj County",
  "Virovitičko-podravska": "Virovitica-Podravina County",
  "Požeško-slavonska": "Požega-Slavonia County",
  "Brodsko-posavska": "Brod-Posavina County",
  Zadarska: "Zadar County",
  "Osječko-baranjska": "Osijek-Baranja County",
  "Šibensko-kninska": "Šibenik-Knin County",
  "Vukovarsko-srijemska": "Vukovar-Srijem County",
  "Splitsko-dalmatinska": "Split-Dalmatia County",
  Istarska: "Istria County",
  "Dubrovačko-neretvanska": "Dubrovnik-Neretva County",
  Međimurska: "Međimurje County",
  "Grad Zagreb": "City of Zagreb",
};

const county = (name: string): string => COUNTIES[name] ?? `${name} County`;

/** English noun form after a number. */
const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);

export const en: Messages = {
  site: {
    name: "My Municipality in Numbers",
    tagline:
      "How your town or municipality spends money, what it buys and which public services are nearby.",
    skipToContent: "Skip to content",
    nav: {
      label: "Main navigation",
      home: "Home",
      methodology: "How we calculate",
      sources: "Data sources",
      accessibility: "Accessibility",
    },
    editions: {
      label: "Language",
      links: { hr: "Hrvatski" },
    },
    footer: {
      about:
        "A non-commercial open-source project. We only show data that public bodies have already published, and we do not judge whether spending is good or bad.",
      licence:
        "Source code: EUPL-1.2. Data: Open Licence of the Republic of Croatia, CC BY and ODbL (OpenStreetMap).",
    },
  },

  home: {
    title: "Find your municipality or town",
    intro:
      "For every municipality and town we show the budget, public procurement, payments and public services in one place, and compare them with similar ones in the same county.",
    searchLabel: "Name or postcode",
    searchHint: "For example “Lepoglava” or “42250”",
    resultsCount: (n: number) => `${n} ${plural(n, "result", "results")}`,
    noResults: "No municipality or town matches your search.",
    tableCaption: (name: string) => `Towns and municipalities: ${county(name)}`,
    allUnits: "Towns and municipalities",
    columns: {
      name: "Name",
      type: "Type",
      population: "Residents",
      postcodes: "Postcodes",
    },
  },

  unitType: { grad: "Town", opcina: "Municipality" },
  unitTypePlural: { grad: "towns", opcina: "municipalities" },
  band: {
    under_3k: "fewer than 3,000 residents",
    "3k_10k": "3,000 to 10,000 residents",
    "10k_35k": "10,000 to 35,000 residents",
    over_35k: "more than 35,000 residents",
  },

  page: {
    breadcrumb: "Breadcrumb",
    county,
    population: (total: string, year: number, estimate: boolean) =>
      `${total} residents (${year} ${estimate ? "estimate" : "census"})`,
    contents: "On this page",
    keyFigures: "At a glance",
    revenue: (year: number) => `Revenue ${year}`,
    expenditure: (year: number) => `Expenditure ${year}`,
    perResident: (value: string) => `${value} per resident`,
    contracts: "Public contracts",
    contractsSince: (from: string) => `since ${from}`,
    vsPeers: (
      direction: "more" | "less" | "same",
      share: string,
      only: string | null,
    ) =>
      direction === "same"
        ? `per resident, about the same as ${only ?? "similar units on average"}`
        : `per resident, ${share} ${direction} than ${only ?? "similar units on average"}`,
  },

  sections: {
    budget: "Budget",
    peers: "Compared with similar units",
    procurement: "Public procurement",
    payments: "Payments from the budget",
    facilities: "Schools, kindergartens and health care",
    sources: "Data sources",
  },

  budget: {
    intro: (year: number) =>
      `Actual revenue and expenditure in ${year}, from the financial report the unit submits to the Ministry of Finance.`,
    revenueByType: "Where the money comes from",
    expenditureByFunction: "What it is spent on",
    revenueSummary: (top: string, share: string) =>
      `The largest source of revenue is ${top.toLowerCase()} (${share} of all revenue).`,
    functionSummary: (top: string, share: string) =>
      `The largest share is spent on ${top.toLowerCase()} (${share} of expenditure classified by function).`,
    functionNote:
      "Expenditure by function does not include money the town or municipality passes to its own institutions (kindergartens, libraries…); that money appears with the institution that spends it.",
    // Account classes of the Croatian budget chart of accounts.
    revenueLabels: {
      "61": "Taxes",
      "62": "Social contributions",
      "63": "Grants from abroad and from other public budgets",
      "64": "Property income",
      "65": "Administrative fees and charges under special regulations",
      "66": "Sales of goods and services, and donations",
      "67": "Transfers from the budget",
      "68": "Fines, administrative measures and other revenue",
      "71": "Sale of non-produced long-term assets (land)",
      "72": "Sale of produced long-term assets (buildings, equipment)",
    },
    // COFOG divisions, as the UN classification names them.
    functionLabels: {
      "01": "General public services",
      "02": "Defence",
      "03": "Public order and safety",
      "04": "Economic affairs",
      "05": "Environmental protection",
      "06": "Housing and community amenities",
      "07": "Health",
      "08": "Recreation, culture and religion",
      "09": "Education",
      "10": "Social protection",
    },
    columns: {
      item: "Item",
      amount: "Amount",
      perResident: "Per resident",
      share: "Share",
    },
  },

  peers: {
    intro: (
      typePlural: string,
      band: string,
      countyName: string,
      count: number,
    ) =>
      `Similar units are ${typePlural} in the same county (${county(countyName)}) with ${band}.` +
      (count > 1 ? ` There are ${count}, including this one.` : ""),
    alone:
      "There is no other unit of the same type and size in this county, so no comparison is possible.",
    chartTitle: "Expenditure per resident",
    rank: (rank: number, of: number) =>
      rank === 1
        ? `the most of ${of} comparable units`
        : rank === of
          ? `the least of ${of} comparable units`
          : `the ${ordinal(rank)} most of ${of} comparable units`,
    summary: (name: string, rank: string) =>
      `${name} spends ${rank} per resident.`,
    thisUnit: "(this unit)",
    context:
      "A comparison per resident does not say whether spending is good or bad. Tourist municipalities, county seats and units with large investments often spend more per resident.",
    columns: {
      name: "Town or municipality",
      population: "Residents",
      revenue: "Revenue per resident",
      expenditure: "Expenditure per resident",
    },
  },

  procurement: {
    intro: (count: number, formatted: string, from: string, to: string) =>
      `${formatted} public ${plural(count, "contract", "contracts")} from ${from} to ${to}, including contracts of the unit's own institutions (kindergartens, libraries…).`,
    contractCount: (count: number, formatted: string) =>
      `${formatted} ${plural(count, "contract", "contracts")}`,
    total: "Total value of contracts (excluding VAT)",
    recent: "Latest contracts",
    topSuppliers: "Largest suppliers",
    topSuppliersSummary: (name: string, share: string) =>
      `The largest supplier is ${name}, with ${share} of the total contract value.`,
    topSupplierName: (name: string) => `The largest supplier is ${name}.`,
    noValue: "amount not published",
    columns: {
      date: "Date",
      subject: "Subject",
      supplier: "Supplier",
      value: "Value excluding VAT",
      contracts: "Contracts",
      total: "Total",
    },
  },

  payments: {
    intro: (from: string, to: string) =>
      `Payments from the budget from ${from} to ${to}, as the town or municipality publishes them every month.`,
    monthly: "Payments by month",
    monthlySummary: (total: string, months: number) =>
      `${total} in total over ${months} ${plural(months, "month", "months")} with published data.`,
    missingMonth: "not published",
    categories: "What the money is paid for",
    categoriesSummary: (label: string) => `The most was paid for “${label}”.`,
    recipients: "Largest recipients",
    recipientsSummary: (name: string, amount: string) =>
      `The largest recipient was ${name} (${amount}).`,
    labelsNote:
      "Categories are shown in Croatian, as the town or municipality publishes them.",
    privacy:
      "Payments to individuals are shown only as totals, without names, as the rules on publication and data protection require.",
    columns: {
      month: "Month",
      amount: "Amount",
      category: "Type of expenditure",
      recipient: "Recipient",
      payments: "Payments",
    },
  },

  facilities: {
    intro: (count: number) =>
      `${count} public ${plural(count, "facility", "facilities")} in this unit.`,
    types: {
      school: "Schools",
      kindergarten: "Kindergartens",
      health: "Health care and pharmacies",
    },
    address: "Address",
    noAddress: "no address given",
    mapLink: "Show on map",
  },

  map: {
    home: "Map: select a town or municipality, or choose one from the list below.",
    locator: (name: string) => `Location of ${name} in the county`,
    noData: "data not yet available",
    legend: "Map key",
    legendOthers: "other towns and municipalities",
    legendUnit: "town or municipality with data",
  },

  missing: {
    budget: "We do not have budget data for this unit yet.",
    peers: "No comparison is available because we have no budget data.",
    procurement: "We found no published public contracts for this unit.",
    payments: "We do not show payments from the budget for this unit yet.",
    facilities:
      "We found no schools, kindergartens or health facilities in this unit.",
  },

  notFound: {
    title: "Page not found",
    body: "This address does not exist. It may have been mistyped, or the page has moved.",
    home: "Find your municipality or town on the home page",
  },

  figure: {
    showTable: "Show the data as a table",
    source: "Source",
    retrieved: (date: string) => `retrieved ${date}`,
  },

  sources: {
    intro:
      "Every number on this page comes from one of these sources. We download the data automatically every night.",
    columns: {
      source: "Source",
      publisher: "Publisher",
      fetched: "Retrieved",
      rows: "Records",
      licence: "Licence",
    },
    generated: (date: string) =>
      `The data on this site was compiled on ${date}`,
    status: {
      failed: "the last download failed; showing the previous data",
      skipped: "not downloaded: the source requires special permission",
      unavailable: "the source is not available in a machine-readable form",
    },
    licences: {
      minfin_budget: "Publicly available data (no licence stated)",
      minfin_budget_users: "Open Licence of the Republic of Croatia",
      lau_codes: "© European Union, reuse with attribution",
      dzs_population:
        "Free use with attribution (Croatian Bureau of Statistics)",
      dzs_settlements:
        "Free use with attribution (Croatian Bureau of Statistics)",
      dzs_estimates:
        "Free use with attribution (Croatian Bureau of Statistics)",
      postcodes: "No licence stated",
      dgu_boundaries: "Open Licence of the Republic of Croatia",
      schools_primary: "Open Licence of the Republic of Croatia",
      schools_secondary: "Open Licence of the Republic of Croatia",
      kindergartens: "Open Licence of the Republic of Croatia",
      osm_facilities: "ODbL 1.0",
      payments: "The publishing towns and municipalities state no licence",
      contracts_municipal: "Open Licence of the Republic of Croatia",
      contracts_ted: "Reuse with attribution (Commission Decision 2011/833/EU)",
      contracts_eojn_legacy: "Publicly available data (no licence stated)",
      contracts_eojn: "Publicly available data (no licence stated)",
    },
  },
};

function ordinal(n: number): string {
  const lastTwo = n % 100;
  if (lastTwo >= 11 && lastTwo <= 13) return `${n}th`;
  return `${n}${["th", "st", "nd", "rd"][n % 10] ?? "th"}`;
}
