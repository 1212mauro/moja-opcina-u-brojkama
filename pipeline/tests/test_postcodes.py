import polars as pl
import pytest

from opcina_pipeline.postcodes import build_postcodes

MASTER = pl.DataFrame(
    {"name": ["Ludbreg", "Maruševec", "Varaždin"], "dzs_code": ["02445", "02607", "04723"]}
)
POSTA = pl.DataFrame(
    {
        "postcode": ["42000", "42230", "42243", "10000"],
        "post_office": ["Varaždin", "Ludbreg", "Maruševec", "Zagreb"],
        "settlement": ["Varaždin", "Selnik", "Selnik", "Zagreb"],
        "county": ["Varaždinska županija"] * 3 + ["Grad Zagreb"],
    }
)
SETTLEMENTS = pl.DataFrame(
    {
        "county": ["Varaždinska"] * 3,
        "municipality": ["Varaždin", "Ludbreg", "Maruševec"],
        "settlement": ["VARAŽDIN", "Selnik", "Selnik"],
    }
)


def test_resolves_ambiguous_settlement_names_with_overrides(scope):
    overrides = {("42230", "Selnik"): "02445", ("42243", "Selnik"): "02607"}
    result = build_postcodes(POSTA, SETTLEMENTS, MASTER, scope, overrides)

    assert result.rows() == [
        ("42000", "Varaždin", "Varaždin", "04723"),
        ("42230", "Ludbreg", "Selnik", "02445"),
        ("42243", "Maruševec", "Selnik", "02607"),
    ]


def test_lists_every_unresolved_settlement(scope):
    with pytest.raises(ValueError, match="42230 Selnik") as error:
        build_postcodes(POSTA, SETTLEMENTS, MASTER, scope, overrides={})
    assert "42243 Selnik" in str(error.value)


def test_rejects_override_with_unknown_code(scope):
    overrides = {("42230", "Selnik"): "02445", ("42243", "Selnik"): "99999"}
    with pytest.raises(ValueError, match="not in the master table"):
        build_postcodes(POSTA, SETTLEMENTS, MASTER, scope, overrides)


def test_rejects_stale_override(scope):
    overrides = {
        ("42230", "Selnik"): "02445",
        ("42243", "Selnik"): "02607",
        ("42999", "Nepostojeće"): "04723",
    }
    with pytest.raises(ValueError, match="matching no Pošta row"):
        build_postcodes(POSTA, SETTLEMENTS, MASTER, scope, overrides)


def test_names_census_municipality_missing_from_master(scope):
    settlements = SETTLEMENTS.with_columns(
        municipality=pl.when(pl.col("municipality") == "Ludbreg")
        .then(pl.lit("Donji Ludbreg"))
        .otherwise(pl.col("municipality"))
    )
    with pytest.raises(ValueError, match="Donji Ludbreg"):
        build_postcodes(POSTA, settlements, MASTER, scope, overrides={})
