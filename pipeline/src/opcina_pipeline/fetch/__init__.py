"""Automatic download of every source (task C1): ``opcina fetch``."""

import importlib
import json
import os
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path

from opcina_pipeline.config import load_scope, load_sources, repo_root
from opcina_pipeline.fetch.base import FETCHERS, FetchContext, Outcome, append_run, run_record
from opcina_pipeline.fetch.http import ConditionalCache, PoliteClient

# Modules that register fetchers with @fetcher; importing them fills FETCHERS.
FETCHER_MODULES = ["minfin", "stats", "dgu", "ckan", "osm", "payments", "eojn", "ted"]

# Hosts that rate-limit aggressively get a longer pause between requests.
HOST_INTERVALS = {
    "eojn.hr": 6.0,
    "eojn.nn.hr": 3.0,
    "overpass-api.de": 5.0,
    "overpass.kumi.systems": 5.0,
    "api.ted.europa.eu": 1.0,
    "ted.europa.eu": 1.0,
}


def load_fetchers() -> None:
    for module in FETCHER_MODULES:
        importlib.import_module(f"opcina_pipeline.fetch.{module}")


def run_fetch(only: list[str] | None = None) -> dict[str, Outcome]:
    """Fetch the given sources (default: all). One failing source does not stop the others."""
    load_fetchers()
    sources = load_sources()
    keys = only or list(sources)
    unknown = [k for k in keys if k not in sources]
    if unknown:
        raise SystemExit(f"unknown sources: {unknown}; known: {sorted(sources)}")

    raw_dir = repo_root() / "data" / "raw"
    log_path = raw_dir / "source_runs.jsonl"
    cache = ConditionalCache(raw_dir / ".http_cache.json")
    outcomes: dict[str, Outcome] = {}

    with PoliteClient(cache=cache, host_intervals=HOST_INTERVALS) as client:
        for key in keys:
            started = datetime.now(UTC)
            fetch = FETCHERS.get(key)
            recent = recently_fetched(log_path, key, sources[key].options.get("refresh_days"))
            if fetch is None:
                outcome = Outcome("failed", message="no fetcher registered for this source")
            elif recent and not only:
                outcome = Outcome(
                    "skipped", message=f"last fetched {recent}; refresh_days not reached"
                )
            else:
                ctx = FetchContext(sources[key], client, load_scope(), raw_dir)
                try:
                    outcome = fetch(ctx)
                except Exception as error:  # noqa: BLE001 - one source must not stop the rest
                    outcome = Outcome("failed", message=f"{type(error).__name__}: {error}")
                    traceback.print_exc()
            append_run(log_path, run_record(key, started, outcome, raw_dir))
            outcomes[key] = outcome
            print(
                f"{key:<24} {outcome.status:<11} {len(outcome.files):>3} files  {outcome.message}"
            )

    write_step_summary(outcomes)
    return outcomes


# A source that is down keeps its last good files (the website says so). After this
# many days without a successful download it also turns the nightly job red, which
# emails the maintainer. It never holds back other sources: see deploy.yml.
STALE_LIMIT_DAYS = 7


def last_success(log_path: Path, key: str) -> str | None:
    """Finish time of the last run of this source that got its files ("ok"/"unchanged")."""
    if not log_path.exists():
        return None
    last = None
    for line in log_path.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        if record["source"] == key and record["status"] in ("ok", "unchanged"):
            last = record["finished_at"]
    return last


def overdue_failures(
    outcomes: dict[str, Outcome], log_path: Path, now: datetime | None = None
) -> dict[str, str]:
    """Failed sources that need the maintainer's attention, with the reason.

    Every failed source keeps the files of its last successful download, the build
    uses them, and the website marks the source as "last download failed, showing
    previous data"; every other source still updates. A failure is only reported as
    overdue when the source has no good files at all, or none newer than
    ``STALE_LIMIT_DAYS``. Shorter outages are warnings on the run page.
    """
    now = now or datetime.now(UTC)
    overdue = {}
    for key, outcome in outcomes.items():
        if outcome.status != "failed":
            continue
        last = last_success(log_path, key)
        if last is None:
            overdue[key] = "no earlier successful download"
        elif now - datetime.fromisoformat(last) > timedelta(days=STALE_LIMIT_DAYS):
            overdue[key] = f"last successful download {last}, over {STALE_LIMIT_DAYS} days ago"
        else:
            warn(f"{key} is down ({outcome.message}); using the files downloaded {last}")
    return overdue


def warn(text: str) -> None:
    """A warning on the GitHub Actions run page (plain output elsewhere)."""
    prefix = "::warning title=Source down::" if os.environ.get("GITHUB_ACTIONS") else "warning: "
    print(prefix + text)


def recently_fetched(log_path: Path, key: str, refresh_days: int | None) -> str | None:
    """Finish time of the last successful run if it is newer than ``refresh_days``.

    Slow sources that rarely change (the old EOJN register: ~20 minutes of polite
    requests) set ``refresh_days`` so the nightly run fetches them only weekly.
    Naming the source explicitly (``opcina fetch <key>``) always fetches it.
    """
    if not refresh_days:
        return None
    last = last_success(log_path, key)
    if last and datetime.now(UTC) - datetime.fromisoformat(last) < timedelta(days=refresh_days):
        return last
    return None


def write_step_summary(outcomes: dict[str, Outcome]) -> None:
    """Markdown table on the GitHub Actions run page (no-op elsewhere)."""
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    lines = ["| Source | Status | Files | Note |", "| --- | --- | --- | --- |"]
    for key, outcome in outcomes.items():
        note = outcome.message.replace("|", "\\|")
        lines.append(f"| `{key}` | {outcome.status} | {len(outcome.files)} | {note} |")
    with open(summary, "a", encoding="utf-8") as f:
        f.write("## Source fetch\n\n" + "\n".join(lines) + "\n")
