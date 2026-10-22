"""Fetcher registry, context and run log.

A fetcher is a function ``(ctx) -> Outcome`` registered under a source key from
``config/sources.toml``. It only downloads: parsing happens in later steps.
Every run appends one line per source to ``data/raw/source_runs.jsonl``, which
is the provenance every figure on the site points back to.
"""

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import polars as pl

from opcina_pipeline.config import Scope, Source, config_path
from opcina_pipeline.fetch.http import Download, PoliteClient

Status = Literal["ok", "unchanged", "skipped", "unavailable", "failed"]


@dataclass
class Outcome:
    """What a fetcher did.

    ``skipped``: could run but a precondition is missing (e.g. no API key).
    ``unavailable``: the publisher offers no machine-readable route (reported, not an error).
    """

    status: Status
    files: list[Download] = field(default_factory=list)
    message: str = ""

    @classmethod
    def from_downloads(cls, files: list[Download], message: str = "") -> "Outcome":
        status: Status = "ok" if any(f.changed for f in files) else "unchanged"
        return cls(status, files, message)


@dataclass
class FetchContext:
    source: Source
    client: PoliteClient
    scope: Scope
    raw_dir: Path

    @property
    def out_dir(self) -> Path:
        """Directory this source writes to (``data/raw/<source key>/``)."""
        path = self.raw_dir / self.source.key
        path.mkdir(parents=True, exist_ok=True)
        return path

    def master(self) -> pl.DataFrame:
        """The municipality master table: who is in scope, with OIBs and codes."""
        return pl.read_csv(config_path("municipalities.csv"), infer_schema_length=0)

    @property
    def ignore_parts(self) -> frozenset[str]:
        """Workbook parts that change on every download (``ignore_parts`` in sources.toml)."""
        return frozenset(self.source.options.get("ignore_parts", []))

    @staticmethod
    def secret(name: str) -> str | None:
        """Credentials come from the environment (GitHub Actions secrets), never from config."""
        return os.environ.get(name) or None


Fetcher = Callable[[FetchContext], Outcome]
FETCHERS: dict[str, Fetcher] = {}


def fetcher(key: str) -> Callable[[Fetcher], Fetcher]:
    def register(fn: Fetcher) -> Fetcher:
        if key in FETCHERS:
            raise ValueError(f"two fetchers registered for {key!r}")
        FETCHERS[key] = fn
        return fn

    return register


@dataclass
class RunRecord:
    id: str
    source: str
    started_at: str
    finished_at: str
    status: Status
    message: str
    files: list[dict]


def run_record(source: str, started: datetime, outcome: Outcome, raw_dir: Path) -> RunRecord:
    finished = datetime.now(UTC)
    return RunRecord(
        id=f"{source}-{started:%Y%m%dT%H%M%SZ}",
        source=source,
        started_at=started.isoformat(timespec="seconds"),
        finished_at=finished.isoformat(timespec="seconds"),
        status=outcome.status,
        message=outcome.message,
        files=[
            {
                "path": f.path.relative_to(raw_dir).as_posix(),
                "sha256": f.sha256,
                "bytes": f.bytes,
                "changed": f.changed,
            }
            for f in outcome.files
        ],
    )


def append_run(log_path: Path, record: RunRecord) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
