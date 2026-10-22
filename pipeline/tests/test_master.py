from dataclasses import replace

import polars as pl
import pytest

from opcina_pipeline.master import MASTER_COLUMNS, build_master


def test_builds_one_row_per_unit_in_county(register, lau, scope):
    master = build_master(register, lau, scope)

    assert master.columns == MASTER_COLUMNS
    assert master["slug"].to_list() == ["breznicki-hum", "varazdin"]
    varazdin = master.row(by_predicate=pl.col("slug") == "varazdin", named=True)
    assert varazdin == {
        "slug": "varazdin",
        "name": "Varaždin",
        "official_name": "GRAD VARAŽDIN",
        "type": "grad",
        "oib": "13269011531",
        "rkp": "31350",
        "dzs_code": "04723",
        "lau_code": "HR_04723",
        "county": "Varaždinska",
        "pilot": True,
    }
    assert master.filter(pl.col("slug") == "breznicki-hum")["type"].item() == "opcina"


def test_pads_rkp_to_five_digits(register, lau, scope):
    register = register.with_columns(
        rkp=pl.when(pl.col("rkp") == "31761").then(pl.lit("761")).otherwise(pl.col("rkp"))
    )
    master = build_master(register, lau, scope)
    assert master.filter(pl.col("slug") == "breznicki-hum")["rkp"].item() == "00761"


def test_fails_when_a_unit_has_no_lau_code(register, lau, scope):
    with pytest.raises(ValueError, match="disagree"):
        build_master(register, lau.filter(pl.col("dzs_code") != "01511"), scope)


def test_fails_when_code_join_pairs_different_names(register, lau, scope):
    lau = lau.with_columns(
        name=pl.when(pl.col("dzs_code") == "01511")
        .then(pl.lit("Breznica"))
        .otherwise(pl.col("name"))
    )
    with pytest.raises(ValueError, match="different names"):
        build_master(register, lau, scope)


def test_fails_when_a_pilot_is_out_of_scope(register, lau, scope):
    scope = replace(scope, pilot_lau_codes=("99999",))
    with pytest.raises(ValueError, match="pilot"):
        build_master(register, lau, scope)
