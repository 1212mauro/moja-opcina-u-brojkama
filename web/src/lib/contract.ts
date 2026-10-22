/* Generated from contract/schema.json by npm run gen:types. Do not edit by hand. */

/**
 * Wrapper that pulls every published file shape into one JSON Schema.
 */
export interface Contract {
  municipalityPage: MunicipalityPage;
  searchIndex: SearchIndex;
  sourceStatus: SourceStatus;
}
/**
 * Everything shown on one municipality page. Sections are null when data is missing.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "MunicipalityPage".
 */
export interface MunicipalityPage {
  slug: string;
  oib: string;
  rkp: string;
  dzsCode: string;
  lauCode: string;
  name: string;
  type: "grad" | "opcina";
  county: string;
  population: Population;
  band: "under_3k" | "3k_10k" | "10k_35k" | "over_35k";
  budget: Budget | null;
  peers: Peers | null;
  procurement: Procurement | null;
  payments: Payments | null;
  facilities: Facility[];
  sources: SourceRun[];
  generatedAt: string;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Population".
 */
export interface Population {
  year: number;
  total: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Budget".
 */
export interface Budget {
  year: number;
  period: "H1" | "FY";
  revenueTotalEur: number;
  expenditureTotalEur: number;
  revenuePerResidentEur: number;
  expenditurePerResidentEur: number;
  revenueByType: BudgetItem[];
  expenditureByFunction: BudgetItem[];
  sourceRunId: string;
}
/**
 * A revenue type or a spending function (COFOG) with its amount.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "BudgetItem".
 */
export interface BudgetItem {
  code: string;
  label: string;
  amountEur: number;
  perResidentEur: number;
}
/**
 * Same county, same unit type, same population band.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Peers".
 */
export interface Peers {
  county: string;
  unitType: "grad" | "opcina";
  band: "under_3k" | "3k_10k" | "10k_35k" | "over_35k";
  year: number;
  members: PeerMember[];
  ranks: Rank[];
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "PeerMember".
 */
export interface PeerMember {
  slug: string;
  name: string;
  population: number;
  revenuePerResidentEur: number | null;
  expenditurePerResidentEur: number | null;
}
/**
 * Position of this municipality among its peers for one metric (1 = highest).
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Rank".
 */
export interface Rank {
  metric: string;
  rank: number;
  of: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Procurement".
 */
export interface Procurement {
  dataFrom: string;
  dataTo: string;
  contractCount: number;
  totalValueEur: number;
  recentAwards: ContractAward[];
  topSuppliers: SupplierTotal[];
  sourceRunIds: string[];
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "ContractAward".
 */
export interface ContractAward {
  contractId: string;
  subject: string;
  supplierName: string;
  supplierOib: string | null;
  cpv: string | null;
  valueEur: number;
  signedOn: string;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "SupplierTotal".
 */
export interface SupplierTotal {
  name: string;
  oib: string | null;
  contracts: number;
  totalEur: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Payments".
 */
export interface Payments {
  months: MonthlyTotal[];
  byCategory: PaymentCategory[];
  topRecipients: PaymentRecipient[];
  sourceRunId: string;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "MonthlyTotal".
 */
export interface MonthlyTotal {
  month: string;
  totalEur: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "PaymentCategory".
 */
export interface PaymentCategory {
  label: string;
  amountEur: number;
}
/**
 * Legal persons only; payments to private individuals appear only as categories.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "PaymentRecipient".
 */
export interface PaymentRecipient {
  name: string;
  oib: string | null;
  payments: number;
  amountEur: number;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "Facility".
 */
export interface Facility {
  type: "school" | "kindergarten" | "health";
  name: string;
  address: string | null;
  lat: number;
  lon: number;
  sourceRunId: string;
}
/**
 * One fetch of one source file; every figure on the site points to one of these.
 *
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "SourceRun".
 */
export interface SourceRun {
  id: string;
  source:
    | "minfin_budget"
    | "minfin_budget_users"
    | "eojn_contracts"
    | "dzs_population"
    | "dgu_boundaries"
    | "facilities"
    | "payments";
  title: string;
  publisher: string;
  url: string;
  licence: string;
  fetchedAt: string;
  fileHash: string;
  rowCount: number;
  status: "ok" | "failed";
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "SearchIndex".
 */
export interface SearchIndex {
  generatedAt: string;
  entries: SearchEntry[];
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "SearchEntry".
 */
export interface SearchEntry {
  slug: string;
  name: string;
  nameAscii: string;
  type: "grad" | "opcina";
  county: string;
  population: number;
  postcodes: string[];
  hasData: boolean;
}
/**
 * This interface was referenced by `Contract`'s JSON-Schema
 * via the `definition` "SourceStatus".
 */
export interface SourceStatus {
  generatedAt: string;
  runs: SourceRun[];
}
