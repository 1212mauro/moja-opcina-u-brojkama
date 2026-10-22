"""Automatic download of every source (task C1): ``opcina fetch``."""

import importlib
import os
import traceback
from datetime import UTC, datetime

from opcina_pipeline.config import load_scope, load_sources, repo_root
from opcina_pipeline.fetch.base import FETCHERS, FetchContext, Outcome, append_run, run_record
from opcina_pipeline.fetch.http import ConditionalCache, PoliteClient

# Modules that register fetchers with @fetcher; importing them fills FETCHERS.
FETCHER_MODULES = ["minfin", "stats", "dgu", "ckan", "osm", "payments"]

# Hosts that rate-limit aggressively get a longer pause between requests.
HOST_INTERVALS = {
    "eojn.hr": 6.0,
    "eojn.nn.hr": 3.0,
    "overpass-api.de": 5.0,
    "overpass.kumi.systems": 5.0,
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
            if fetch is None:
                outcome = Outcome("failed", message="no fetcher registered for this source")
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

    return outcomes
