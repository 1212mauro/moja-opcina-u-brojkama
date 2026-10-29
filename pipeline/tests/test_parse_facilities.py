import json
from pathlib import Path

import httpx
import polars as pl
import pytest

from opcina_pipeline.fetch.http import PoliteClient
from opcina_pipeline.parse.facilities import (
    Geocoder,
    MinistryRow,
    address_key,
    geocode_queries,
    health_name,
    kindergarten_core,
    names_match,
    parse_facilities,
    read_ministry,
    read_municipalities,
    read_osm,
)
from opcina_pipeline.tables import FACILITY

FIXTURES = Path(__file__).parent / "fixtures" / "parse_facilities"
COUNTY = "Varaždinska županija"
ALFA, BETA = "00001", "00002"
RUN_IDS = {
    "schools_primary": "run-primary",
    "schools_secondary": "run-secondary",
    "kindergartens": "run-kindergartens",
    "osm_facilities": "run-osm",
}
SETTLEMENTS = {"alfa": {ALFA}, "beta": {BETA}, "selo": {BETA}}


class FakeGeocoder:
    """Answers from a dict keyed by query; records every query."""

    def __init__(self, answers: dict[str, list[dict]]):
        self.answers = answers
        self.queries: list[str] = []
        self.requests = 0

    def search(self, query, viewbox):
        self.queries.append(query)
        self.requests += 1
        return self.answers.get(query, [])


def hit(lon, lat, rank=30):
    return {"lon": lon, "lat": lat, "place_rank": rank}


@pytest.fixture
def ministry() -> list[MinistryRow]:
    return [
        row
        for source in ("schools_primary", "schools_secondary", "kindergartens")
        for row in read_ministry(FIXTURES / source, source, COUNTY)
    ]


@pytest.fixture
def geocoder() -> FakeGeocoder:
    return FakeGeocoder(
        {
            "Glavna 5, Beta": [hit(16.15, 46.05)],
            "Cesta 2, Beta": [hit(16.15, 46.07)],
            # A city-level result inside Alfa and a precise one in the wrong municipality.
            "Ul. A. Šenoe 4, Alfa": [hit(16.05, 46.05, rank=16), hit(16.15, 46.02)],
            "Alfa": [hit(16.05, 46.05, rank=16)],  # a town: its centre is too coarse
            "Selo": [hit(16.13, 46.03, rank=16)],  # a village: its centre will do
        }
    )


@pytest.fixture
def result(ministry, geocoder):
    units = read_municipalities(FIXTURES / "municipalities.geojson", {ALFA, BETA})
    return parse_facilities(
        ministry,
        read_osm(FIXTURES / "overpass.json"),
        units,
        SETTLEMENTS,
        RUN_IDS,
        geocoder,
        towns=frozenset({"alfa"}),
    )


def by_id(df: pl.DataFrame) -> dict[str, dict]:
    return {r["facility_id"]: r for r in df.iter_rows(named=True)}


def test_read_ministry_filters_county_and_reads_no_personal_fields(ministry):
    assert [(r.source, r.code) for r in ministry if r.type == "school"] == [
        ("schools_primary", "05-001-001"),
        ("schools_primary", "05-002-001"),
        ("schools_primary", "05-002-002"),
        ("schools_secondary", "05-001-501"),
        ("schools_secondary", "05-001-001"),
    ]
    # "Zupanija" values carry a trailing space; the other county's row is gone.
    assert [r.name for r in ministry if r.type == "kindergarten"] == [
        'Dječji vrtić "Sunce"',
        'Dječji vrtić "Mjesec"',
        "Udruga Igra",
    ]
    assert [r.subtype for r in ministry if r.type == "kindergarten"] == [
        "kindergarten",
        "kindergarten",
        "preschool_programme",
    ]


def test_facility_rows(result):
    df, report = result
    assert df.schema == pl.Schema(FACILITY)
    rows = by_id(df)
    assert set(rows) == {
        "mzo:05-001-001",
        "mzo:05-002-001",
        "mzo:05-002-002",
        "mzo:05-001-501",
        "osm:way/2",  # branch school
        "osm:node/5",  # school missing from the ministry list
        "mzo:dv/alfa/djecji-vrtic-sunce",
        "mzo:dv/beta/djecji-vrtic-mjesec",
        "mzo:dv/alfa/udruga-igra",
        "osm:way/21",  # other building of "Sunce"
        "osm:node/24",  # kindergarten only in OSM
        "osm:node/30",
        "osm:node/32",
        "osm:way/33",
        "osm:node/34",
    }

    def located(fid):
        r = rows[fid]
        return r["dzs_code"], r["location_source"], round(r["lon"], 4), round(r["lat"], 4)

    assert located("mzo:05-001-001") == (ALFA, "osm", 16.02, 46.02)
    assert located("mzo:05-001-501") == (ALFA, "osm", 16.03, 46.03)  # address match
    assert located("mzo:05-002-001") == (BETA, "geocoded", 16.15, 46.05)
    assert located("mzo:dv/alfa/djecji-vrtic-sunce") == (ALFA, "osm", 16.05, 46.05)
    # Geocoded, then the OSM kindergarten 65 m away is taken as the same one.
    assert located("mzo:dv/beta/djecji-vrtic-mjesec") == (BETA, "osm", 16.1505, 46.0705)
    # Unknown Mjesto, settlement from the address, address not found: the village centre.
    assert located("mzo:05-002-002") == (BETA, "geocoded", 16.13, 46.03)
    # Town-level and out-of-municipality results are rejected: municipality point.
    assert rows["mzo:dv/alfa/udruga-igra"]["dzs_code"] == ALFA
    assert rows["mzo:dv/alfa/udruga-igra"]["location_source"] == "municipality_point"

    assert rows["osm:way/2"]["dzs_code"] == BETA
    assert rows["osm:way/2"]["subtype"] == "primary"
    assert rows["osm:node/5"]["subtype"] == "secondary"
    assert rows["mzo:05-001-001"]["subtype"] == "primary"  # in both lists, kept once
    assert rows["mzo:05-001-001"]["source_run_id"] == "run-primary"
    assert rows["mzo:05-001-501"]["source_run_id"] == "run-secondary"
    assert rows["osm:node/24"]["source_run_id"] == "run-osm"

    assert rows["osm:node/32"]["name"] == "Ordinacija opće medicine"
    assert rows["osm:node/34"]["name"] == "Stomatološka ordinacija"
    assert rows["osm:way/33"]["name"] == "Ambulanta Beta"
    assert rows["osm:node/30"]["subtype"] == "pharmacy"

    text = " ".join(str(v) for r in rows.values() for v in r.values())
    assert "Ivić" not in text and "Anić" not in text and "example.org" not in text

    assert any("Nepoznato" in u for u in report.unmatched_settlements)
    assert report.coarse_geocodes == ["Osnovna škola Gama (Selo)"]
    assert report.fallbacks == ["Udruga Igra (Ul. A. Šenoe 4, Alfa)"]
    assert any("node/4" in d and "dropped" in d for d in report.dedup)
    assert any("node/22" in d and "dropped" in d for d in report.dedup)
    assert any("node/31" in d for d in report.dedup)
    assert any("node/35" in d for d in report.dropped)


def test_geocoder_queries(result, geocoder):
    assert geocoder.queries == [
        "Glavna 5, Beta",
        "Selo 7, Nepoznato",
        "Selo",  # settlement from the address, as a last resort
        "Cesta 2, Beta",
        "Ul. A. Šenoe 4, Alfa",
        "Šenoe 4, Alfa",
        "Alfa",
    ]
    assert result[1].geocode_requests == 7


def test_geocoder_caches_answers(tmp_path):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=[{"lat": "46.05", "lon": "16.05", "place_rank": 30}])

    cache = tmp_path / "geocode_cache.json"
    client = PoliteClient(min_interval=0, transport=httpx.MockTransport(handler))
    geocoder = Geocoder(cache, client=client)
    viewbox = (16.0, 46.0, 16.1, 46.1)
    first = geocoder.search("Dravska 1, Alfa", viewbox)
    assert geocoder.search("Dravska 1, Alfa", viewbox) == first
    assert len(seen) == 1 and geocoder.requests == 1
    params = seen[0].url.params
    assert params["format"] == "jsonv2" and params["countrycodes"] == "hr"
    assert params["viewbox"] == "16.0,46.1,16.1,46.0" and params["bounded"] == "1"
    assert seen[0].headers["user-agent"].startswith("moja-opcina")
    assert first == [
        {
            "lat": 46.05,
            "lon": 16.05,
            "place_rank": 30,
            "category": None,
            "type": None,
            "display_name": None,
        }
    ]

    def offline(request):
        raise AssertionError("a rerun must not hit the network")

    rerun = Geocoder(cache, client=PoliteClient(transport=httpx.MockTransport(offline)))
    assert rerun.search("Dravska 1, Alfa", viewbox) == first
    assert rerun.requests == 0
    assert list(json.loads(cache.read_text(encoding="utf-8")).values()) == [first]


def test_name_and_address_helpers():
    assert address_key("Dravska ulica 1") == address_key("DRAVSKA 1") == "dravska 1"
    assert address_key("Kamenica35 H") == "kamenica 35 h"
    assert names_match(
        kindergarten_core('Dječji vrtić "Ježeva kućica - Beretinec"'),
        kindergarten_core("Dječji vrtić Ježeva kućica"),
    )
    assert names_match(kindergarten_core("Dječji vrtić- Vrtić Panda"), kindergarten_core("Panda"))
    assert not kindergarten_core("Dječji vrtić")
    assert not names_match(kindergarten_core("DV Zeko"), kindergarten_core("Dječji vrtić Zečić"))


def test_health_names_drop_personal_names():
    assert health_name("doctors", "Ambulanta Novi Marof", "general") == "Ambulanta Novi Marof"
    assert health_name("dentist", "Zubni rendgen dr. Lauc", None) == "Stomatološka ordinacija"
    assert (
        health_name("dentist", "Privatna ordinacija dentalne medicine Ime Prezime", None)
        == "Stomatološka ordinacija"
    )
    assert health_name("doctors", "Ordinacija Ime Prezime", "occupational") == (
        "Ordinacija medicine rada"
    )
    assert health_name("pharmacy", None, None) == "Ljekarna"
    assert health_name("hospital", "Opća bolnica Varaždin", None) == "Opća bolnica Varaždin"


def test_geocode_queries_drop_postcode_initials_and_bb():
    row = MinistryRow("kindergartens", None, "X", "Dravska bb", "Bartolovec", "42202", "k", "k")
    assert geocode_queries(row) == ["Dravska, Bartolovec"]
    row = MinistryRow("kindergartens", None, "X", "J.Križanića 96", "Varaždin", "42000", "k", "k")
    assert geocode_queries(row) == ["J.Križanića 96, Varaždin", "Križanića 96, Varaždin"]
    row = MinistryRow(
        "schools_secondary", "1", "X", "Božene Plazzeriano 4, 42000 Varaždin", "Varaždin",
        "42000", "school", "secondary",
    )  # fmt: skip
    assert geocode_queries(row) == ["Božene Plazzeriano 4, Varaždin"]
