"""Monthly payment disclosures (Naputak, NN 59/23), one connector per publishing platform.

``config/payments.toml`` says which platform each municipality uses; adding a
municipality on a supported platform is a config change. Files go to
``data/raw/payments/<dzs_code>/``.
"""

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from opcina_pipeline.config import config_path
from opcina_pipeline.fetch.base import FetchContext, Outcome, fetcher
from opcina_pipeline.fetch.http import Download
from opcina_pipeline.fetch.links import find_links

OTVORENIGRAD_API = "https://api.otvorenigrad.hr/itransparentnost/isplate"
# Months this recent are fetched again on every run: late corrections still land there.
REFRESH_MONTHS = 2
# On html_links pages, this many newest files are fetched again on every run.
REFRESH_FILES = 2


def load_platforms() -> dict[str, dict]:
    import tomllib

    return tomllib.loads(config_path("payments.toml").read_text(encoding="utf-8"))


def _today() -> date:
    return date.today()  # patched in tests


def month_starts(today: date, count: int) -> list[date]:
    """First days of the last ``count`` months, oldest first, including the current month."""
    starts = []
    year, month = today.year, today.month
    for _ in range(count):
        starts.append(date(year, month, 1))
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return starts[::-1]


def next_month(start: date) -> date:
    return date(start.year + start.month // 12, start.month % 12 + 1, 1)


def fetch_otvorenigrad(ctx: FetchContext, entry: dict, dest: Path) -> list[Download]:
    """iTransparentnost API: one CSV per month. The upper date bound is exclusive."""
    starts = month_starts(_today(), ctx.source.options["months"])
    refresh_from = starts[-REFRESH_MONTHS]
    files = []
    for start in starts:
        target = dest / f"{start:%Y-%m}.csv"
        # Empty months (nothing published yet) are always asked again: late publishing.
        if target.exists() and target.stat().st_size and start < refresh_from:
            continue
        filters = {
            "datum": {"values": [start.isoformat(), next_month(start).isoformat()], "op": "BETWEEN"}
        }
        download = ctx.client.download(
            OTVORENIGRAD_API,
            target,
            params={"lang": "hr", "format": "csv", "filters": json.dumps(filters)},
            headers={"LC-Tenant": entry["tenant"]},
        )
        # An empty body is a month with nothing published yet (the platform syncs daily).
        head = download.path.read_bytes()[:200].decode("utf-8-sig", "replace")
        if download.bytes and "Naziv isplatitelja" not in head:
            raise ValueError(f"{entry['tenant']} {start:%Y-%m}: response is not the payments CSV")
        files.append(download)
    return files


def fetch_kipos(ctx: FetchContext, entry: dict, dest: Path) -> list[Download]:
    """Kipos portal search: returns every payment since the portal started, as JSON.

    Only the portal's own documented search call is used, with fixed parameters.
    """
    download = ctx.client.download(
        f"{entry['base_url'].rstrip('/')}/dbapi.php",
        dest / "payments.json",
        params={
            "radim": "search",
            "idz": "m/trans",
            "godina": "sve godine",
            "oib": "svi",
            "datumOd": "",
            "datumDo": "",
        },
    )
    rows = json.loads(download.path.read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{entry['base_url']}: expected a non-empty JSON list of payments")
    return [download]


def fetch_html_links(ctx: FetchContext, entry: dict, dest: Path) -> list[Download]:
    """Files linked from one page; files already on disk are kept, the newest refreshed.

    Local files the page no longer links (a renamed or corrected upload) are removed,
    so the folder always mirrors what the municipality currently publishes.
    """
    page_url = entry["page"]
    links = find_links(ctx.client.get(page_url).text, entry["pattern"], page_url)
    if not links:
        raise ValueError(f"no links matching {entry['pattern']!r} on {page_url}")
    names = [unquote(PurePosixPath(urlsplit(url).path).name) for url in links]
    if len(set(names)) != len(names):
        raise ValueError(f"two linked files share a name on {page_url}: {names}")
    if dest.exists():
        for stale in dest.iterdir():
            if stale.is_file() and stale.name not in names:
                stale.unlink()
    refresh = set(sorted(names, key=_month_key)[-REFRESH_FILES:])
    files = []
    for url, name in zip(links, names, strict=True):
        target = dest / name
        if target.exists() and name not in refresh:
            continue
        files.append(ctx.client.download(url, target))
    return files


def _month_key(name: str) -> str:
    """Sort key for names ending in "MM-YY": "..._04-26.ods" -> "26-04"."""
    stem = PurePosixPath(name).stem
    month, _, year = stem.rpartition("_")[2].partition("-")
    return f"{year}-{month}" if month.isdigit() and year.isdigit() else stem


PLATFORMS: dict[str, Callable[[FetchContext, dict, Path], list[Download]]] = {
    "otvorenigrad": fetch_otvorenigrad,
    "kipos": fetch_kipos,
    "html_links": fetch_html_links,
}


@fetcher("payments")
def fetch_payments(ctx: FetchContext) -> Outcome:
    platforms = load_platforms()
    in_scope = set(ctx.master()["dzs_code"])
    unknown = set(platforms) - in_scope
    if unknown:
        raise ValueError(f"payments.toml lists codes outside the master table: {sorted(unknown)}")

    files: list[Download] = []
    notes, failures = [], []
    for code, entry in sorted(platforms.items()):
        platform = entry["platform"]
        if platform == "unavailable":
            notes.append(f"{code} unavailable")
            continue
        try:
            unit_files = PLATFORMS[platform](ctx, entry, ctx.out_dir / code)
        except Exception as error:  # noqa: BLE001 - one municipality must not stop the rest
            failures.append(f"{code} {platform}: {type(error).__name__}: {error}")
            continue
        files.extend(unit_files)
        notes.append(
            f"{code} {platform} {sum(f.changed for f in unit_files)}/{len(unit_files)} new"
        )

    not_configured = sorted(in_scope - set(platforms))
    if not_configured:
        notes.append(f"{len(not_configured)} units not configured")
    message = "; ".join(failures + notes)
    if failures:
        return Outcome("failed", files, message)
    return Outcome.from_downloads(files, message)
