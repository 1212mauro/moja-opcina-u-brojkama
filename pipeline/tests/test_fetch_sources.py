import io
import zipfile
from datetime import date

import polars as pl
import pytest
from pyproj import Transformer

from opcina_pipeline.boundaries import simplify_boundaries
from opcina_pipeline.fetch.ckan import resource_filename
from opcina_pipeline.fetch.dgu import county_features
from opcina_pipeline.fetch.minfin import extract_county_workbook, zip_member_name
from opcina_pipeline.fetch.payments import _month_key, month_starts, next_month

# --- MinFin ---------------------------------------------------------------------------


def test_zip_member_names_are_decoded_as_cp852():
    garbled = "05 Varaždinska.xlsx".encode("cp852").decode("cp437")
    info = zipfile.ZipInfo(garbled)
    info.flag_bits = 0
    assert zip_member_name(info) == "05 Varaždinska.xlsx"


def test_extract_county_workbook_prefers_correction(tmp_path):
    archive = tmp_path / "lokalci.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("14 Osjecko.xlsx", b"original")
        zf.writestr("14 Osjecko ispravak.xlsx", b"corrected")
        zf.writestr("15 Sibensko.xlsx", b"other county")
    chosen = extract_county_workbook(archive, "14", tmp_path / "county.xlsx")
    assert chosen == "14 Osjecko ispravak.xlsx"
    assert (tmp_path / "county.xlsx").read_bytes() == b"corrected"


def test_extract_county_workbook_fails_for_missing_county(tmp_path):
    archive = tmp_path / "lokalci.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("01 Zagrebacka.xlsx", b"x")
    with pytest.raises(ValueError, match="'05 '"):
        extract_county_workbook(archive, "5", tmp_path / "county.xlsx")


# --- Payments ---------------------------------------------------------------------------


def test_month_starts_cross_the_year():
    assert month_starts(date(2026, 2, 17), 4) == [
        date(2025, 11, 1),
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    ]
    assert next_month(date(2025, 12, 1)) == date(2026, 1, 1)


def test_month_key_orders_mm_yy_file_names():
    names = ["X_12-25.ods", "X_01-26.ods", "X_04-25.ods"]
    assert sorted(names, key=_month_key) == ["X_04-25.ods", "X_12-25.ods", "X_01-26.ods"]


# --- CKAN -------------------------------------------------------------------------------


def test_resource_filename_is_slug_plus_extension():
    resource = {"id": "abc", "name": "Registar ugovora 2018. - 2023.", "url": "https://x/a/b.XLSX"}
    assert resource_filename(resource) == "registar-ugovora-2018-2023.xlsx"
    assert (
        resource_filename({"id": "abc", "name": "Škole", "url": "https://x/api", "format": "JSON"})
        == "skole.json"
    )


# --- DGU boundaries ---------------------------------------------------------------------

TO_3035 = Transformer.from_crs("EPSG:4326", "EPSG:3035", always_xy=True)


def pos_list(lonlat_ring):
    """EPSG:3035 posList text in the CRS's own axis order: northing, easting."""
    values = []
    for lon, lat in lonlat_ring:
        easting, northing = TO_3035.transform(lon, lat)
        values += [f"{northing:.3f}", f"{easting:.3f}"]
    return " ".join(values)


def square(lon, lat, size=0.01):
    return [(lon, lat), (lon + size, lat), (lon + size, lat + size), (lon, lat + size), (lon, lat)]


def unit_xml(gml_id, level, code, name, upper, ring):
    upper_xml = f'<au:upperLevelUnit xlink:href="#{upper}"/>' if upper else ""
    return f"""<wfs:member><au:AdministrativeUnit gml:id="{gml_id}">
      <au:geometry><gml:MultiSurface><gml:surfaceMember><gml:Polygon><gml:exterior><gml:LinearRing>
        <gml:posList>{pos_list(ring)}</gml:posList>
      </gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember></gml:MultiSurface></au:geometry>
      <au:nationalCode>{code}</au:nationalCode>
      <au:nationalLevel xlink:href="x/{level}" xlink:title="{level}"/>
      <au:name><gn:GeographicalName><gn:spelling><gn:SpellingOfName><gn:text>{name}</gn:text>
      </gn:SpellingOfName></gn:spelling></gn:GeographicalName></au:name>
      {upper_xml}
    </au:AdministrativeUnit></wfs:member>"""


def test_county_features_keeps_only_the_county_and_reprojects():
    members = [
        unit_xml("AU.1", "2ndOrder", "05", "Varaždinska županija", "AU.0", square(16.0, 46.0, 1)),
        unit_xml("AU.2", "2ndOrder", "06", "Koprivničko-križevačka", "AU.0", square(17.0, 46.0, 1)),
        unit_xml("AU.10", "3rdOrder", "04723", "Varaždin", "AU.1", square(16.33, 46.30)),
        unit_xml("AU.11", "3rdOrder", "01511", "Breznički Hum", "AU.1", square(16.27, 46.10)),
        unit_xml("AU.20", "3rdOrder", "01988", "Koprivnica", "AU.2", square(16.83, 46.16)),
        unit_xml("AU.30", "4thOrder", "000019", "Naselje", "AU.10", square(16.33, 46.30, 0.001)),
    ]
    gml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"
      xmlns:au="http://inspire.ec.europa.eu/schemas/au/4.0" xmlns:gml="http://www.opengis.net/gml/3.2"
      xmlns:gn="http://inspire.ec.europa.eu/schemas/gn/4.0" xmlns:xlink="http://www.w3.org/1999/xlink">
      {"".join(members)}
    </wfs:FeatureCollection>"""

    features = county_features(io.BytesIO(gml.encode("utf-8")), "05")

    assert [f["properties"]["dzs_code"] for f in features] == ["01511", "04723"]
    varazdin = features[1]
    assert varazdin["properties"]["name"] == "Varaždin"
    lon, lat = varazdin["geometry"]["coordinates"][0][0][0]
    assert lon == pytest.approx(16.33, abs=1e-6) and lat == pytest.approx(46.30, abs=1e-6)


def test_county_features_fails_for_unknown_county():
    gml = """<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"/>"""
    with pytest.raises(ValueError, match="'05'"):
        county_features(io.BytesIO(gml.encode()), "05")


# --- Simplified boundaries ----------------------------------------------------------------


def jagged_square(lon0, lat0, size=0.1, steps=50):
    """A square whose shared east/west edges carry many tiny zigzags."""
    east = [
        (lon0 + size + (0.00001 if i % 2 else 0), lat0 + size * i / steps) for i in range(steps + 1)
    ]
    west = [
        (lon0 + (0.00001 if i % 2 else 0), lat0 + size * i / steps) for i in range(steps, -1, -1)
    ]
    return [*east, *west, east[0]]


def boundary_feature(code, ring):
    return {
        "type": "Feature",
        "properties": {"dzs_code": code},
        "geometry": {"type": "MultiPolygon", "coordinates": [[[list(p) for p in ring]]]},
    }


MASTER = pl.DataFrame(
    {
        "dzs_code": ["00001", "00002"],
        "slug": ["lijevo", "desno"],
        "name": ["Lijevo", "Desno"],
        "type": ["opcina", "grad"],
        "pilot": ["true", "false"],
    }
)


def test_simplify_boundaries_keeps_neighbours_touching():
    from shapely.geometry import shape

    features = [
        boundary_feature("00001", jagged_square(16.0, 46.0)),
        boundary_feature("00002", jagged_square(16.1, 46.0)),
    ]
    result = simplify_boundaries(features, MASTER, tolerance=0.001).model_dump(mode="json")

    left, right = (shape(f["geometry"]) for f in result["features"])
    assert left.intersection(right).area == pytest.approx(0, abs=1e-12)
    assert left.distance(right) == 0
    assert len(result["features"][0]["geometry"]["coordinates"][0][0]) < 20
    assert result["features"][0]["properties"] == {
        "slug": "lijevo",
        "name": "Lijevo",
        "type": "opcina",
        "hasData": True,
    }


def test_simplify_boundaries_rejects_units_missing_from_master():
    features = [boundary_feature("99999", jagged_square(16.0, 46.0))]
    with pytest.raises(ValueError, match="disagree"):
        simplify_boundaries(features, MASTER)


# --- Payments connectors -------------------------------------------------------------------


class FakeCtx:
    """Just enough of FetchContext for one connector."""

    def __init__(self, handler, months=3):
        import httpx

        from opcina_pipeline.fetch.http import PoliteClient

        self.client = PoliteClient(
            min_interval=0, backoff=0, transport=httpx.MockTransport(handler)
        )
        self.source = type("S", (), {"options": {"months": months}})()


def test_empty_months_are_asked_again(tmp_path, monkeypatch):
    import httpx

    from opcina_pipeline.fetch import payments

    monkeypatch.setattr(payments, "_today", lambda: date(2026, 12, 5))
    (tmp_path / "2026-10.csv").write_bytes(b"")  # nothing was published in October yet
    (tmp_path / "2026-09.csv").write_bytes(b'"Naziv isplatitelja";"Datum"\n')
    asked = []

    def handler(request):
        asked.append(request.url.params["filters"])
        return httpx.Response(200, content=b'"Naziv isplatitelja";"Datum"\n')

    payments.fetch_otvorenigrad(FakeCtx(handler, months=4), {"tenant": "grad-x"}, tmp_path)

    assert any('"2026-10-01"' in f for f in asked)  # empty month asked again
    assert not any('"2026-09-01"' in f for f in asked)  # finished month kept


def test_html_links_removes_files_no_longer_linked(tmp_path):
    import httpx

    from opcina_pipeline.fetch import payments

    (tmp_path / "Isplate_04-26.ods").write_bytes(b"old upload")
    page = '<a href="/f/Isplate_04-26_ispravak.ods">x</a><a href="/f/Isplate_03-26.ods">y</a>'

    def handler(request):
        if request.url.path == "/page":
            return httpx.Response(200, text=page)
        return httpx.Response(200, content=b"ods")

    entry = {"page": "https://hum.hr/page", "pattern": r"/f/[^\"]+\.ods"}
    payments.fetch_html_links(FakeCtx(handler), entry, tmp_path)

    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "Isplate_03-26.ods",
        "Isplate_04-26_ispravak.ods",
    ]
