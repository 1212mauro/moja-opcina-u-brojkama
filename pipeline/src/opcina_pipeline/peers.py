"""Peer groups and ranks (task C9, SPEC matching rule 3).

Peers are fixed per year: same county, same unit type (grad / općina) and the same
population band. Per-resident figures use that year's population: the DZS
estimate for the year, else the census, else the nearest earlier figure.
Rank 1 is the highest value in the group.
"""

import polars as pl

# Upper bounds (exclusive) of the four bands in SPEC.md.
BANDS = [(3_000, "under_3k"), (10_000, "3k_10k"), (35_000, "10k_35k"), (None, "over_35k")]

# Derived budget positions used for the headline per-resident figures.
REVENUE_CODE = "X067"  # Prihodi i primici ukupno
EXPENDITURE_CODE = "Y034"  # Rashodi i izdaci ukupno
METRICS = ["revenue_per_resident_eur", "expenditure_per_resident_eur"]


def band_for(population: int) -> str:
    for upper, band in BANDS:
        if upper is None or population < upper:
            return band
    raise AssertionError("unreachable")


def population_by_year(population: pl.DataFrame, years: list[int]) -> pl.DataFrame:
    """``dzs_code, year, population`` for each requested year (see module docstring)."""
    ranked = population.with_columns(
        # Prefer an estimate over the census for the same year.
        preference=pl.when(pl.col("kind") == "estimate").then(1).otherwise(0)
    )
    rows = []
    for year in years:
        available = ranked.filter(pl.col("year") <= year)
        best = (
            available.sort("year", "preference")
            .group_by("dzs_code")
            .last()
            .select(
                "dzs_code",
                pl.lit(year, dtype=pl.Int32).alias("year"),
                pl.col("total").alias("population"),
            )
        )
        rows.append(best)
    return pl.concat(rows)


def per_resident(column: str) -> pl.Expr:
    return (pl.col(column) / pl.col("population")).round(2)


def peer_table(
    master: pl.DataFrame, population: pl.DataFrame, budget_lines: pl.DataFrame
) -> pl.DataFrame:
    """One row per municipality and budget year with its peer group, figures and ranks."""
    totals = (
        budget_lines.filter(
            pl.col("classification") == "derived",
            pl.col("code").is_in([REVENUE_CODE, EXPENDITURE_CODE]),
        )
        .pivot(on="code", index=["dzs_code", "year"], values="amount_eur", aggregate_function="sum")
        .rename({REVENUE_CODE: "revenue_eur", EXPENDITURE_CODE: "expenditure_eur"})
    )
    years = sorted(totals["year"].unique().to_list())
    table = (
        totals.join(population_by_year(population, years), on=["dzs_code", "year"], how="inner")
        .join(master.select("dzs_code", "slug", "name", "type", "county"), on="dzs_code")
        .with_columns(
            band=pl.col("population").map_elements(band_for, return_dtype=pl.Utf8),
            revenue_per_resident_eur=per_resident("revenue_eur"),
            expenditure_per_resident_eur=per_resident("expenditure_eur"),
        )
        .with_columns(group=pl.concat_str("county", "type", "band", separator="|"))
    )
    group = ["year", "group"]
    return table.with_columns(
        group_size=pl.len().over(group),
        **{
            f"rank_{metric}": pl.col(metric).rank("min", descending=True).over(group).cast(pl.Int32)
            for metric in METRICS
        },
    ).sort("year", "group", "dzs_code")
