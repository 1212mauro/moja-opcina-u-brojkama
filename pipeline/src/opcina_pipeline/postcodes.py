"""Postcode -> municipality lookup (task B9).

Hrvatska pošta lists postcode per settlement (naselje) but not the municipality,
so settlements are matched by name to the DZS census settlement list, which
does name the municipality. Names that are ambiguous within the county, or that
Pošta spells differently, are resolved in ``config/postcode_overrides.csv``.
"""

import csv
from pathlib import Path

import polars as pl

from opcina_pipeline.config import CONFIG_DIR, Scope
from opcina_pipeline.text import name_key

OVERRIDES_PATH = CONFIG_DIR / "postcode_overrides.csv"


def read_posta(path: Path) -> pl.DataFrame:
    df = pl.read_excel(path, infer_schema_length=0)
    return df.select(
        pl.col("BrojPu").alias("postcode"),
        pl.col("NazivPu").alias("post_office"),
        pl.col("Naselje").alias("settlement"),
        pl.col("Zupanija").alias("county"),
    )


def read_census_settlements(path: Path) -> pl.DataFrame:
    """Settlement rows of DZS "stanovništvo po naseljima", sheet 1.

    Headers contain line breaks and trailing spaces, so columns are taken by position.
    Municipality subtotal rows have no settlement and are dropped.
    """
    df = pl.read_excel(path, sheet_name="1.", infer_schema_length=0, read_options={"header_row": 7})
    county, municipality, settlement, sex = (df.columns[i] for i in (0, 4, 5, 6))
    return df.filter(pl.col(settlement).is_not_null(), pl.col(sex) == "sv.").select(
        pl.col(county).alias("county"),
        pl.col(municipality).alias("municipality"),
        pl.col(settlement).alias("settlement"),
    )


def read_overrides(path: Path = OVERRIDES_PATH) -> dict[tuple[str, str], str]:
    with path.open(encoding="utf-8", newline="") as f:
        return {(r["postcode"], r["settlement"]): r["dzs_code"] for r in csv.DictReader(f)}


def build_postcodes(
    posta: pl.DataFrame,
    settlements: pl.DataFrame,
    master: pl.DataFrame,
    scope: Scope,
    overrides: dict[tuple[str, str], str],
) -> pl.DataFrame:
    """One row per (postcode, settlement) in scope, with the settlement's DZS municipality code."""
    code_by_name = {name_key(n): c for n, c in master.select("name", "dzs_code").iter_rows()}

    census: dict[str, set[str]] = {}
    for municipality, settlement in (
        settlements.filter(pl.col("county") == scope.census_name)
        .select("municipality", "settlement")
        .iter_rows()
    ):
        census.setdefault(name_key(settlement), set()).add(code_by_name[name_key(municipality)])

    rows, problems = [], []
    for postcode, office, settlement in (
        posta.filter(pl.col("county") == scope.postal_name)
        .select("postcode", "post_office", "settlement")
        .iter_rows()
    ):
        code = overrides.get((postcode, settlement))
        if code is None:
            candidates = census.get(name_key(settlement), set())
            if len(candidates) == 1:
                code = next(iter(candidates))
            else:
                problems.append((postcode, settlement, sorted(candidates)))
                continue
        rows.append((postcode, office, settlement, code))

    if problems:
        listing = "\n".join(f"  {p} {s}: candidates {c}" for p, s, c in problems)
        raise ValueError(f"add these to {OVERRIDES_PATH.name}:\n{listing}")

    return pl.DataFrame(
        rows, schema=["postcode", "post_office", "settlement", "dzs_code"], orient="row"
    ).sort("postcode", "settlement")
