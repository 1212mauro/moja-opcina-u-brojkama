"""Population per municipality (task C4): census 2021 and DZS yearly estimates.

Both DZS tables name municipalities without codes, so names are matched to the
master table with ``name_key``; any unmatched name in the county is an error.
"""

import re
from pathlib import Path

import polars as pl

from opcina_pipeline.config import Scope, config_path, load_scope, load_sources
from opcina_pipeline.tables import conform, latest_run_id
from opcina_pipeline.text import name_key

CENSUS_YEAR = 2021
# Header prefixes of the columns read by position (headers contain line breaks).
CENSUS_COLUMNS = {0: "Županija", 4: "Grad/općina", 5: "Tip naselja", 7: "Spol", 9: "Ukupno"}
ESTIMATE_COLUMNS = {0: "Županije", 2: "Gradovi/općine"}
ESTIMATE_YEAR = re.compile(r"^(\d{4})\.$")  # "2025." (later blocks repeat as "2025._1")


def _check_columns(df: pl.DataFrame, expected: dict[int, str], table: str) -> list[str]:
    for index, prefix in expected.items():
        if not df.columns[index].startswith(prefix):
            raise ValueError(
                f"{table}: column {index} is {df.columns[index]!r}, expected {prefix}…"
            )
    return [df.columns[i] for i in expected]


def _codes(names: pl.Series, master: pl.DataFrame, table: str) -> pl.Series:
    code_by_name = {name_key(n): c for n, c in master.select("name", "dzs_code").iter_rows()}
    unknown = sorted({n for n in names if name_key(n) not in code_by_name})
    if unknown:
        raise ValueError(f"{table}: municipalities missing from the master table: {unknown}")
    return names.map_elements(lambda n: code_by_name[name_key(n)], return_dtype=pl.Utf8)


def parse_census(df: pl.DataFrame, master: pl.DataFrame, scope: Scope) -> pl.DataFrame:
    """Sheet "20." of the census by grad/općina: one total per municipality."""
    county, municipality, settlement_type, sex, total = _check_columns(df, CENSUS_COLUMNS, "census")
    rows = df.filter(
        pl.col(county) == scope.census_name,
        pl.col(municipality).is_not_null(),
        pl.col(settlement_type) == "Ukupno",
        pl.col(sex) == "sv.",
    )
    return pl.DataFrame(
        {
            "dzs_code": _codes(rows[municipality], master, "census"),
            "year": CENSUS_YEAR,
            "kind": "census",
            "total": rows[total].str.replace_all(r"\D", "").cast(pl.Int64),
        }
    )


def parse_estimates(df: pl.DataFrame, master: pl.DataFrame, scope: Scope) -> pl.DataFrame:
    """Sheet "Tab-2." of "Gradovi u statistici": 31 December estimates per year."""
    county, municipality = _check_columns(df, ESTIMATE_COLUMNS, "estimates")
    years = {c: int(m.group(1)) for c in df.columns if (m := ESTIMATE_YEAR.match(c))}
    if not years:
        raise ValueError("estimates: no year columns like '2025.'")
    rows = df.filter(pl.col(county) == scope.census_name, pl.col(municipality).is_not_null())
    wide = rows.select(
        _codes(rows[municipality], master, "estimates").alias("dzs_code"),
        *[pl.col(c).alias(str(y)) for c, y in years.items()],
    )
    return (
        wide.unpivot(index="dzs_code", variable_name="year", value_name="total")
        # DZS writes "-" for zero; an empty cell is a year without an estimate.
        .with_columns(pl.col("total").str.replace("^-$", "0"))
        .filter(pl.col("total").is_not_null())
        .select(
            "dzs_code",
            pl.col("year").cast(pl.Int32),
            pl.lit("estimate").alias("kind"),
            pl.col("total").str.replace_all(r"\D", "").cast(pl.Int64),
        )
    )


def _read(path: Path, sheet: str) -> pl.DataFrame:
    return pl.read_excel(
        path, sheet_name=sheet, infer_schema_length=0, read_options={"header_row": 7}
    )


def build_population() -> pl.DataFrame:
    sources = load_sources()
    master = pl.read_csv(config_path("municipalities.csv"), infer_schema_length=0)
    scope = load_scope()
    census = parse_census(_read(sources["dzs_population"].path, "20."), master, scope)
    estimates = parse_estimates(_read(sources["dzs_estimates"].path, "Tab-2."), master, scope)
    df = pl.concat(
        [
            census.with_columns(source_run_id=pl.lit(latest_run_id("dzs_population"))),
            estimates.with_columns(source_run_id=pl.lit(latest_run_id("dzs_estimates"))),
        ]
    )
    missing = set(master["dzs_code"]) - set(census["dzs_code"])
    if missing:
        raise ValueError(f"census has no total for {sorted(missing)}")
    return conform(df, "population").sort("dzs_code", "kind", "year")


def latest_population(population: pl.DataFrame) -> pl.DataFrame:
    """Newest figure per municipality, estimate over census: ``dzs_code, year, total``."""
    return (
        population.sort("year", pl.col("kind") == "estimate")
        .group_by("dzs_code")
        .last()
        .select("dzs_code", "year", "total")
    )
