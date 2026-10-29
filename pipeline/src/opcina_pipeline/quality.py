"""Quality gate (task C10): staged tables are published only if they pass.

For every table in ``data/interim/staging/``:

- the schema matches ``tables.TABLES`` exactly;
- the row count is within ±20 % of the last published version (first run: no limit);
- the table's own checks pass (uniqueness, reconciliation, personal-data rules).

A passing table is copied to ``data/interim/published/``; a failing one is not, so
the website keeps showing the last good data. The run writes
``data/interim/quality_report.json`` and fails when any table failed, which makes
the nightly job email the maintainer.
"""

import json
import shutil
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime

import polars as pl

from opcina_pipeline.config import config_path, repo_root
from opcina_pipeline.tables import TABLES, interim_path

ROW_TOLERANCE = 0.20

Check = Callable[[pl.DataFrame], list[str]]


@dataclass
class TableResult:
    table: str
    rows: int
    previous_rows: int | None
    problems: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.problems


def unique(*columns: str) -> Check:
    def check(df: pl.DataFrame) -> list[str]:
        dupes = df.height - df.unique(list(columns)).height
        return [f"{dupes} duplicate rows on {', '.join(columns)}"] if dupes else []

    return check


def no_nulls(*columns: str) -> Check:
    def check(df: pl.DataFrame) -> list[str]:
        return [f"{c}: {n} empty values" for c in columns if (n := df[c].null_count())]

    return check


def every_unit_present(df: pl.DataFrame) -> list[str]:
    units = set(pl.read_csv(config_path("municipalities.csv"), infer_schema_length=0)["dzs_code"])
    missing = units - set(df["dzs_code"])
    return [f"no rows for {sorted(missing)}"] if missing else []


def natural_persons_anonymous(df: pl.DataFrame) -> list[str]:
    """GDPR: payments to natural persons never carry a name or OIB."""
    leaked = df.filter(
        pl.col("natural_person")
        & (pl.col("recipient_name").is_not_null() | pl.col("recipient_oib").is_not_null())
    )
    return [f"{leaked.height} natural-person payments carry a name or OIB"] if leaked.height else []


def in_croatia(df: pl.DataFrame) -> list[str]:
    outside = df.filter(
        ~pl.col("lat").is_between(42.3, 46.6) | ~pl.col("lon").is_between(13.4, 19.5)
    )
    return [f"{outside.height} facilities outside Croatia"] if outside.height else []


TABLE_CHECKS: dict[str, list[Check]] = {
    "population": [
        unique("dzs_code", "year", "kind"),
        no_nulls("dzs_code", "year", "total"),
        every_unit_present,
    ],
    "budget_line": [
        unique("dzs_code", "year", "period", "classification", "code"),
        no_nulls("dzs_code", "year", "code", "amount_eur"),
        every_unit_present,
    ],
    "contract": [
        unique("contract_key"),
        # Some old-register contracts publish no amount, and annexes ("Dodatak") can
        # lower a contract, so value_eur may be empty or negative.
        no_nulls("dzs_code", "buyer_oib"),
    ],
    "payment": [
        no_nulls("dzs_code", "paid_on", "amount_eur"),
        natural_persons_anonymous,
    ],
    "facility": [
        unique("facility_id"),
        no_nulls("dzs_code", "type", "name", "lat", "lon"),
        in_croatia,
    ],
}


def check_table(
    table: str,
    staged: pl.DataFrame,
    published: pl.DataFrame | None,
    extra_checks: list[Check] = (),
    accept_row_change: bool = False,
) -> TableResult:
    """``accept_row_change``: skip the ±20 % check once, for an expected step change
    (a new municipality or source, a backfill); every other check still applies."""
    result = TableResult(table, staged.height, published.height if published is not None else None)
    expected = TABLES[table]
    if dict(staged.schema) != expected:
        result.problems.append(f"schema differs: {dict(staged.schema)} != {expected}")
        return result
    if staged.height == 0:
        result.problems.append("table is empty")
    if published is not None and published.height and not accept_row_change:
        change = staged.height / published.height - 1
        if abs(change) > ROW_TOLERANCE:
            result.problems.append(
                f"row count {published.height} -> {staged.height} ({change:+.0%}), "
                f"beyond ±{ROW_TOLERANCE:.0%}"
            )
    for check in [*TABLE_CHECKS.get(table, []), *extra_checks]:
        result.problems.extend(check(staged))
    return result


def run_gate(
    tables: list[str] | None = None,
    extra_checks: dict[str, list[Check]] | None = None,
    accept: set[str] = frozenset(),
) -> list[TableResult]:
    """Check every staged table, publish the ones that pass, write the report."""
    results = []
    for table in tables or list(TABLES):
        staged_path = interim_path(table, "staging")
        if not staged_path.exists():
            continue
        published_path = interim_path(table, "published")
        published = pl.read_parquet(published_path) if published_path.exists() else None
        result = check_table(
            table,
            pl.read_parquet(staged_path),
            published,
            (extra_checks or {}).get(table, []),
            accept_row_change=table in accept,
        )
        if result.passed:
            published_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(staged_path, published_path)
        results.append(result)

    report = repo_root() / "data" / "interim" / "quality_report.json"
    report.write_text(
        json.dumps(
            {
                "checked_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "tables": [{**asdict(r), "passed": r.passed} for r in results],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return results
