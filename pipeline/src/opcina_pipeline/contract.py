"""Data contract between the pipeline and the website.

The pipeline writes JSON files shaped by these models into ``web/public/data/``:

- ``search-index.json``      -> SearchIndex
- ``m/<slug>.json``          -> MunicipalityPage
- ``sources.json``           -> SourceStatus
- ``boundaries.geojson``     -> Boundaries

These models are the single source of truth: ``opcina schema`` writes them to
``contract/schema.json`` and the website generates its TypeScript types from
that file (``npm run gen:types`` in ``web/``).
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

UnitType = Literal["grad", "opcina"]
PopulationBand = Literal["under_3k", "3k_10k", "10k_35k", "over_35k"]
SourceKey = Literal[
    "minfin_budget",
    "minfin_budget_users",
    "eojn_contracts",
    "dzs_population",
    "dgu_boundaries",
    "facilities",
    "payments",
]
FacilityType = Literal["school", "kindergarten", "health"]


class ContractModel(BaseModel):
    """Base for every contract model: camelCase in JSON, snake_case in Python."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="forbid",
    )


class SourceRun(ContractModel):
    """One fetch of one source file; every figure on the site points to one of these."""

    id: str
    source: SourceKey
    title: str
    publisher: str
    url: str
    licence: str
    fetched_at: datetime
    file_hash: str
    row_count: int
    status: Literal["ok", "failed"]


class Population(ContractModel):
    year: int
    total: int


class BudgetItem(ContractModel):
    """A revenue type or a spending function (COFOG) with its amount."""

    code: str
    label: str
    amount_eur: float
    per_resident_eur: float


class Budget(ContractModel):
    year: int
    period: Literal["H1", "FY"]
    revenue_total_eur: float
    expenditure_total_eur: float
    revenue_per_resident_eur: float
    expenditure_per_resident_eur: float
    revenue_by_type: list[BudgetItem]
    expenditure_by_function: list[BudgetItem]
    source_run_id: str


class PeerMember(ContractModel):
    slug: str
    name: str
    population: int
    revenue_per_resident_eur: float | None
    expenditure_per_resident_eur: float | None


class Rank(ContractModel):
    """Position of this municipality among its peers for one metric (1 = highest)."""

    metric: str
    rank: int
    of: int


class Peers(ContractModel):
    """Same county, unit type and population band as the page's municipality."""

    year: int
    members: list[PeerMember]
    ranks: list[Rank]


class ContractAward(ContractModel):
    contract_id: str
    subject: str
    supplier_name: str
    supplier_oib: str | None
    cpv: str | None
    value_eur: float
    signed_on: date


class SupplierTotal(ContractModel):
    name: str
    oib: str | None
    contracts: int
    total_eur: float


class Procurement(ContractModel):
    data_from: date
    data_to: date
    contract_count: int
    total_value_eur: float
    recent_awards: list[ContractAward]
    top_suppliers: list[SupplierTotal]
    source_run_ids: list[str]


class MonthlyTotal(ContractModel):
    month: str  # YYYY-MM
    total_eur: float


class PaymentCategory(ContractModel):
    label: str
    amount_eur: float


class PaymentRecipient(ContractModel):
    """Legal persons only; payments to private individuals appear only as categories."""

    name: str
    oib: str | None
    payments: int
    amount_eur: float


class Payments(ContractModel):
    months: list[MonthlyTotal]
    by_category: list[PaymentCategory]
    top_recipients: list[PaymentRecipient]
    source_run_id: str


class Facility(ContractModel):
    type: FacilityType
    name: str
    address: str | None
    lat: float
    lon: float
    source_run_id: str


class MunicipalityPage(ContractModel):
    """Everything shown on one municipality page. Sections are null when data is missing."""

    slug: str
    oib: str
    rkp: str
    dzs_code: str
    lau_code: str
    name: str
    type: UnitType
    county: str
    population: Population
    band: PopulationBand
    budget: Budget | None
    peers: Peers | None
    procurement: Procurement | None
    payments: Payments | None
    facilities: list[Facility]
    sources: list[SourceRun]
    generated_at: datetime


class SearchEntry(ContractModel):
    slug: str
    name: str
    name_ascii: str  # lower-case, diacritics removed: "Čakovec" -> "cakovec"
    type: UnitType
    county: str
    population: int
    postcodes: list[str]
    has_data: bool


class SearchIndex(ContractModel):
    generated_at: datetime
    entries: list[SearchEntry]


class SourceStatus(ContractModel):
    generated_at: datetime
    runs: list[SourceRun]


class BoundaryProperties(ContractModel):
    slug: str
    name: str
    type: UnitType
    has_data: bool


class BoundaryFeature(ContractModel):
    type: Literal["Feature"]
    properties: BoundaryProperties
    geometry: dict[str, Any]  # GeoJSON Polygon or MultiPolygon, simplified for the browser


class Boundaries(ContractModel):
    """GeoJSON FeatureCollection of municipality outlines."""

    type: Literal["FeatureCollection"]
    features: list[BoundaryFeature]


class Contract(ContractModel):
    """Wrapper that pulls every published file shape into one JSON Schema."""

    municipality_page: MunicipalityPage
    search_index: SearchIndex
    source_status: SourceStatus
    boundaries: Boundaries
