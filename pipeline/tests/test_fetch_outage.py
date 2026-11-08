"""A source that is down must not block the others while its last files are recent."""

import json
from datetime import UTC, datetime, timedelta

from opcina_pipeline.fetch import STALE_LIMIT_DAYS, blocking_failures, last_success
from opcina_pipeline.fetch.base import Outcome

NOW = datetime(2026, 11, 8, 10, 40, tzinfo=UTC)


def write_log(path, *records):
    path.write_text(
        "".join(json.dumps(r) + "\n" for r in records),
        encoding="utf-8",
    )


def run(source, status, finished):
    return {"source": source, "status": status, "finished_at": finished.isoformat()}


def test_last_success_ignores_failed_runs(tmp_path):
    log = tmp_path / "source_runs.jsonl"
    write_log(
        log,
        run("minfin_budget", "ok", NOW - timedelta(days=2)),
        run("minfin_budget", "unchanged", NOW - timedelta(days=1)),
        run("minfin_budget", "failed", NOW),
    )
    assert last_success(log, "minfin_budget") == (NOW - timedelta(days=1)).isoformat()
    assert last_success(log, "kindergartens") is None
    assert last_success(tmp_path / "missing.jsonl", "minfin_budget") is None


def test_recent_files_turn_a_failure_into_a_warning(tmp_path, capsys):
    log = tmp_path / "source_runs.jsonl"
    write_log(log, run("minfin_budget", "unchanged", NOW - timedelta(days=1)))
    outcomes = {
        "minfin_budget": Outcome("failed", message="ConnectError: reset"),
        "payments": Outcome("ok"),
    }
    assert blocking_failures(outcomes, log, now=NOW) == {}
    assert "minfin_budget is down" in capsys.readouterr().out


def test_old_or_missing_files_block_the_run(tmp_path):
    log = tmp_path / "source_runs.jsonl"
    write_log(log, run("dzs_population", "ok", NOW - timedelta(days=STALE_LIMIT_DAYS + 1)))
    outcomes = {
        "dzs_population": Outcome("failed", message="ConnectError: reset"),
        "kindergartens": Outcome("failed", message="ConnectError: reset"),
        "contracts_eojn": Outcome("skipped", message="no API key"),
    }
    blocking = blocking_failures(outcomes, log, now=NOW)
    assert set(blocking) == {"dzs_population", "kindergartens"}
    assert "over 7 days" in blocking["dzs_population"]
    assert blocking["kindergartens"] == "no earlier successful download"
