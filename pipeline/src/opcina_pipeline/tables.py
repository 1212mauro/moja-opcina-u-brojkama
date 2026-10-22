"""Schemas of the clean tables parsers write to ``data/interim/<table>.parquet``.

These follow the data model in SPEC.md. Every row is tied to one municipality by
``dzs_code`` (the master table's key) and to the fetch it came from by
``source_run_id`` (an id from ``data/raw/source_runs.jsonl``). Amounts are euro;
pre-2023 kuna amounts are converted once, at parse time, at the fixed rate, and the
original text is kept for audit.
"""

import json
from pathlib import Path

import polars as pl

from opcina_pipeline.config import repo_root

HRK_PER_EUR = 7.53450  # fixed conversion rate, Croatia's euro changeover 2023-01-01

POPULATION = {
    "dzs_code": pl.Utf8,
    "year": pl.Int32,
    "kind": pl.Utf8,  # "census" | "estimate"
    "total": pl.Int64,
    "source_run_id": pl.Utf8,
}

BUDGET_LINE = {
    "dzs_code": pl.Utf8,
    "year": pl.Int32,
    "period": pl.Utf8,  # "FY" (I-XII)
    "classification": pl.Utf8,  # "economic" | "function" | "derived"
    "code": pl.Utf8,  # account ("611"), COFOG ("091") or derived position ("X067")
    "level": pl.Int8,  # digits of the code (1-4); 0 for derived positions
    "label": pl.Utf8,
    "amount_eur": pl.Float64,
    "source_run_id": pl.Utf8,
}

CONTRACT = {
    "contract_key": pl.Utf8,  # unique: "<system>:<id>"
    "system": pl.Utf8,  # "eojn_legacy" | "eojn" | "municipal"
    "dzs_code": pl.Utf8,  # municipality the buyer belongs to
    "buyer_oib": pl.Utf8,
    "buyer_name": pl.Utf8,
    "buyer_kind": pl.Utf8,  # "unit" | "budget_user"
    "subject": pl.Utf8,
    "cpv": pl.Utf8,  # 8 digits, nullable
    "procedure": pl.Utf8,
    "contract_number": pl.Utf8,
    "supplier_name": pl.Utf8,
    "supplier_oib": pl.Utf8,  # nullable
    "signed_on": pl.Date,
    "value_eur": pl.Float64,  # without VAT
    "value_with_vat_eur": pl.Float64,  # nullable
    "value_original": pl.Utf8,  # as published, e.g. "25.000,00 HRK"
    "currency_original": pl.Utf8,  # "EUR" | "HRK"
    "source_run_id": pl.Utf8,
}

PAYMENT = {
    "dzs_code": pl.Utf8,
    "paid_on": pl.Date,
    "month": pl.Utf8,  # "YYYY-MM"
    "payer_name": pl.Utf8,  # the municipality or one of its budget users
    "recipient_name": pl.Utf8,  # null for natural persons
    "recipient_oib": pl.Utf8,  # legal persons only, else null
    "natural_person": pl.Boolean,
    "economic_code": pl.Utf8,  # account, e.g. "3232"
    "economic_label": pl.Utf8,
    "function_code": pl.Utf8,  # COFOG, nullable (not every platform publishes it)
    "description": pl.Utf8,  # nullable
    "amount_eur": pl.Float64,
    "source_run_id": pl.Utf8,
}

FACILITY = {
    "facility_id": pl.Utf8,  # stable: "<source>:<id>", e.g. "mzo:05-086-508", "osm:node/123"
    "dzs_code": pl.Utf8,
    "type": pl.Utf8,  # "school" | "kindergarten" | "health"
    "subtype": pl.Utf8,  # e.g. "primary", "secondary", "pharmacy", "hospital"
    "name": pl.Utf8,
    "address": pl.Utf8,  # nullable
    "settlement": pl.Utf8,  # nullable
    "lat": pl.Float64,
    "lon": pl.Float64,
    "location_source": pl.Utf8,  # "osm" | "geocoded" | "settlement_centroid"
    "source_run_id": pl.Utf8,
}

TABLES = {
    "population": POPULATION,
    "budget_line": BUDGET_LINE,
    "contract": CONTRACT,
    "payment": PAYMENT,
    "facility": FACILITY,
}


def interim_path(table: str) -> Path:
    return repo_root() / "data" / "interim" / f"{table}.parquet"


def conform(df: pl.DataFrame, table: str) -> pl.DataFrame:
    """Columns of ``table`` in schema order with schema types; raises on missing columns."""
    schema = TABLES[table]
    missing = set(schema) - set(df.columns)
    if missing:
        raise ValueError(f"{table}: missing columns {sorted(missing)}")
    return df.select([pl.col(name).cast(dtype, strict=True) for name, dtype in schema.items()])


def write_table(df: pl.DataFrame, table: str) -> Path:
    path = interim_path(table)
    path.parent.mkdir(parents=True, exist_ok=True)
    conform(df, table).write_parquet(path)
    return path


def read_table(table: str) -> pl.DataFrame:
    return pl.read_parquet(interim_path(table))


def latest_run_id(source: str, log_path: Path | None = None) -> str:
    """Id of the newest successful fetch of ``source`` (ok or unchanged)."""
    log_path = log_path or repo_root() / "data" / "raw" / "source_runs.jsonl"
    latest = None
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            if record["source"] == source and record["status"] in ("ok", "unchanged"):
                latest = record["id"]
    if latest is None:
        raise LookupError(f"no successful fetch of {source!r}; run `opcina fetch {source}`")
    return latest
