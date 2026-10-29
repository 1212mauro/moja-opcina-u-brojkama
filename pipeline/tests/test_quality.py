from datetime import date

import polars as pl
import pytest

from opcina_pipeline import quality
from opcina_pipeline.quality import check_table, natural_persons_anonymous
from opcina_pipeline.tables import conform


@pytest.fixture(autouse=True)
def synthetic_units(monkeypatch):
    """Synthetic codes are not in the real master table; skip that one check."""
    checks = [c for c in quality.TABLE_CHECKS["population"] if c is not quality.every_unit_present]
    monkeypatch.setitem(quality.TABLE_CHECKS, "population", checks)


def population(n: int, start: int = 0) -> pl.DataFrame:
    return conform(
        pl.DataFrame(
            {
                "dzs_code": [f"{i:05d}" for i in range(start, start + n)],
                "year": [2021] * n,
                "kind": ["census"] * n,
                "total": [1000] * n,
                "source_run_id": ["r"] * n,
            }
        ),
        "population",
    )


def test_first_run_passes_without_row_limit():
    result = check_table("population", population(10), None)
    assert result.passed, result.problems


def test_row_count_swing_beyond_tolerance_fails():
    assert check_table("population", population(12), population(10)).passed  # +20 %
    failed = check_table("population", population(7), population(10))  # -30 %
    assert not failed.passed
    assert "-30%" in failed.problems[0]


def test_changed_schema_fails():
    staged = population(3).with_columns(pl.col("total").cast(pl.Float64))
    result = check_table("population", staged, None)
    assert not result.passed and "schema differs" in result.problems[0]


def test_duplicates_fail():
    staged = pl.concat([population(3), population(1)])
    result = check_table("population", staged, None)
    assert any("duplicate" in p for p in result.problems)


def payments(**overrides) -> pl.DataFrame:
    row = {
        "dzs_code": "02445",
        "paid_on": date(2026, 9, 1),
        "month": "2026-09",
        "payer_name": "Grad",
        "recipient_name": None,
        "recipient_oib": None,
        "natural_person": True,
        "economic_code": "3721",
        "economic_label": "Naknade građanima",
        "function_code": None,
        "description": None,
        "amount_eur": 100.0,
        "source_run_id": "r",
    }
    row.update(overrides)
    return conform(pl.DataFrame([row]), "payment")


def test_natural_person_names_are_never_published():
    assert natural_persons_anonymous(payments()) == []
    assert natural_persons_anonymous(payments(recipient_name="Ivo Ivić")) == [
        "1 natural-person payments carry a name or OIB"
    ]
    assert not check_table("payment", payments(recipient_oib="12345678903"), None).passed
