"""Schools, kindergartens and health facilities per municipality (task C8).

Sources and how they are joined:

- Ministry registries (e-Matica, national JSON): the authoritative list of schools
  and kindergartens, with addresses but no coordinates. ``Mjesto`` (or a settlement
  named in the address) is matched to the DZS census settlement list, which names
  the municipality. Contact columns and ``Ravnatelj`` (a person) are never read.
- OpenStreetMap (Overpass): coordinates, and the only source of health facilities.
  Schools carry ``ref:HR:e-matica`` = the ministry's ``Šifra``.

Coordinates of ministry rows, in order of preference:

1. ``osm``: the OSM element with the same e-Matica code (schools), or the OSM
   kindergarten with the same normalised name in the same municipality.
2. ``geocoded``: Nominatim, up to three queries per facility (address, simplified
   address, settlement), every answer cached in ``data/interim/geocode_cache.json``.
   A result counts only if it falls inside the facility's municipality and is
   precise: a street or finer, or, for the settlement query, a village (any
   settlement except a town that gives its name to a grad).
3. ``municipality_point``: the municipality polygon's ``representative_point()``.

OSM elements that are not the location of a ministry row:

- Schools: branch schools ("Područna škola ...") share the parent's e-Matica code
  and are separate buildings, so they become rows of their own (``osm:<type>/<id>``).
  Elements whose code is missing from the ministry list are separate institutions
  and become rows too. Any other element with a ministry code is a duplicate of the
  ministry row and is dropped.
- Kindergartens: an OSM kindergarten is the same facility as a ministry row when its
  normalised name matches within the municipality, or (for geocoded rows) when it
  lies within 300 m. Name matches that are not the chosen location are other
  buildings of the same institution and are kept unless within 300 m of it. Unnamed
  OSM kindergartens within 300 m of a listed one are dropped as duplicates.

Every row's point is checked to lie inside its municipality polygon.
"""

import json
import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlencode

import polars as pl
import shapely
from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry

from opcina_pipeline.config import config_path, load_scope, load_sources, repo_root
from opcina_pipeline.fetch.http import PoliteClient
from opcina_pipeline.postcodes import read_census_settlements
from opcina_pipeline.tables import FACILITY, conform, latest_run_id
from opcina_pipeline.text import ascii_fold, name_key, slugify

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_INTERVAL = 1.1  # seconds; Nominatim allows at most 1 request per second
MIN_PLACE_RANK = 19  # Nominatim place_rank: 26 street, 30 house; 16 a settlement boundary
SETTLEMENT_RANK = 16  # Croatian settlements are administrative boundaries in Nominatim
MATCH_DISTANCE_M = 300.0  # same facility if this close (kindergartens)
HEALTH_DUPLICATE_M = 100.0  # same subtype + same name this close = one OSM facility

MINISTRY_SOURCES = {
    "schools_primary": ("school", "primary"),
    "schools_secondary": ("school", "secondary"),
    "kindergartens": ("kindergarten", "kindergarten"),
}
OSM_SOURCE = "osm_facilities"

HEALTH_SUBTYPES = {
    "hospital": "hospital",
    "clinic": "clinic",
    "doctors": "doctors",
    "doctor": "doctors",
    "dentist": "dentist",
    "pharmacy": "pharmacy",
}
HEALTH_LABELS = {
    "hospital": "Bolnica",
    "clinic": "Ambulanta",
    "doctors": "Liječnička ordinacija",
    "dentist": "Stomatološka ordinacija",
    "pharmacy": "Ljekarna",
}
# Used instead of a practice's name when that name may contain a person's name.
SPECIALITY_LABELS = {
    "general": "Ordinacija opće medicine",
    "occupational": "Ordinacija medicine rada",
    "dermatovenereology": "Dermatovenerološka ordinacija",
    "paediatrics": "Pedijatrijska ordinacija",
    "gynaecology": "Ginekološka ordinacija",
    "orthodontics": "Ortodontska ordinacija",
    "radiology": "Radiološka ordinacija",
}
# Doctor and dentist names are kept only if they name an institution, not a person.
INSTITUTION_WORDS = re.compile(
    r"\b(ambulant\w*|dom zdravlja|zdravstveni dom|poliklinik\w*|bolnic\w*|sluzb\w*|zavod\w*)\b"
)
DOCTOR_TITLE = re.compile(r"\bdr\b")
BRANCH_SCHOOL = re.compile(r"\b(podrucn\w*|ps)\b")
KINDERGARTEN_WORDS = {"djecji", "djecki", "decji", "vrtic", "vrtici", "dv"}
STREET_WORDS = {"ulica", "ul"}


# --- small helpers -------------------------------------------------------------------


def _tokens(text: str) -> list[str]:
    """Folded words; letters and digits glued together are split ("Kamenica35" -> 2)."""
    folded = ascii_fold(text)
    folded = re.sub(r"(?<=[a-z])(?=\d)|(?<=\d)(?=[a-z]{2})", " ", folded)
    return re.sub(r"[^\w/]+", " ", folded).split()


def _clean(text: str | None) -> str | None:
    if text is None:
        return None
    text = " ".join(str(text).split())
    return text or None


def address_key(text: str) -> str:
    """ "Dravska ulica 1" and "DRAVSKA 1" -> "dravska 1"."""
    return " ".join(t for t in _tokens(text) if t not in STREET_WORDS)


def address_keys(address: str) -> set[str]:
    """Keys of each comma-separated part ("Šemovec, Plitvička 2" -> two keys)."""
    return {address_key(part) for part in address.split(",") if address_key(part)}


def kindergarten_core(name: str) -> frozenset[str]:
    """Distinctive words of a kindergarten name: 'Dječji vrtić "Sunce"' -> {"sunce"}."""
    return frozenset(t for t in _tokens(name) if t not in KINDERGARTEN_WORDS and len(t) > 1)


def names_match(a: frozenset[str], b: frozenset[str]) -> bool:
    return bool(a) and bool(b) and (a <= b or b <= a)


def distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in metres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = phi2 - phi1, math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def school_subtype_from_code(code: str | None, name: str) -> str:
    """e-Matica numbers secondary schools 5xx within the town (05-086-501)."""
    if code and re.fullmatch(r"\d{2}-\d{3}-\d{3}", code):
        return "secondary" if int(code[-3:]) >= 500 else "primary"
    return "secondary" if re.search(r"gimnazij|srednj", ascii_fold(name)) else "primary"


def health_name(subtype: str, name: str | None, speciality: str | None) -> str:
    """OSM name, unless it may name a person (doctors' and dentists' private practices)."""
    label = HEALTH_LABELS[subtype]
    if subtype in ("doctors", "dentist") and speciality:
        label = SPECIALITY_LABELS.get(speciality.split(";")[0], label)
    if not name:
        return label
    folded = ascii_fold(name)
    if DOCTOR_TITLE.search(folded):
        return label
    if subtype in ("doctors", "dentist") and not INSTITUTION_WORDS.search(folded):
        return label
    return name


# --- inputs --------------------------------------------------------------------------


@dataclass
class Municipalities:
    polygons: dict[str, BaseGeometry]

    def __post_init__(self) -> None:
        for geometry in self.polygons.values():
            shapely.prepare(geometry)

    def locate(self, lon: float, lat: float) -> str | None:
        point = Point(lon, lat)
        for code, geometry in self.polygons.items():
            if geometry.covers(point):
                return code
        return None

    def contains(self, code: str, lon: float, lat: float) -> bool:
        return self.polygons[code].covers(Point(lon, lat))

    def viewbox(self, codes: set[str]) -> tuple[float, float, float, float]:
        minx, miny, maxx, maxy = shapely.union_all([self.polygons[c] for c in codes]).bounds
        return (round(minx, 4), round(miny, 4), round(maxx, 4), round(maxy, 4))


def read_municipalities(path: Path, codes: set[str]) -> Municipalities:
    features = json.loads(path.read_text(encoding="utf-8"))["features"]
    polygons = {
        f["properties"]["dzs_code"]: shape(f["geometry"])
        for f in features
        if f["properties"]["dzs_code"] in codes
    }
    missing = codes - set(polygons)
    if missing:
        raise ValueError(f"no boundary polygon for {sorted(missing)}")
    return Municipalities(polygons)


def settlement_index(
    settlements: pl.DataFrame, master: pl.DataFrame, census_name: str
) -> dict[str, set[str]]:
    """name_key(settlement) -> dzs codes of the municipalities that have a settlement so named."""
    code_by_name = {name_key(n): c for n, c in master.select("name", "dzs_code").iter_rows()}
    index: dict[str, set[str]] = {}
    for municipality, settlement in (
        settlements.filter(pl.col("county") == census_name)
        .select("municipality", "settlement")
        .iter_rows()
    ):
        code = code_by_name.get(name_key(municipality))
        if code is None:
            raise ValueError(f"census municipality missing from the master table: {municipality}")
        index.setdefault(name_key(settlement), set()).add(code)
    return index


@dataclass
class MinistryRow:
    source: str  # key in MINISTRY_SOURCES
    code: str | None  # e-Matica Šifra (schools only)
    name: str
    address: str | None
    place: str  # Mjesto
    postcode: str | None
    type: str
    subtype: str


def _field(record: dict, *names: str) -> str | None:
    for name in names:
        if name in record:
            return _clean(record[name])
    return None


def _county_key(record: dict) -> str:
    """The county column, spelled "Župnija", "Županija" or "Zupanija" depending on the file."""
    for key in record:
        if ascii_fold(key).startswith(("zupanij", "zupnij")):
            return key
    raise ValueError(f"no county column among {sorted(record)}")


def read_ministry(folder: Path, source: str, county: str) -> list[MinistryRow]:
    """Rows of every JSON file in ``folder`` in ``county`` (e.g. "Varaždinska županija")."""
    facility_type, subtype = MINISTRY_SOURCES[source]
    rows = []
    for path in sorted(folder.glob("*.json")):
        for record in json.loads(path.read_text(encoding="utf-8-sig")):
            if name_key(record.get(_county_key(record)) or "") != name_key(county):
                continue
            name = _field(record, "Naziv")
            row_subtype = subtype
            if facility_type == "kindergarten" and not KINDERGARTEN_WORDS & set(_tokens(name)):
                row_subtype = "preschool_programme"  # e.g. run by an association or a school
            rows.append(
                MinistryRow(
                    source=source,
                    code=_field(record, "Šifra", "Sifra"),
                    name=name,
                    address=_field(record, "Adresa"),
                    place=_field(record, "Mjesto"),
                    postcode=_field(record, "PoštanskiBroj", "PostanskiBroj"),
                    type=facility_type,
                    subtype=row_subtype,
                )
            )
    return rows


@dataclass
class OsmFeature:
    osm_id: str  # "way/123"
    tags: dict
    lon: float
    lat: float
    dzs_code: str

    @property
    def name(self) -> str | None:
        return _clean(self.tags.get("name"))

    @property
    def address(self) -> str | None:
        street = self.tags.get("addr:street") or self.tags.get("addr:place")
        number = self.tags.get("addr:housenumber")
        return _clean(" ".join(p for p in (street, number) if p)) if street else None

    @property
    def settlement(self) -> str | None:
        return _clean(self.tags.get("addr:city") or self.tags.get("addr:place"))


def read_osm(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["elements"]


# --- geocoding -----------------------------------------------------------------------


class Geocoder:
    """Nominatim search with a persistent cache: reruns make no requests."""

    def __init__(self, cache_path: Path, client: PoliteClient | None = None):
        self.cache_path = cache_path
        self._cache: dict[str, list[dict]] = (
            json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
        )
        self._client = client
        self._own_client = client is None
        self.requests = 0

    def search(self, query: str, viewbox: tuple[float, float, float, float]) -> list[dict]:
        minx, miny, maxx, maxy = viewbox
        params = {
            "q": query,
            "format": "jsonv2",
            "countrycodes": "hr",
            "limit": "5",
            "viewbox": f"{minx},{maxy},{maxx},{miny}",
            "bounded": "1",
            "accept-language": "hr",
        }
        key = urlencode(sorted(params.items()))
        if key in self._cache:
            return self._cache[key]
        if self._client is None:
            self._client = PoliteClient(min_interval=NOMINATIM_INTERVAL)
        response = self._client.get(NOMINATIM_URL, params=params)
        self.requests += 1
        results = [
            {
                "lat": float(r["lat"]),
                "lon": float(r["lon"]),
                "place_rank": r.get("place_rank"),
                "category": r.get("category"),
                "type": r.get("type"),
                "display_name": r.get("display_name"),
            }
            for r in response.json()
        ]
        self._cache[key] = results
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        return results

    def close(self) -> None:
        if self._own_client and self._client is not None:
            self._client.close()


def geocode_queries(row: MinistryRow) -> list[str]:
    """Address and place; then, if different, without initials and "ulica" ("A. Šenoe 4").

    Nominatim needs every query word in the result's address, so "A. Šenoe 4" fails
    where "Šenoe 4" finds "Ulica Augusta Šenoe 4". The postcode is left out: the
    search is already bounded to the municipality, and post office areas cross
    municipal borders.
    """
    address = re.sub(r"\b(bb|broj)\b\.?", " ", row.address or "", flags=re.IGNORECASE)
    address = " ".join(address.replace(f"{row.postcode} {row.place}", "").split()).strip(" ,.")
    if not address:
        return [row.place]
    short = re.sub(r"\b\w\.\s*", " ", address)  # initials
    short = " ".join(re.sub(r"\b(ulica|ul\.?)\s", " ", short, flags=re.IGNORECASE).split())
    queries = [f"{address}, {row.place}"]
    if short != address:
        queries.append(f"{short}, {row.place}")
    return queries


# --- assembly ------------------------------------------------------------------------


@dataclass
class Report:
    unmatched_settlements: list[str] = field(default_factory=list)
    municipality_notes: list[str] = field(default_factory=list)
    dedup: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    coarse_geocodes: list[str] = field(default_factory=list)  # village-level results
    fallbacks: list[str] = field(default_factory=list)
    possible_duplicates: list[str] = field(default_factory=list)
    renamed_health: int = 0
    geocode_requests: int = 0

    def log(self) -> None:
        for title, items in (
            ("unmatched settlements", self.unmatched_settlements),
            ("municipality notes", self.municipality_notes),
            ("dropped", self.dropped),
            ("municipality-point fallbacks", self.fallbacks),
            ("possible duplicates", self.possible_duplicates),
        ):
            for item in items:
                log.warning("facilities: %s: %s", title, item)
        for title, items in (
            ("dedup", self.dedup),
            ("village-level geocodes", self.coarse_geocodes),
        ):
            for item in items:
                log.info("facilities: %s: %s", title, item)
        log.info(
            "facilities: %d geocoding requests, %d health names replaced by a generic label",
            self.geocode_requests,
            self.renamed_health,
        )


@dataclass
class Placed:
    """A ministry row with its municipality and location."""

    row: MinistryRow
    settlement: str
    expected: set[str]  # municipalities the row can be in
    fallback: str | None  # municipality whose point is used when geocoding fails
    dzs_code: str | None = None
    lon: float | None = None
    lat: float | None = None
    location_source: str | None = None


class FacilityBuilder:
    def __init__(
        self,
        municipalities: Municipalities,
        settlements: dict[str, set[str]],
        run_ids: dict[str, str],
        geocoder,  # anything with .search(query, viewbox) -> [{"lat","lon","place_rank"}]
        towns: frozenset[str] = frozenset(),  # name_key of each grad's own settlement
    ):
        self.towns = towns
        self.units = municipalities
        self.settlements = settlements
        self.run_ids = run_ids
        self.geocoder = geocoder
        self.report = Report()
        self.rows: list[dict] = []

    # ministry rows: municipality --------------------------------------------------

    def _address_settlement(self, address: str | None) -> str | None:
        """A census settlement named in the address: "Donja Višnjica 156" -> Donja Višnjica."""
        for part in (address or "").split(","):
            candidate = re.match(r"[^\d]*", part).group(0).strip(" .")
            if candidate and name_key(candidate) in self.settlements:
                return candidate
        return None

    def place(self, row: MinistryRow) -> Placed:
        """Municipalities the row can be in, from ``Mjesto`` and a settlement in the address.

        ``Mjesto`` is sometimes the post office town rather than the settlement, so a
        settlement named in the address wins when the two disagree.
        """
        by_place = self.settlements.get(name_key(row.place or ""), set())
        in_address = self._address_settlement(row.address)
        by_address = self.settlements.get(name_key(in_address), set()) if in_address else set()
        if by_address and by_place and not by_address & by_place:
            self.report.municipality_notes.append(
                f"{row.name}: Mjesto {row.place!r} and address settlement {in_address!r} "
                "are in different municipalities"
            )
        if not by_place:
            self.report.unmatched_settlements.append(
                f"{row.place!r} ({row.name})"
                + (f" -> address settlement {in_address!r}" if by_address else "")
            )
        primary = by_address or by_place
        if len(primary) > 1:
            self.report.municipality_notes.append(
                f"{row.name}: settlement {row.place!r} is ambiguous: {sorted(primary)}"
            )
        return Placed(
            row,
            settlement=in_address or row.place,
            expected=(by_address | by_place) or set(self.units.polygons),
            fallback=next(iter(primary)) if len(primary) == 1 else None,
        )

    # ministry rows: coordinates --------------------------------------------------

    def set_osm(self, placed: Placed, feature: OsmFeature) -> None:
        if feature.dzs_code not in placed.expected:
            self.report.municipality_notes.append(
                f"{placed.row.name}: OSM {feature.osm_id} lies in {feature.dzs_code}, "
                f"settlement {placed.settlement!r} suggests {sorted(placed.expected)}; "
                "using the OSM location"
            )
        placed.dzs_code = feature.dzs_code
        placed.lon, placed.lat = feature.lon, feature.lat
        placed.location_source = "osm"

    def geocode(self, placed: Placed) -> None:
        row = placed.row
        viewbox = self.units.viewbox(placed.expected)
        queries = geocode_queries(row)
        if placed.settlement not in queries:
            # Last resort: the settlement itself. Accepted for villages, not for towns.
            queries.append(placed.settlement)
        village = name_key(placed.settlement) not in self.towns
        for query in queries:
            min_rank = SETTLEMENT_RANK if village and query == placed.settlement else MIN_PLACE_RANK
            for result in self.geocoder.search(query, viewbox):
                if (result.get("place_rank") or 0) < min_rank:
                    continue
                lon, lat = result["lon"], result["lat"]
                code = next(
                    (c for c in sorted(placed.expected) if self.units.contains(c, lon, lat)), None
                )
                if code is None:
                    continue
                placed.dzs_code, placed.lon, placed.lat = code, lon, lat
                placed.location_source = "geocoded"
                if result["place_rank"] < 26:
                    self.report.coarse_geocodes.append(f"{row.name} ({query})")
                return
        if placed.fallback is not None:
            code = placed.fallback
            point = self.units.polygons[code].representative_point()
            placed.dzs_code, placed.lon, placed.lat = code, point.x, point.y
            placed.location_source = "municipality_point"
            self.report.fallbacks.append(f"{row.name} ({row.address}, {row.place})")
        else:
            self.report.dropped.append(f"{row.name}: no municipality and no geocoding result")

    def ministry_row(self, placed: Placed, facility_id: str) -> None:
        if placed.dzs_code is None:
            return
        row = placed.row
        self.rows.append(
            {
                "facility_id": facility_id,
                "dzs_code": placed.dzs_code,
                "type": row.type,
                "subtype": row.subtype,
                "name": row.name,
                "address": row.address,
                "settlement": placed.settlement,
                "lat": placed.lat,
                "lon": placed.lon,
                "location_source": placed.location_source,
                "source_run_id": self.run_ids[row.source],
            }
        )

    def osm_row(self, feature: OsmFeature, type_: str, subtype: str, name: str) -> None:
        self.rows.append(
            {
                "facility_id": f"osm:{feature.osm_id}",
                "dzs_code": feature.dzs_code,
                "type": type_,
                "subtype": subtype,
                "name": name,
                "address": feature.address,
                "settlement": feature.settlement,
                "lat": feature.lat,
                "lon": feature.lon,
                "location_source": "osm",
                "source_run_id": self.run_ids[OSM_SOURCE],
            }
        )

    # facility types ---------------------------------------------------------------

    def schools(self, ministry: list[MinistryRow], osm: list[OsmFeature]) -> None:
        by_code: dict[str, MinistryRow] = {}
        for row in ministry:
            if row.code in by_code:
                self.report.dedup.append(
                    f"{row.code} {row.name}: in both the primary and secondary list; "
                    f"kept once as {by_code[row.code].subtype}"
                )
                continue
            by_code[row.code] = row

        osm_by_code: dict[str, list[OsmFeature]] = {}
        for feature in osm:
            osm_by_code.setdefault(feature.tags.get("ref:HR:e-matica"), []).append(feature)

        used: set[str] = set()
        for code, row in by_code.items():
            placed = self.place(row)
            mains = [
                f
                for f in osm_by_code.get(code, [])
                if not BRANCH_SCHOOL.search(ascii_fold(f.name or ""))
            ]
            keys = address_keys(row.address or "")
            by_address = [f for f in mains if f.address and address_key(f.address) in keys]
            main = (by_address or mains or [None])[0]
            if main is not None:
                used.add(main.osm_id)
                self.set_osm(placed, main)
            else:
                self.geocode(placed)
            self.ministry_row(placed, f"mzo:{code}")

        for feature in osm:
            if feature.osm_id in used:
                continue
            code = feature.tags.get("ref:HR:e-matica")
            name = feature.name or "Škola"
            parent = by_code.get(code)
            if BRANCH_SCHOOL.search(ascii_fold(name)):
                subtype = parent.subtype if parent else school_subtype_from_code(code, name)
                self.osm_row(feature, "school", subtype, name)
            elif parent is None:
                self.osm_row(feature, "school", school_subtype_from_code(code, name), name)
                self.report.dedup.append(
                    f"OSM {feature.osm_id} {name} ({code}): not in the ministry list, kept"
                )
            else:
                self.report.dedup.append(
                    f"OSM {feature.osm_id} {name} ({code}): another element of mzo:{code}, dropped"
                )

    def kindergartens(self, ministry: list[MinistryRow], osm: list[OsmFeature]) -> None:
        placed_rows = [self.place(row) for row in ministry]
        cores = {f.osm_id: kindergarten_core(f.name or "") for f in osm}
        consumed: set[str] = set()
        branch_of: dict[str, Placed] = {}  # OSM id -> ministry institution it belongs to

        # 1. Same normalised name in the same municipality.
        for placed in placed_rows:
            core = kindergarten_core(placed.row.name)
            candidates = [
                f
                for f in osm
                if f.osm_id not in consumed
                and f.dzs_code in placed.expected
                and names_match(core, cores[f.osm_id])
            ]
            if not candidates:
                continue
            keys = address_keys(placed.row.address or "")
            by_address = [f for f in candidates if f.address and address_key(f.address) in keys]
            chosen = by_address[0] if by_address else None
            if chosen is None and len(candidates) == 1:
                chosen = candidates[0]
            if chosen is None:
                self.geocode(placed)
                if placed.location_source == "geocoded":
                    near = [
                        (distance_m(f.lon, f.lat, placed.lon, placed.lat), f) for f in candidates
                    ]
                    near = [(d, f) for d, f in near if d < MATCH_DISTANCE_M]
                    chosen = min(near, key=lambda x: x[0])[1] if near else None
            if chosen is not None:
                consumed.add(chosen.osm_id)
                self.set_osm(placed, chosen)
                self.report.dedup.append(
                    f"{placed.row.name} = OSM {chosen.osm_id} {chosen.name!r} (name match)"
                )
            for f in candidates:
                if f is not chosen:
                    branch_of[f.osm_id] = placed

        # 2. The rest: geocode, then the nearest unmatched OSM kindergarten within 300 m.
        for placed in placed_rows:
            if placed.location_source is None:
                self.geocode(placed)
        pairs = []
        for placed in placed_rows:
            if placed.location_source != "geocoded":
                continue
            for f in osm:
                if f.osm_id in consumed or f.osm_id in branch_of or f.dzs_code != placed.dzs_code:
                    continue
                d = distance_m(f.lon, f.lat, placed.lon, placed.lat)
                if d < MATCH_DISTANCE_M:
                    pairs.append((d, id(placed), placed, f))
        matched: set[int] = set()
        for d, key, placed, f in sorted(pairs, key=lambda p: p[:2]):
            if key in matched or f.osm_id in consumed:
                continue
            matched.add(key)
            consumed.add(f.osm_id)
            self.set_osm(placed, f)
            self.report.dedup.append(
                f"{placed.row.name} = OSM {f.osm_id} {f.name!r} ({d:.0f} m from the geocoded "
                "address)"
            )

        ids: set[str] = set()
        for placed in placed_rows:
            facility_id = f"mzo:dv/{slugify(placed.row.place)}/{slugify(placed.row.name)}"
            if facility_id in ids:
                raise ValueError(f"duplicate kindergarten id {facility_id}")
            ids.add(facility_id)
            self.ministry_row(placed, facility_id)

        # 3. OSM kindergartens not matched to a ministry row.
        listed = [(p.lon, p.lat) for p in placed_rows if p.location_source == "osm"]
        for f in osm:
            if f.osm_id in consumed:
                continue
            parent = branch_of.get(f.osm_id)
            if parent is not None and parent.location_source in ("osm", "geocoded"):
                d = distance_m(f.lon, f.lat, parent.lon, parent.lat)
                if d < MATCH_DISTANCE_M:
                    self.report.dedup.append(
                        f"OSM {f.osm_id} {f.name!r}: {d:.0f} m from {parent.row.name}, dropped"
                    )
                    continue
            near = [distance_m(f.lon, f.lat, lon, lat) for lon, lat in listed]
            if not cores[f.osm_id] and near and min(near) < MATCH_DISTANCE_M:
                self.report.dedup.append(
                    f"OSM {f.osm_id} {f.name!r} (unnamed): {min(near):.0f} m from a listed "
                    "kindergarten, dropped"
                )
                continue
            self.osm_row(f, "kindergarten", "kindergarten", f.name or "Dječji vrtić")
            listed.append((f.lon, f.lat))
            if parent is not None:
                self.report.dedup.append(
                    f"OSM {f.osm_id} {f.name!r}: another building of {parent.row.name}, kept"
                )
            else:
                self.report.dedup.append(f"OSM {f.osm_id} {f.name!r}: not in ministry list, kept")
                fallen = [
                    p.row.name
                    for p in placed_rows
                    if p.location_source == "municipality_point" and p.dzs_code == f.dzs_code
                ]
                if fallen:
                    self.report.possible_duplicates.append(
                        f"OSM {f.osm_id} {f.name!r} may be one of {fallen} (not located)"
                    )

    def health(self, osm: list[OsmFeature]) -> None:
        kept: list[tuple[str, frozenset[str], OsmFeature]] = []
        for f in osm:
            subtype = HEALTH_SUBTYPES.get(f.tags.get("amenity")) or HEALTH_SUBTYPES.get(
                f.tags.get("healthcare")
            )
            name = health_name(subtype, f.name, f.tags.get("healthcare:speciality"))
            if f.name and name != f.name:
                self.report.renamed_health += 1
            core = frozenset(t for t in _tokens(name) if t not in {"ljekarna", "ljekarne"})
            twin = next(
                (
                    k
                    for s, c, k in kept
                    if s == subtype
                    and c == core
                    and distance_m(f.lon, f.lat, k.lon, k.lat) < HEALTH_DUPLICATE_M
                ),
                None,
            )
            if twin is not None:
                self.report.dedup.append(
                    f"OSM {f.osm_id} {name!r}: same {subtype} as OSM {twin.osm_id}, dropped"
                )
                continue
            kept.append((subtype, core, f))
            self.osm_row(f, "health", subtype, name)


def osm_features(elements: list[dict], units: Municipalities, report: Report) -> list[OsmFeature]:
    features = []
    for e in elements:
        point = e.get("center") or e
        if "lat" not in point:
            report.dropped.append(f"OSM {e['type']}/{e['id']}: no coordinates")
            continue
        lon, lat = float(point["lon"]), float(point["lat"])
        code = units.locate(lon, lat)
        if code is None:
            report.dropped.append(f"OSM {e['type']}/{e['id']}: outside every municipality")
            continue
        features.append(OsmFeature(f"{e['type']}/{e['id']}", e.get("tags", {}), lon, lat, code))
    return features


def parse_facilities(
    ministry: list[MinistryRow],
    elements: list[dict],
    municipalities: Municipalities,
    settlements: dict[str, set[str]],
    run_ids: dict[str, str],
    geocoder,
    towns: frozenset[str] = frozenset(),
) -> tuple[pl.DataFrame, Report]:
    builder = FacilityBuilder(municipalities, settlements, run_ids, geocoder, towns)
    features = osm_features(elements, municipalities, builder.report)

    def kind(f: OsmFeature) -> str | None:
        for key in ("amenity", "healthcare"):
            value = f.tags.get(key)
            if value in ("school", "kindergarten"):
                return value
            if value in HEALTH_SUBTYPES:
                return "health"
        return None

    builder.schools(
        [r for r in ministry if r.type == "school"], [f for f in features if kind(f) == "school"]
    )
    builder.kindergartens(
        [r for r in ministry if r.type == "kindergarten"],
        [f for f in features if kind(f) == "kindergarten"],
    )
    builder.health([f for f in features if kind(f) == "health"])

    df = conform(pl.DataFrame(builder.rows, schema=FACILITY), "facility")
    check_facilities(df, municipalities)
    builder.report.geocode_requests = getattr(geocoder, "requests", 0)
    return df.sort("dzs_code", "type", "subtype", "name"), builder.report


def check_facilities(df: pl.DataFrame, municipalities: Municipalities) -> None:
    duplicates = df.filter(pl.col("facility_id").is_duplicated())["facility_id"].unique()
    if len(duplicates):
        raise ValueError(f"duplicate facility ids: {duplicates.to_list()}")
    bad_source = set(df["location_source"]) - {"osm", "geocoded", "municipality_point"}
    if bad_source:
        raise ValueError(f"unknown location_source {bad_source}")
    outside = [
        fid
        for fid, code, lon, lat in df.select("facility_id", "dzs_code", "lon", "lat").iter_rows()
        if not municipalities.contains(code, lon, lat)
    ]
    if outside:
        raise AssertionError(f"facilities outside their municipality: {outside}")


def build_facilities_with_report(geocoder=None) -> tuple[pl.DataFrame, Report]:
    sources = load_sources()
    scope = load_scope()
    master = pl.read_csv(config_path("municipalities.csv"), infer_schema_length=0)
    municipalities = read_municipalities(
        sources["dgu_boundaries"].path, set(master["dzs_code"].to_list())
    )
    settlements = settlement_index(
        read_census_settlements(sources["dzs_settlements"].path), master, scope.census_name
    )
    ministry = [
        row
        for source in MINISTRY_SOURCES
        for row in read_ministry(sources[source].path, source, scope.postal_name)
    ]
    run_ids = {source: latest_run_id(source) for source in (*MINISTRY_SOURCES, OSM_SOURCE)}
    own = geocoder is None
    if own:
        geocoder = Geocoder(repo_root() / "data" / "interim" / "geocode_cache.json")
    try:
        df, report = parse_facilities(
            ministry,
            read_osm(sources[OSM_SOURCE].path),
            municipalities,
            settlements,
            run_ids,
            geocoder,
            towns=frozenset(name_key(n) for n in master.filter(pl.col("type") == "grad")["name"]),
        )
    finally:
        if own:
            geocoder.close()
    report.log()
    return df, report


def build_facilities(geocoder=None) -> pl.DataFrame:
    return build_facilities_with_report(geocoder)[0]
