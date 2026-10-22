"""OpenStreetMap schools, kindergartens and health facilities via the Overpass API.

Fallback for facilities the official registries list without coordinates, and
the only national source for health facilities. The county is selected by its
ISO 3166-2 code, which uses the same numbering as MinFin ("5" -> "HR-05").
"""

import json

import httpx

from opcina_pipeline.fetch.base import FetchContext, Outcome, fetcher
from opcina_pipeline.fetch.http import Download, content_fingerprint, file_sha256

AMENITIES = "school|kindergarten|clinic|doctors|hospital|pharmacy|dentist"
HEALTHCARE = "clinic|doctor|hospital|pharmacy|dentist|centre"


def overpass_query(iso_code: str) -> str:
    return f"""
[out:json][timeout:180];
area["ISO3166-2"="{iso_code}"]["boundary"="administrative"]->.county;
(
  nwr["amenity"~"^({AMENITIES})$"](area.county);
  nwr["healthcare"~"^({HEALTHCARE})$"](area.county);
);
out center tags;
""".strip()


@fetcher("osm_facilities")
def fetch_osm(ctx: FetchContext) -> Outcome:
    iso_code = f"HR-{int(ctx.scope.register_code):02d}"
    query = overpass_query(iso_code)
    errors = []
    for endpoint in ctx.source.options["endpoints"]:
        try:
            response = ctx.client.post(endpoint, data={"data": query})
            payload = response.json()
        except (httpx.HTTPError, json.JSONDecodeError) as error:
            errors.append(f"{endpoint}: {type(error).__name__}")
            continue
        elements = payload.get("elements", [])
        if not elements:  # an empty answer means the area lookup failed, not "no facilities"
            errors.append(f"{endpoint}: 0 elements ({payload.get('remark', 'no remark')})")
            continue
        return Outcome.from_downloads(
            [write_json(ctx.source.path, payload)],
            f"{len(elements)} elements for {iso_code} from {endpoint}, "
            f"data as of {payload.get('osm3s', {}).get('timestamp_osm_base', '?')}",
        )
    raise RuntimeError("every Overpass endpoint failed: " + "; ".join(errors))


def write_json(dest, payload: dict) -> Download:
    """Write a JSON answer; "changed" ignores Overpass's own timestamp."""
    previous = _elements_fingerprint(dest) if dest.exists() else None
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    tmp.replace(dest)
    return Download(
        dest, _elements_fingerprint(dest) != previous, file_sha256(dest), dest.stat().st_size
    )


def _elements_fingerprint(path) -> str:
    try:
        elements = json.loads(path.read_text(encoding="utf-8")).get("elements", [])
    except (OSError, json.JSONDecodeError):
        return content_fingerprint(path)
    return json.dumps(elements, sort_keys=True)
