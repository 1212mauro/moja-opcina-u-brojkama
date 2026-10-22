"""DGU administrative boundaries (INSPIRE AU) via the ATOM download feed.

The WFS is disabled, so the whole country comes as one zipped GML (~600 MB,
EPSG:3035, weekly). It is streamed straight out of the zip; only the county in
scope (2nd-order unit, national code = MinFin county number) and its cities and
municipalities (3rd-order units pointing to it) are kept and reprojected to WGS84.
"""

import json
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import IO
from xml.etree.ElementTree import iterparse

import numpy as np
from pyproj import Transformer

from opcina_pipeline.fetch.base import FetchContext, Outcome, fetcher
from opcina_pipeline.fetch.http import Download, file_sha256
from opcina_pipeline.fetch.links import find_links

AU = "{http://inspire.ec.europa.eu/schemas/au/4.0}"
GML = "{http://www.opengis.net/gml/3.2}"
GN = "{http://inspire.ec.europa.eu/schemas/gn/4.0}"
XLINK = "{http://www.w3.org/1999/xlink}"

COUNTY_LEVEL = "2ndOrder"
MUNICIPALITY_LEVEL = "3rdOrder"

# GML in EPSG:3035 lists northing before easting (the CRS's own axis order);
# always_xy=False keeps that order on input and yields (lat, lon) on output.
TO_WGS84 = Transformer.from_crs("EPSG:3035", "EPSG:4326", always_xy=False)


@dataclass
class Unit:
    gml_id: str
    level: str
    code: str
    name: str
    upper_id: str | None
    # polygons -> rings -> flat "northing easting northing easting ..." text from posList
    polygons: list[list[str]]


def read_units(stream: IO[bytes], levels: set[str]) -> Iterator[Unit]:
    """Administrative units of the given levels, streamed from INSPIRE AU GML."""
    for _, elem in iterparse(stream, events=("end",)):
        if elem.tag != f"{AU}AdministrativeUnit":
            continue
        level_el = elem.find(f"{AU}nationalLevel")
        level = level_el.get(f"{XLINK}title") if level_el is not None else None
        if level in levels:
            upper = elem.find(f"{AU}upperLevelUnit")
            yield Unit(
                gml_id=elem.get(f"{GML}id"),
                level=level,
                code=(elem.findtext(f"{AU}nationalCode") or "").strip(),
                name=(elem.findtext(f".//{GN}text") or "").strip(),
                upper_id=upper.get(f"{XLINK}href", "").lstrip("#") if upper is not None else None,
                polygons=[
                    [ring.text or "" for ring in polygon.iter(f"{GML}posList")]
                    for polygon in elem.iter(f"{GML}Polygon")
                ],
            )
        elem.clear()


def to_wgs84(pos_list: str) -> list[list[float]]:
    values = np.array(pos_list.split(), dtype=float)
    northing, easting = values[0::2], values[1::2]
    lat, lon = TO_WGS84.transform(northing, easting)
    return np.round(np.column_stack([lon, lat]), 6).tolist()


def county_features(stream: IO[bytes], county_code: str) -> list[dict]:
    """GeoJSON features for every city/municipality of the county with this national code."""
    counties: dict[str, str] = {}
    municipalities: list[Unit] = []
    for unit in read_units(stream, {COUNTY_LEVEL, MUNICIPALITY_LEVEL}):
        if unit.level == COUNTY_LEVEL:
            counties[unit.code] = unit.gml_id
        else:
            municipalities.append(unit)

    county_id = counties.get(county_code)
    if county_id is None:
        raise ValueError(f"no county with national code {county_code!r} (have {sorted(counties)})")

    features = []
    for unit in municipalities:
        if unit.upper_id != county_id:
            continue
        rings = [[to_wgs84(ring) for ring in polygon] for polygon in unit.polygons]
        features.append(
            {
                "type": "Feature",
                "properties": {"dzs_code": unit.code, "name": unit.name, "gml_id": unit.gml_id},
                "geometry": {"type": "MultiPolygon", "coordinates": rings},
            }
        )
    return sorted(features, key=lambda f: f["properties"]["dzs_code"])


def extract_county(archive: Path, county_code: str, dest: Path) -> int:
    with zipfile.ZipFile(archive) as zf:
        members = [n for n in zf.namelist() if n.lower().endswith(".gml")]
        if len(members) != 1:
            raise ValueError(f"expected one GML in {archive.name}, found {members}")
        with zf.open(members[0]) as stream:
            features = county_features(stream, county_code)
    if not features:
        raise ValueError(f"no municipalities found for county {county_code}")
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(dest)
    return len(features)


@fetcher("dgu_boundaries")
def fetch_boundaries(ctx: FetchContext) -> Outcome:
    feed = ctx.client.get(ctx.source.url).text
    zips = find_links(feed, r"https?://[^\"'<>\s]+\.zip", ctx.source.url)
    if len(zips) != 1:
        raise ValueError(f"expected one zip in the ATOM feed, found {zips}")
    archive = ctx.client.download(zips[0], ctx.out_dir / "au.zip")

    dest = ctx.source.path
    county_code = f"{int(ctx.scope.register_code):02d}"
    if archive.changed or not dest.exists():
        count = extract_county(archive.path, county_code, dest)
        message = f"{count} municipalities in county {county_code}"
        changed = True
    else:
        message, changed = "archive unchanged", False
    extracted = Download(dest, changed, file_sha256(dest), dest.stat().st_size)
    return Outcome.from_downloads([archive, extracted], message)
