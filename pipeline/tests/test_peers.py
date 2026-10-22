import polars as pl
import pytest

from opcina_pipeline.config import Scope
from opcina_pipeline.parse.population import latest_population, parse_census, parse_estimates
from opcina_pipeline.peers import band_for, peer_table, population_by_year

SCOPE = Scope("Varaždinska", "5", "HR062", "Varaždinska županija", "Varaždinska", ())

MASTER = pl.DataFrame(
    {
        "dzs_code": ["00001", "00002", "00003", "00004"],
        "slug": ["a", "b", "c", "d"],
        "name": ["Alfa", "Beta", "Gama", "Delta"],
        "type": ["opcina", "opcina", "opcina", "grad"],
        "county": ["Varaždinska"] * 4,
    }
)


@pytest.mark.parametrize(
    ("population", "band"),
    [
        (1, "under_3k"),
        (2_999, "under_3k"),
        (3_000, "3k_10k"),
        (9_999, "3k_10k"),
        (10_000, "10k_35k"),
        (35_000, "over_35k"),
        (44_283, "over_35k"),
    ],
)
def test_band_boundaries(population, band):
    assert band_for(population) == band


def population(rows):
    return pl.DataFrame(rows, schema=["dzs_code", "year", "kind", "total"], orient="row")


def test_population_by_year_prefers_same_year_estimate_then_earlier():
    pop = population(
        [
            ("00001", 2021, "census", 1000),
            ("00001", 2021, "estimate", 1010),
            ("00001", 2024, "estimate", 990),
            ("00002", 2021, "census", 2000),
        ]
    )
    got = {
        (r["dzs_code"], r["year"]): r["population"]
        for r in population_by_year(pop, [2021, 2023, 2024]).iter_rows(named=True)
    }
    assert got[("00001", 2021)] == 1010  # estimate beats census in the same year
    assert got[("00001", 2023)] == 1010  # nearest earlier figure
    assert got[("00001", 2024)] == 990
    assert got[("00002", 2024)] == 2000


def budget(rows):
    return pl.DataFrame(
        [(code, 2025, "derived", item, amount) for code, item, amount in rows],
        schema=["dzs_code", "year", "classification", "code", "amount_eur"],
        orient="row",
    )


def test_peer_groups_split_by_type_and_band_and_rank_descending():
    pop = population(
        [
            ("00001", 2025, "estimate", 2_000),
            ("00002", 2025, "estimate", 2_500),
            ("00003", 2025, "estimate", 5_000),  # same type, other band
            ("00004", 2025, "estimate", 2_200),  # same band, other type
        ]
    )
    lines = budget(
        [
            ("00001", "X067", 2_000_000),
            ("00001", "Y034", 1_800_000),
            ("00002", "X067", 3_000_000),
            ("00002", "Y034", 2_000_000),
            ("00003", "X067", 4_000_000),
            ("00003", "Y034", 4_000_000),
            ("00004", "X067", 1_000_000),
            ("00004", "Y034", 1_000_000),
        ]
    )
    table = peer_table(MASTER, pop, lines)
    row = {r["dzs_code"]: r for r in table.iter_rows(named=True)}

    assert row["00001"]["group"] == row["00002"]["group"] == "Varaždinska|opcina|under_3k"
    assert row["00001"]["group_size"] == 2
    assert row["00003"]["group_size"] == row["00004"]["group_size"] == 1
    assert row["00001"]["revenue_per_resident_eur"] == 1000.0
    assert row["00002"]["revenue_per_resident_eur"] == 1200.0
    assert (
        row["00002"]["rank_revenue_per_resident_eur"],
        row["00001"]["rank_revenue_per_resident_eur"],
    ) == (1, 2)
    assert row["00001"]["rank_expenditure_per_resident_eur"] == 1  # 900 vs 800 per resident


def census_sheet(rows):
    header = [
        "Županija",
        "Jedinica lokalne samouprave",
        "County of",
        "Local self-government unit",
        "Grad/općina  \nTown/Municipality ",
        "Tip naselja",
        "Type of settlement",
        "Spol",
        "Sex",
        "Ukupno\nTotal",
    ]
    return pl.DataFrame(rows, schema=header, orient="row")


def test_parse_census_keeps_municipal_totals_only():
    master = MASTER.with_columns(name=pl.Series(["Alfa", "Beta", "Gama", "Delta"]))
    sheet = census_sheet(
        [
            ("Varaždinska", None, "", None, None, "Ukupno", "Total", "sv.", "All", "9000"),
            ("Varaždinska", "Općina", "", "", "Alfa", "Ukupno", "Total", "sv.", "All", "1 234"),
            ("Varaždinska", "Općina", "", "", "Alfa", "Ukupno", "Total", "m", "M", "600"),
            (
                "Varaždinska",
                "Općina",
                "",
                "",
                "Alfa",
                "U ostalim naseljima",
                "",
                "sv.",
                "All",
                "1234",
            ),
            ("Međimurska", "Grad", "", "", "Čakovec", "Ukupno", "Total", "sv.", "All", "27000"),
        ]
    )
    census = parse_census(sheet, master, SCOPE)
    assert census.rows() == [("00001", 2021, "census", 1234)]


def test_parse_census_rejects_unknown_municipality():
    sheet = census_sheet(
        [("Varaždinska", "Općina", "", "", "Nepostojeća", "Ukupno", "", "sv.", "", "1")]
    )
    with pytest.raises(ValueError, match="Nepostojeća"):
        parse_census(sheet, MASTER, SCOPE)


def test_parse_estimates_unpivots_years_and_reads_dash_as_zero():
    sheet = pl.DataFrame(
        {
            "Županije": ["Varaždinska", "Varaždinska"],
            "County of": ["", ""],
            "Gradovi/općine\nTowns/municipalities": ["Alfa", "Beta"],
            "2024.": ["1000", "-"],
            "2025.": ["990", "5"],
            "2025._1": ["12", "3"],  # a later block (births): ignored
        }
    )
    est = parse_estimates(sheet, MASTER, SCOPE).sort("dzs_code", "year")
    assert est.rows() == [
        ("00001", 2024, "estimate", 1000),
        ("00001", 2025, "estimate", 990),
        ("00002", 2024, "estimate", 0),
        ("00002", 2025, "estimate", 5),
    ]
    latest = latest_population(est.with_columns(source_run_id=pl.lit("x")))
    assert dict(latest.select("dzs_code", "total").iter_rows()) == {"00001": 990, "00002": 5}
