"""Municipality master table (task B2): one row per city/municipality.

Joins the MinFin RKP register (OIB, RKP number) with the Eurostat LAU list
(DZS/LAU code, proper-case name). The register's "Statistička oznaka grada/općine"
is the DZS code without its check digit ("472" <-> "04723"), which gives a code
join instead of a fragile name join; names are compared only as a cross-check.
"""

from pathlib import Path

import polars as pl

from opcina_pipeline.config import Scope
from opcina_pipeline.text import name_key, slugify

UNIT_PREFIXES = {"GRAD ": "grad", "OPĆINA ": "opcina"}
LOCAL_BUDGET_LEVEL = "22"

MASTER_COLUMNS = [
    "slug",
    "name",
    "official_name",
    "type",
    "oib",
    "rkp",
    "dzs_code",
    "lau_code",
    "county",
    "pilot",
]


def read_register(path: Path) -> pl.DataFrame:
    df = pl.read_excel(path, sheet_name="RKP registar", infer_schema_length=0)
    return df.select(
        pl.col("RKP broj").alias("rkp"),
        pl.col("Naziv subjekta").alias("official_name"),
        pl.col("Osobni identifikacijski broj").alias("oib"),
        pl.col("Statistička oznaka županije").alias("county_label"),
        pl.col("Statistička oznaka grada/općine").alias("city_label"),
        pl.col("Razina financijskog izvještavanja").alias("level_label"),
        pl.col("RKP broj nadležne JLP(R)S").alias("parent_rkp"),
    )


def read_lau(path: Path) -> pl.DataFrame:
    df = pl.read_excel(path, sheet_name="HR", infer_schema_length=0)
    return df.select(
        pl.col("NUTS3").alias("nuts3"),
        pl.col("LAU CODE").alias("dzs_code"),
        pl.col("LAU NAME NATIONAL").alias("name"),
    )


def _label_code(column: str) -> pl.Expr:
    """ "5 - VARAŽDINSKA" -> "5"."""
    return pl.col(column).str.split(" - ").list.first().str.strip_chars()


def build_master(register: pl.DataFrame, lau: pl.DataFrame, scope: Scope) -> pl.DataFrame:
    units = register.filter(
        _label_code("level_label") == LOCAL_BUDGET_LEVEL,
        _label_code("county_label") == scope.register_code,
        pl.col("official_name").str.starts_with("GRAD ")
        | pl.col("official_name").str.starts_with("OPĆINA "),
    ).with_columns(
        city_code=_label_code("city_label").str.zfill(4),
        rkp=pl.col("rkp").str.zfill(5),
        type=pl.when(pl.col("official_name").str.starts_with("GRAD "))
        .then(pl.lit("grad"))
        .otherwise(pl.lit("opcina")),
    )
    codes = lau.filter(pl.col("nuts3") == scope.nuts3).with_columns(
        city_code=pl.col("dzs_code").str.slice(0, 4)
    )

    master = units.join(codes, on="city_code", how="full", coalesce=True)
    unmatched = master.filter(pl.col("oib").is_null() | pl.col("dzs_code").is_null())
    if unmatched.height:
        raise ValueError(f"register and LAU list disagree on these units:\n{unmatched}")

    mismatched = [
        (official, name)
        for official, name in master.select("official_name", "name").iter_rows()
        if name_key(_strip_prefix(official)) != name_key(name)
    ]
    if mismatched:
        raise ValueError(f"code join paired units with different names: {mismatched}")

    master = master.with_columns(
        slug=pl.col("name").map_elements(slugify, return_dtype=pl.Utf8),
        lau_code=pl.lit("HR_") + pl.col("dzs_code"),
        county=pl.lit(scope.county_name),
        pilot=pl.col("dzs_code").is_in(scope.pilot_lau_codes),
    )
    if master["slug"].n_unique() != master.height:
        raise ValueError("slugs are not unique")
    missing_pilots = set(scope.pilot_lau_codes) - set(master["dzs_code"])
    if missing_pilots:
        raise ValueError(f"pilot LAU codes not found in scope: {sorted(missing_pilots)}")

    return master.select(MASTER_COLUMNS).sort("slug")


def _strip_prefix(official_name: str) -> str:
    for prefix in UNIT_PREFIXES:
        if official_name.startswith(prefix):
            return official_name.removeprefix(prefix)
    return official_name
