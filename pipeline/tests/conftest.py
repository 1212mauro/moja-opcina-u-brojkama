import polars as pl
import pytest

from opcina_pipeline.config import Scope


@pytest.fixture
def scope() -> Scope:
    return Scope(
        county_name="Varaždinska",
        register_code="5",
        nuts3="HR062",
        postal_name="Varaždinska županija",
        census_name="Varaždinska",
        pilot_lau_codes=("04723",),
    )


def register_row(rkp, name, oib, county, city, level, parent=None):
    return {
        "rkp": rkp,
        "official_name": name,
        "oib": oib,
        "county_label": county,
        "city_label": city,
        "level_label": level,
        "parent_rkp": parent,
    }


@pytest.fixture
def register() -> pl.DataFrame:
    level_22 = "22 - Proračun jedinice lokalne i područne (regionalne) samouprave"
    return pl.DataFrame(
        [
            register_row(
                "31350",
                "GRAD VARAŽDIN",
                "13269011531",
                "5 - VARAŽDINSKA",
                "472 - VARAŽDIN",
                level_22,
            ),
            register_row(
                "31761",
                "OPĆINA BREZNIČKI HUM",
                "35774913576",
                "5 - VARAŽDINSKA",
                "151 - BREZNIČKI HUM",
                level_22,
            ),
            # The county's own budget is level 22 too, but it is not a city or municipality.
            register_row(
                "32043",
                "VARAŽDINSKA ŽUPANIJA",
                "15877210917",
                "5 - VARAŽDINSKA",
                "472 - VARAŽDIN",
                level_22,
            ),
            # A budget user of Varaždin (level 21) must not become a master row.
            register_row(
                "41001",
                "GRADSKA KNJIŽNICA",
                "00000000003",
                "5 - VARAŽDINSKA",
                "472 - VARAŽDIN",
                "21 - Proračunski korisnik",
                "31350",
            ),
            # A unit in another county.
            register_row(
                "30001", "GRAD ČAKOVEC", "00000000004", "20 - MEĐIMURSKA", "51 - ČAKOVEC", level_22
            ),
        ]
    )


@pytest.fixture
def lau() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "nuts3": ["HR062", "HR062", "HR061"],
            "dzs_code": ["04723", "01511", "00515"],
            "name": ["Varaždin", "Breznički Hum", "Čakovec"],
        }
    )
