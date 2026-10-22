"""Budget execution per municipality (task C2): MinFin PR-RAS and RAS-funkcijski.

The county workbook has one sheet per unit (named like ``official_name`` in the master
table) plus aggregate sheets. Every sheet has the same layout, described in
``config/budget_layout.toml``: a header row, an economic section (accounts mixed with
derived positions such as ``X067`` total revenue) and a COFOG function section.

Codes are taken from "Pozicija u obrascu", which is unique per sheet, and read as text:
integers become their digits ("611"), COFOG keeps its leading zeros ("011"), and the one
position Excel stored as a number (96.97, meaning accounts 96+97) is mapped back to
"96,97" by an alias in the layout file. A repeated position is an error, not something
to pick from. Empty amounts are dropped (an account that did not exist that year);
zeros are kept.
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from opcina_pipeline.config import config_path, load_sources
from opcina_pipeline.tables import conform, latest_run_id

SOURCE = "minfin_budget"
LAYOUT_FILE = "budget_layout.toml"

# Positions the reconciliation checks rely on.
TOTAL_REVENUE = "X067"  # 6 + 7
TOTAL_EXPENDITURE = "Y034"  # Z005 + 4 (operating expenditure + non-financial assets)
COFOG_TOTAL = "R1"  # 01 + ... + 10
OWN_USERS_TRANSFERS = "367"  # transfers to the unit's own budget users, not in COFOG
TOLERANCE_EUR = 1.0  # amounts are in cents; sums of floats drift a little


@dataclass(frozen=True)
class Layout:
    search_rows: int
    label_column: str
    key_column: str
    year_pattern: re.Pattern
    currency_label: str
    currency: str
    period_label: str
    period_value: str
    period: str
    economic_heading: str
    function_heading: str
    economic_pattern: str
    function_pattern: str
    aliases: dict[str, str]
    skip_sheets: frozenset[str]


def load_layout(path: Path | None = None) -> Layout:
    raw = tomllib.loads((path or config_path(LAYOUT_FILE)).read_text(encoding="utf-8"))
    header, meta, sections, codes = raw["header"], raw["metadata"], raw["sections"], raw["codes"]
    return Layout(
        search_rows=header["search_rows"],
        label_column=header["label_column"],
        key_column=header["key_column"],
        year_pattern=re.compile(header["year_column_pattern"]),
        currency_label=meta["currency_label"],
        currency=meta["currency"],
        period_label=meta["period_label"],
        period_value=meta["period_value"],
        period=meta["period"],
        economic_heading=sections["economic_heading"],
        function_heading=sections["function_heading"],
        economic_pattern=codes["economic_pattern"],
        function_pattern=codes["function_pattern"],
        aliases=dict(codes.get("aliases", {})),
        skip_sheets=frozenset(name.strip() for name in raw["sheets"]["skip"]),
    )


def read_workbook(path: Path) -> dict[str, pl.DataFrame]:
    """Every sheet as a headerless grid of text cells (``column_0``, ``column_1``, ...)."""
    return pl.read_excel(path, sheet_id=0, has_header=False, infer_schema_length=0)


def _text(value: str | None) -> str:
    return (value or "").strip()


def _find_header(grid: pl.DataFrame, layout: Layout, sheet: str) -> tuple[int, list[str]]:
    for index, row in enumerate(grid.head(layout.search_rows).iter_rows()):
        cells = [_text(cell) for cell in row]
        if layout.key_column in cells and layout.label_column in cells:
            return index, cells
    raise ValueError(
        f"{sheet}: no header row with {layout.key_column!r} and {layout.label_column!r} "
        f"in the first {layout.search_rows} rows"
    )


def _metadata(grid: pl.DataFrame, header_index: int) -> dict[str, str]:
    """Label/value pairs above the header: ``{"Valuta": "Euro", ...}``."""
    pairs = {}
    for row in grid.head(header_index).iter_rows():
        cells = [_text(cell) for cell in row]
        for label, value in zip(cells, cells[1:], strict=False):
            if label.endswith(":") and value:
                pairs[label.rstrip(":").strip()] = value
    return pairs


def _check_metadata(grid: pl.DataFrame, header_index: int, layout: Layout, sheet: str) -> None:
    meta = _metadata(grid, header_index)
    expected = {layout.currency_label: layout.currency, layout.period_label: layout.period_value}
    for label, value in expected.items():
        if meta.get(label) != value:
            raise ValueError(f"{sheet}: {label!r} is {meta.get(label)!r}, expected {value!r}")


def _heading_row(grid: pl.DataFrame, heading: str, sheet: str) -> int:
    marks = pl.any_horizontal(
        pl.col(c).str.strip_chars().str.starts_with(heading).fill_null(False)
        for c in grid.columns[:3]
    )
    rows = grid.with_row_index("row").filter(marks)["row"].to_list()
    if len(rows) != 1:
        raise ValueError(f"{sheet}: expected one heading {heading!r}, found {len(rows)}")
    return rows[0]


def parse_sheet(grid: pl.DataFrame, layout: Layout, sheet: str = "sheet") -> pl.DataFrame:
    """One unit's sheet -> rows of (year, period, classification, code, level, label, amount)."""
    header_index, header = _find_header(grid, layout, sheet)
    _check_metadata(grid, header_index, layout, sheet)
    columns = grid.columns
    years = {
        columns[i]: int(match.group(1))
        for i, name in enumerate(header)
        if (match := layout.year_pattern.match(name))
    }
    if not years:
        raise ValueError(f"{sheet}: no year columns matching {layout.year_pattern.pattern!r}")
    key = columns[header.index(layout.key_column)]
    label = columns[header.index(layout.label_column)]

    economic_row = _heading_row(grid, layout.economic_heading, sheet)
    function_row = _heading_row(grid, layout.function_heading, sheet)
    if not header_index < economic_row < function_row:
        raise ValueError(f"{sheet}: expected header, economic heading, function heading in order")

    row = pl.int_range(pl.len())
    code = pl.col(key).str.strip_chars().replace(layout.aliases)
    rows = (
        grid.with_columns(
            section=pl.when(row > function_row)
            .then(pl.lit("function"))
            .when(row > economic_row)
            .then(pl.lit("economic")),
            code=pl.when(code != "").then(code),
        )
        .filter(pl.col("section").is_not_null(), pl.col("code").is_not_null())
        .with_columns(
            classification=pl.when(
                (pl.col("section") == "economic")
                & pl.col("code").str.contains(layout.economic_pattern)
            )
            .then(pl.lit("economic"))
            .when(
                (pl.col("section") == "function")
                & pl.col("code").str.contains(layout.function_pattern)
            )
            .then(pl.lit("function"))
            .otherwise(pl.lit("derived"))
        )
    )
    repeated = rows.filter(pl.col("code").is_duplicated())["code"].unique().sort().to_list()
    if repeated:
        raise ValueError(f"{sheet}: positions appear more than once: {repeated}")

    long = rows.select(
        "classification",
        "code",
        pl.when(pl.col("classification") == "derived")
        .then(0)
        .otherwise(pl.col("code").str.len_chars())
        .alias("level"),
        pl.col(label).str.strip_chars().alias("label"),
        *[pl.col(column).alias(str(year)) for column, year in years.items()],
    ).unpivot(
        index=["classification", "code", "level", "label"],
        variable_name="year",
        value_name="text",
    )
    long = long.with_columns(
        amount_eur=pl.col("text").str.strip_chars().cast(pl.Float64, strict=False)
    )
    bad = long.filter(pl.col("amount_eur").is_null() & (pl.col("text").str.strip_chars() != ""))
    if bad.height:
        raise ValueError(f"{sheet}: amounts that are not numbers:\n{bad.head(10)}")
    return long.filter(pl.col("amount_eur").is_not_null()).select(
        pl.col("year").cast(pl.Int32),
        pl.lit(layout.period).alias("period"),
        "classification",
        "code",
        pl.col("level").cast(pl.Int8),
        "label",
        "amount_eur",
    )


def unit_sheets(names: list[str], master: pl.DataFrame, layout: Layout) -> dict[str, str]:
    """Sheet name -> dzs_code for unit sheets; every sheet and every unit must be accounted for."""
    code_by_name = dict(master.select("official_name", "dzs_code").iter_rows())
    units = {name: code_by_name.get(name.strip()) for name in names}
    unknown = [n for n, c in units.items() if c is None and n.strip() not in layout.skip_sheets]
    if unknown:
        raise ValueError(f"budget: sheets that are neither units nor known aggregates: {unknown}")
    found = {name.strip() for name, code in units.items() if code}
    missing = sorted(set(code_by_name) - found)
    if missing:
        raise ValueError(f"budget: units with no sheet in the workbook: {missing}")
    return {name: code for name, code in units.items() if code}


def parse_workbook(
    sheets: dict[str, pl.DataFrame], master: pl.DataFrame, layout: Layout
) -> pl.DataFrame:
    units = unit_sheets(list(sheets), master, layout)
    return pl.concat(
        parse_sheet(sheets[name], layout, name).with_columns(dzs_code=pl.lit(code))
        for name, code in units.items()
    )


def build_budget_lines() -> pl.DataFrame:
    master = pl.read_csv(config_path("municipalities.csv"), infer_schema_length=0)
    sheets = read_workbook(load_sources()[SOURCE].path)
    df = parse_workbook(sheets, master, load_layout())
    check_budget(df)
    return conform(df.with_columns(source_run_id=pl.lit(latest_run_id(SOURCE))), "budget_line")


def reconcile(df: pl.DataFrame) -> pl.DataFrame:
    """Per unit and year, the totals the checks compare (null where a position is absent).

    - ``cofog_vs_r1``: 2-digit COFOG functions minus R1;
    - ``r1_vs_y034_less_367``: R1 minus (Y034 - account 367); COFOG leaves out transfers
      to the unit's own budget users;
    - ``x067_vs_6_plus_7``: X067 minus (accounts 6 + 7).
    """

    def total(condition: pl.Expr) -> pl.Expr:
        return pl.col("amount_eur").filter(condition).sum()

    def position(code: str) -> pl.Expr:
        return pl.col("amount_eur").filter(pl.col("code") == code).first()

    is_economic = pl.col("classification") == "economic"
    totals = df.group_by("dzs_code", "year").agg(
        cofog_sum=total((pl.col("classification") == "function") & (pl.col("level") == 2)),
        r1=position(COFOG_TOTAL),
        y034=position(TOTAL_EXPENDITURE),
        x067=position(TOTAL_REVENUE),
        a367=total(is_economic & (pl.col("code") == OWN_USERS_TRANSFERS)),
        a67=total(is_economic & pl.col("code").is_in(["6", "7"])),
    )
    return totals.with_columns(
        cofog_vs_r1=pl.col("cofog_sum") - pl.col("r1"),
        r1_vs_y034_less_367=pl.col("r1") - (pl.col("y034") - pl.col("a367")),
        x067_vs_6_plus_7=pl.col("x067") - pl.col("a67"),
    ).sort("dzs_code", "year")


CHECKS = ("cofog_vs_r1", "r1_vs_y034_less_367", "x067_vs_6_plus_7")


def check_budget(df: pl.DataFrame, tolerance: float = TOLERANCE_EUR) -> None:
    """Raise if any unit-year's totals differ by more than ``tolerance`` euro.

    All three relations hold for every unit and year of the 2019-2025 file (largest gap
    0.14 EUR), so any failure means the layout changed or the parse is wrong. A check is
    skipped for a unit-year that lacks one of its positions.
    """
    totals = reconcile(df)
    errors = [
        f"{check}: {row['dzs_code']} {row['year']} off by {row[check]:,.2f} EUR"
        for check in CHECKS
        for row in totals.filter(pl.col(check).abs() > tolerance).iter_rows(named=True)
    ]
    if errors:
        raise ValueError("budget totals do not reconcile:\n" + "\n".join(errors))
