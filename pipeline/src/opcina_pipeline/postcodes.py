"""Postcode -> municipality lookup (task B9).

Hrvatska pošta lists postcode per settlement (naselje) but not the municipality,
so settlements are matched by name to the DZS census settlement list, which
does name the municipality. Names that are ambiguous within the county, or that
Pošta spells differently, are resolved in ``config/postcode_overrides.csv``.
"""

import csv
from pathlib import Path

import polars as pl

from opcina_pipeline.config import Scope, config_path
from opcina_pipeline.text import name_key

OVERRIDES_CSV = "postcode_overrides.csv"
# Expected header prefixes of the census columns read by position.
CENSUS_COLUMNS = {0: "Županija", 4: "Grad/općina", 5: "Naselje", 6: "Spol"}


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
    for index, prefix in CENSUS_COLUMNS.items():
        if not df.columns[index].startswith(prefix):
            raise ValueError(f"census column {index} is {df.columns[index]!r}, expected {prefix}…")
    county, municipality, settlement, sex = (df.columns[i] for i in CENSUS_COLUMNS)
    return df.filter(pl.col(settlement).is_not_null(), pl.col(sex) == "sv.").select(
        pl.col(county).alias("county"),
        pl.col(municipality).alias("municipality"),
        pl.col(settlement).alias("settlement"),
    )


def read_overrides(path: Path | None = None) -> dict[tuple[str, str], str]:
    with (path or config_path(OVERRIDES_CSV)).open(encoding="utf-8", newline="") as f:
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

    unknown_overrides = {k: c for k, c in overrides.items() if c not in code_by_name.values()}
    if unknown_overrides:
        raise ValueError(f"{OVERRIDES_CSV} uses codes not in the master table: {unknown_overrides}")

    census: dict[str, set[str]] = {}
    unknown_municipalities = set()
    for municipality, settlement in (
        settlements.filter(pl.col("county") == scope.census_name)
        .select("municipality", "settlement")
        .iter_rows()
    ):
        code = code_by_name.get(name_key(municipality))
        if code is None:
            unknown_municipalities.add(municipality)
            continue
        census.setdefault(name_key(settlement), set()).add(code)
    if unknown_municipalities:
        raise ValueError(
            f"census municipalities missing from the master table: {sorted(unknown_municipalities)}"
        )

    rows, problems, used_overrides = [], [], set()
    for postcode, office, settlement in (
        posta.filter(pl.col("county") == scope.postal_name)
        .select("postcode", "post_office", "settlement")
        .iter_rows()
    ):
        code = overrides.get((postcode, settlement))
        if code is not None:
            used_overrides.add((postcode, settlement))
        else:
            candidates = census.get(name_key(settlement), set())
            if len(candidates) == 1:
                code = next(iter(candidates))
            else:
                problems.append((postcode, settlement, sorted(candidates)))
                continue
        rows.append((postcode, office, settlement, code))

    if problems:
        listing = "\n".join(f"  {p} {s}: candidates {c}" for p, s, c in problems)
        raise ValueError(f"add these to {OVERRIDES_CSV}:\n{listing}")
    stale = set(overrides) - used_overrides
    if stale:
        raise ValueError(f"{OVERRIDES_CSV} has entries matching no Pošta row: {sorted(stale)}")

    return pl.DataFrame(
        rows, schema=["postcode", "post_office", "settlement", "dzs_code"], orient="row"
    ).sort("postcode", "settlement")
