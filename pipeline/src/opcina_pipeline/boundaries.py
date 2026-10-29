"""Browser-sized municipality boundaries (task B6) in the contract's ``Boundaries`` shape.

Polygons are simplified as one coverage (``shapely.coverage_simplify``), so a
border shared by two municipalities is simplified once and neighbours keep
meeting exactly: no slivers or gaps on the map.
"""

import json
from pathlib import Path

import polars as pl
import shapely
from shapely.geometry import mapping, shape

from opcina_pipeline.contract import Boundaries

# Coverage simplification tolerance in degrees (~40 m at 46° N).
DEFAULT_TOLERANCE = 0.0004
COORDINATE_DECIMALS = 5  # ~1 m


def simplify_boundaries(
    features: list[dict],
    master: pl.DataFrame,
    tolerance: float = DEFAULT_TOLERANCE,
    has_data: set[str] | None = None,
) -> Boundaries:
    """``has_data``: DZS codes with a municipality page (default: the pilots)."""
    units = {row["dzs_code"]: row for row in master.iter_rows(named=True)}
    missing = {f["properties"]["dzs_code"] for f in features} ^ set(units)
    if missing:
        raise ValueError(f"boundaries and master table disagree on: {sorted(missing)}")

    geometries = [shape(f["geometry"]) for f in features]
    simplified = shapely.coverage_simplify(geometries, tolerance)
    simplified = shapely.set_precision(simplified, 10**-COORDINATE_DECIMALS)

    out = []
    for feature, geometry in zip(features, simplified, strict=True):
        label = geometry.representative_point()
        unit = units[feature["properties"]["dzs_code"]]
        if geometry.geom_type == "Polygon":
            geometry = shapely.MultiPolygon([geometry])
        out.append(
            {
                "type": "Feature",
                "properties": {
                    "slug": unit["slug"],
                    "name": unit["name"],
                    "type": unit["type"],
                    "hasData": (
                        unit["dzs_code"] in has_data
                        if has_data is not None
                        else unit["pilot"] == "true"
                    ),
                    "labelLon": round(label.x, COORDINATE_DECIMALS),
                    "labelLat": round(label.y, COORDINATE_DECIMALS),
                },
                "geometry": mapping(geometry),
            }
        )
    return Boundaries.model_validate({"type": "FeatureCollection", "features": out})


def write_boundaries(
    source: Path, master: pl.DataFrame, dest: Path, has_data: set[str] | None = None
) -> Boundaries:
    features = json.loads(source.read_text(encoding="utf-8"))["features"]
    boundaries = simplify_boundaries(features, master, has_data=has_data)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(boundaries.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return boundaries
