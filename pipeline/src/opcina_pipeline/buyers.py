"""Public buyers attributed to each municipality (SPEC matching rule 1).

A municipality buys through its own OIB and through its budget users
(kindergartens, libraries, theatres), which the MinFin RKP register links to
their parent unit. Level-31 users (schools, fire brigades financed for
decentralised functions) are left out: they belong to the county or state budget.
"""

from pathlib import Path

import polars as pl

from opcina_pipeline.master import read_register

BUDGET_USER_LEVEL = "21"


def scope_buyers(master: pl.DataFrame, register: pl.DataFrame) -> pl.DataFrame:
    """One row per buyer OIB: ``oib, name, dzs_code, kind`` (``unit`` or ``budget_user``)."""
    units = master.select(
        "oib",
        pl.col("official_name").alias("name"),
        "dzs_code",
        pl.lit("unit").alias("kind"),
    )
    users = (
        register.filter(
            pl.col("level_label").str.split(" - ").list.first().str.strip_chars()
            == BUDGET_USER_LEVEL,
            pl.col("parent_rkp").is_not_null(),
        )
        .with_columns(parent_rkp=pl.col("parent_rkp").str.zfill(5))
        .join(master.select("rkp", "dzs_code"), left_on="parent_rkp", right_on="rkp")
        .select(
            "oib",
            pl.col("official_name").alias("name"),
            "dzs_code",
            pl.lit("budget_user").alias("kind"),
        )
    )
    # A newly registered budget user can lack an OIB; it cannot be matched to anything yet.
    return (
        pl.concat([units, users])
        .filter(pl.col("oib").str.strip_chars().str.len_chars() > 0)
        .unique("oib", keep="first")
        .sort("dzs_code", "kind", "name")
    )


def read_scope_buyers(master: pl.DataFrame, register_path: Path) -> pl.DataFrame:
    return scope_buyers(master, read_register(register_path))
