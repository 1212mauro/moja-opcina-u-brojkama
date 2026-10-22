"""Website data (task C11): published tables -> JSON files shaped by the contract.

Writes to ``web/public/data/``:

- ``m/<slug>.json``        one ``MunicipalityPage`` per municipality in scope
- ``search-index.json``    ``SearchIndex`` (names, ASCII names, postcodes)
- ``sources.json``         ``SourceStatus`` (latest run of every source)
- ``boundaries.geojson``   ``Boundaries`` (simplified outlines)

Every figure carries the id of the fetch it came from; the page's ``sources`` list
resolves those ids to title, publisher, licence and fetch time. A section whose
table is missing for a municipality is ``null`` and the site says so.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from opcina_pipeline.boundaries import write_boundaries
from opcina_pipeline.config import config_path, load_sources, repo_root
from opcina_pipeline.contract import (
    Budget,
    BudgetItem,
    ContractAward,
    Facility,
    MonthlyTotal,
    MunicipalityPage,
    PaymentCategory,
    PaymentRecipient,
    Payments,
    PeerMember,
    Peers,
    Population,
    Procurement,
    Rank,
    SearchEntry,
    SearchIndex,
    SourceRun,
    SourceStatus,
    SupplierTotal,
)
from opcina_pipeline.peers import METRICS, band_for, peer_table
from opcina_pipeline.tables import interim_path
from opcina_pipeline.text import ascii_fold

RECENT_AWARDS = 10
TOP_SUPPLIERS = 5
TOP_RECIPIENTS = 10
TOP_CATEGORIES = 10
PAYMENT_MONTHS = 12

CONTRACT_METRIC_NAMES = {
    "revenue_per_resident_eur": "revenuePerResidentEur",
    "expenditure_per_resident_eur": "expenditurePerResidentEur",
}


def read_published(table: str) -> pl.DataFrame | None:
    path = interim_path(table, "published")
    return pl.read_parquet(path) if path.exists() else None


def read_runs(log_path: Path) -> dict[str, dict]:
    """Every run in the fetch log, by id."""
    runs = {}
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            runs[record["id"]] = record
    return runs


def source_run(run: dict, row_count: int) -> SourceRun:
    source = load_sources()[run["source"]]
    return SourceRun(
        id=run["id"],
        source=run["source"],
        title=source.title,
        publisher=source.publisher,
        url=source.page,
        licence=source.licence,
        fetched_at=datetime.fromisoformat(run["finished_at"]),
        file_hash=(run["files"][0]["sha256"] if run["files"] else ""),
        row_count=row_count,
        status="ok" if run["status"] in ("ok", "unchanged") else "failed",
    )


FORM_NOTE = re.compile(r"\s*\((?:šifr[ae]|za)\b[^()]*\)\s*$", re.IGNORECASE)


def clean_label(label: str) -> str:
    """Drop MinFin's form notes: "Prihodi od poreza (šifre 611+612+613)" -> "Prihodi od poreza"."""
    return FORM_NOTE.sub("", label).strip()


def budget_section(lines: pl.DataFrame, population: int) -> Budget | None:
    if lines.is_empty():
        return None
    year = lines["year"].max()
    lines = lines.filter(pl.col("year") == year)

    def amount(code: str) -> float | None:
        row = lines.filter(pl.col("classification") == "derived", pl.col("code") == code)
        return row["amount_eur"].item() if row.height else None

    revenue, expenditure = amount("X067"), amount("Y034")
    if revenue is None or expenditure is None:
        return None

    def items(rows: pl.DataFrame) -> list[BudgetItem]:
        return [
            BudgetItem(
                code=r["code"],
                label=clean_label(r["label"]),
                amount_eur=round(r["amount_eur"], 2),
                per_resident_eur=round(r["amount_eur"] / population, 2),
            )
            for r in rows.sort("code").iter_rows(named=True)
            if r["amount_eur"]
        ]

    revenue_types = lines.filter(
        pl.col("classification") == "economic",
        pl.col("level") == 2,
        pl.col("code").str.starts_with("6") | pl.col("code").str.starts_with("7"),
    )
    functions = lines.filter(pl.col("classification") == "function", pl.col("level") == 2)
    return Budget(
        year=year,
        period="FY",
        revenue_total_eur=round(revenue, 2),
        expenditure_total_eur=round(expenditure, 2),
        revenue_per_resident_eur=round(revenue / population, 2),
        expenditure_per_resident_eur=round(expenditure / population, 2),
        revenue_by_type=items(revenue_types),
        expenditure_by_function=items(functions),
        source_run_id=lines["source_run_id"][0],
    )


def peers_section(peers: pl.DataFrame, dzs_code: str) -> Peers | None:
    own = peers.filter(pl.col("dzs_code") == dzs_code)
    if own.is_empty():
        return None
    latest = own.sort("year").row(-1, named=True)
    members = peers.filter(pl.col("year") == latest["year"], pl.col("group") == latest["group"])
    return Peers(
        year=latest["year"],
        members=[
            PeerMember(
                slug=m["slug"],
                name=m["name"],
                population=m["population"],
                revenue_per_resident_eur=m["revenue_per_resident_eur"],
                expenditure_per_resident_eur=m["expenditure_per_resident_eur"],
            )
            for m in members.sort("name").iter_rows(named=True)
        ],
        ranks=[
            Rank(metric=CONTRACT_METRIC_NAMES[m], rank=latest[f"rank_{m}"], of=latest["group_size"])
            for m in METRICS
        ],
    )


def procurement_section(contracts: pl.DataFrame) -> Procurement | None:
    if contracts.is_empty():
        return None
    dated = contracts.filter(pl.col("signed_on").is_not_null())
    recent = dated.sort("signed_on", descending=True).head(RECENT_AWARDS)
    suppliers = (
        contracts.with_columns(key=pl.coalesce("supplier_oib", "supplier_name"))
        .group_by("key")
        .agg(
            pl.col("supplier_name").first(),
            pl.col("supplier_oib").first(),
            pl.len().alias("contracts"),
            pl.col("value_eur").sum().alias("total"),
        )
        .sort("total", "supplier_name", descending=[True, False])
        .head(TOP_SUPPLIERS)
    )
    return Procurement(
        data_from=dated["signed_on"].min(),
        data_to=dated["signed_on"].max(),
        contract_count=contracts.height,
        total_value_eur=round(contracts["value_eur"].sum(), 2),
        recent_awards=[
            ContractAward(
                contract_id=r["contract_key"],
                subject=r["subject"] or "",
                supplier_name=r["supplier_name"] or "",
                supplier_oib=r["supplier_oib"],
                cpv=r["cpv"],
                value_eur=None if r["value_eur"] is None else round(r["value_eur"], 2),
                signed_on=r["signed_on"],
            )
            for r in recent.iter_rows(named=True)
        ],
        top_suppliers=[
            SupplierTotal(
                name=s["supplier_name"] or "",
                oib=s["supplier_oib"],
                contracts=s["contracts"],
                total_eur=round(s["total"], 2),
            )
            for s in suppliers.iter_rows(named=True)
        ],
        source_run_ids=sorted(contracts["source_run_id"].unique().to_list()),
    )


def payments_section(payments: pl.DataFrame, as_of: datetime) -> Payments | None:
    """12 calendar months up to the newest complete published month.

    The month in progress is left out: it is still being published (by the 20th of
    the next month) and would look like a drop in spending. A month the publisher
    skipped stays a gap in ``months`` instead of pulling in an older month.
    """
    payments = payments.filter(pl.col("month") < f"{as_of:%Y-%m}")
    if payments.is_empty():
        return None
    year, month = map(int, payments["month"].max().split("-"))
    first_year, first_month = divmod(year * 12 + month - PAYMENT_MONTHS, 12)
    recent = payments.filter(pl.col("month") >= f"{first_year}-{first_month + 1:02d}")
    by_month = recent.group_by("month").agg(pl.col("amount_eur").sum()).sort("month")
    categories = (
        recent.group_by("economic_label")
        .agg(pl.col("amount_eur").sum())
        .sort("amount_eur", descending=True)
        .head(TOP_CATEGORIES)
    )
    recipients = (
        recent.filter(~pl.col("natural_person"), pl.col("recipient_name").is_not_null())
        .group_by(pl.coalesce("recipient_oib", "recipient_name").alias("key"))
        .agg(
            pl.col("recipient_name").first(),
            pl.col("recipient_oib").first(),
            pl.len().alias("payments"),
            pl.col("amount_eur").sum(),
        )
        .sort("amount_eur", descending=True)
        .head(TOP_RECIPIENTS)
    )
    return Payments(
        months=[MonthlyTotal(month=m, total_eur=round(t, 2)) for m, t in by_month.iter_rows()],
        by_category=[
            PaymentCategory(label=label or "Ostalo", amount_eur=round(amount, 2))
            for label, amount in categories.iter_rows()
        ],
        top_recipients=[
            PaymentRecipient(
                name=r["recipient_name"],
                oib=r["recipient_oib"],
                payments=r["payments"],
                amount_eur=round(r["amount_eur"], 2),
            )
            for r in recipients.iter_rows(named=True)
        ],
        source_run_id=recent["source_run_id"][0],
    )


def facilities_section(facilities: pl.DataFrame) -> list[Facility]:
    return [
        Facility(
            type=f["type"],
            name=f["name"],
            address=f["address"],
            lat=round(f["lat"], 6),
            lon=round(f["lon"], 6),
            source_run_id=f["source_run_id"],
        )
        for f in facilities.sort("type", "name").iter_rows(named=True)
    ]


def _rows(table: pl.DataFrame | None, dzs_code: str) -> pl.DataFrame:
    if table is None:
        return pl.DataFrame()
    return table.filter(pl.col("dzs_code") == dzs_code)


def build_pages(generated_at: datetime | None = None) -> tuple[list[MunicipalityPage], dict]:
    """Pages for every unit in the master table, plus the fetch runs they cite."""
    generated_at = generated_at or datetime.now(UTC)
    master = pl.read_csv(config_path("municipalities.csv"), infer_schema_length=0)
    population = read_published("population")
    budget_lines = read_published("budget_line")
    tables = {t: read_published(t) for t in ("contract", "payment", "facility")}
    if population is None or budget_lines is None:
        raise RuntimeError("population and budget_line must be published before export")

    runs = read_runs(repo_root() / "data" / "raw" / "source_runs.jsonl")
    row_counts: dict[str, int] = {}
    for table in [population, budget_lines, *[t for t in tables.values() if t is not None]]:
        for run_id, count in table.group_by("source_run_id").len().iter_rows():
            row_counts[run_id] = row_counts.get(run_id, 0) + count

    peers = peer_table(master, population, budget_lines)
    latest_pop = population.sort("year", pl.col("kind") == "estimate").group_by("dzs_code").last()

    pages = []
    for unit in master.iter_rows(named=True):
        code = unit["dzs_code"]
        pop = latest_pop.filter(pl.col("dzs_code") == code).row(0, named=True)
        unit_rows = {name: _rows(t, code) for name, t in tables.items()}
        budget = budget_section(_rows(budget_lines, code), pop["total"])
        procurement = (
            procurement_section(unit_rows["contract"]) if unit_rows["contract"].height else None
        )
        payments = (
            payments_section(unit_rows["payment"], generated_at)
            if unit_rows["payment"].height
            else None
        )
        facilities = (
            facilities_section(unit_rows["facility"]) if unit_rows["facility"].height else []
        )

        cited = {pop["source_run_id"]}
        if budget:
            cited.add(budget.source_run_id)
        if procurement:
            cited.update(procurement.source_run_ids)
        if payments:
            cited.add(payments.source_run_id)
        cited.update(f.source_run_id for f in facilities)
        boundaries_run = latest_run(runs, "dgu_boundaries")
        if boundaries_run:
            cited.add(boundaries_run)

        own_peers = peers.filter(pl.col("dzs_code") == code)
        band = own_peers.sort("year")["band"][-1] if own_peers.height else band_for(pop["total"])
        pages.append(
            MunicipalityPage(
                slug=unit["slug"],
                oib=unit["oib"],
                rkp=unit["rkp"],
                dzs_code=code,
                lau_code=unit["lau_code"],
                name=unit["name"],
                type=unit["type"],
                county=unit["county"],
                population=Population(year=pop["year"], total=pop["total"]),
                band=band,
                budget=budget,
                peers=peers_section(peers, code),
                procurement=procurement,
                payments=payments,
                facilities=facilities,
                sources=[
                    source_run(runs[r], row_counts.get(r, 0)) for r in sorted(cited) if r in runs
                ],
                generated_at=generated_at,
            )
        )
    return pages, runs


def latest_run(runs: dict, source: str) -> str | None:
    ok = [r for r in runs.values() if r["source"] == source and r["status"] in ("ok", "unchanged")]
    return max(ok, key=lambda r: r["finished_at"])["id"] if ok else None


def search_index(pages: list[MunicipalityPage], generated_at: datetime) -> SearchIndex:
    postcodes = pl.read_csv(config_path("postcodes.csv"), infer_schema_length=0)
    by_code = postcodes.group_by("dzs_code").agg(pl.col("postcode").unique().sort())
    codes = {c: list(p) for c, p in by_code.iter_rows()}
    return SearchIndex(
        generated_at=generated_at,
        entries=[
            SearchEntry(
                slug=p.slug,
                name=p.name,
                name_ascii=ascii_fold(p.name),
                type=p.type,
                county=p.county,
                population=p.population.total,
                postcodes=codes.get(p.dzs_code, []),
                has_data=p.budget is not None,
            )
            for p in sorted(pages, key=lambda p: p.name)
        ],
    )


def source_status(runs: dict, generated_at: datetime) -> SourceStatus:
    latest = {}
    for run in runs.values():
        if run["source"] in load_sources():
            latest[run["source"]] = run  # the log is in time order: last one wins
    return SourceStatus(
        generated_at=generated_at,
        runs=[source_run(r, 0) for _, r in sorted(latest.items())],
    )


def _write(path: Path, model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(model.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def export(out_dir: Path | None = None) -> dict[str, int]:
    out_dir = out_dir or repo_root() / "web" / "public" / "data"
    generated_at = datetime.now(UTC)
    pages, runs = build_pages(generated_at)

    page_dir = out_dir / "m"
    if page_dir.exists():
        for old in page_dir.glob("*.json"):
            old.unlink()  # a unit that left the scope must not keep a stale page
    for page in pages:
        _write(page_dir / f"{page.slug}.json", page)
    _write(out_dir / "search-index.json", search_index(pages, generated_at))
    _write(out_dir / "sources.json", source_status(runs, generated_at))

    with_data = {p.dzs_code for p in pages if p.budget is not None}
    write_boundaries(
        load_sources()["dgu_boundaries"].path,
        pl.read_csv(config_path("municipalities.csv"), infer_schema_length=0),
        out_dir / "boundaries.geojson",
        has_data=with_data,
    )
    return {
        "pages": len(pages),
        "with_budget": len(with_data),
        "with_procurement": sum(p.procurement is not None for p in pages),
        "with_payments": sum(p.payments is not None for p in pages),
        "facilities": sum(len(p.facilities) for p in pages),
    }
