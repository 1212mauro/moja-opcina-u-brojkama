"""Grad Varaždin's payments, from the official CSV export the city was asked for.

The portal's search (transparentni.varazdin.hr) is checked with reCAPTCHA v3 and is never
used. In November 2026 the city named ``/Pretraga/GetExport/`` as its access point for
programmatic export: the search criteria go in the URL, ``exportType`` picks the format.
That address is ``url`` in Varaždin's entry in payments.toml (the ``official_csv``
platform). An answer that is not a payments export is noted and skipped.

The export is expected in the portal's CSV layout (``EXPORT_COLUMNS``); if the official
one differs, ``read_export`` is the place to adapt. Each run cleans what it downloads with
the payment privacy rules (``parse.payments.finish``) into one file per month.
"""

import csv
import html
import io
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import polars as pl

DZS_CODE = "04723"
EXPORT_COLUMNS = [
    "Rbr",
    "Datum isplate",
    "Isplatitelj",
    "Primatelj",
    "PTT broj",
    "Sjedište primatelja",
    "OIB",
    "Iznos isplate",
    "Valuta",
    "Svrha isplate",
    "Vrsta rashoda/izdatka",
]
_SEVERAL_ACCOUNTS = re.compile(r",\s*(?=\d{4}\s)")
_ENTITY = re.compile(r"&(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);")

# Columns of the cleaned monthly files: only what the site may publish.
CLEANED_COLUMNS = [
    "paid_on",
    "payer_name",
    "recipient_name",
    "recipient_oib",
    "economic_code",
    "economic_label",
    "amount_eur",
]


# --- Reading the export -----------------------------------------------------------------


@dataclass(frozen=True)
class ExportRow:
    number: int  # "Rbr", the row number in the result list
    paid_on: date
    payer: str
    recipient: str
    oib: str
    amount_eur: float
    expense: str  # "3222 Materijal i sirovine"


def read_export(path: Path) -> list[ExportRow]:
    """One downloaded export; an empty answer is no rows, any other layout is refused.

    Names come HTML-escaped and unquoted ("ŠMEK&amp;SNACK j.d.o.o."), so the ";" of an
    entity would split the field: entities are decoded before the line is split.
    """
    text = _ENTITY.sub(lambda m: html.unescape(m.group(0)), path.read_text(encoding="utf-8-sig"))
    with io.StringIO(text, newline="") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader, None)
        if header is None:
            return []
        if header != EXPORT_COLUMNS:
            raise ValueError(f"{path.name}: not the payments export layout (header {header})")
        rows = []
        for cells in reader:
            if not any(cell.strip() for cell in cells):
                continue
            # Some rows end with a stray ";" (an empty 12th field); real extra data is refused.
            while len(cells) > len(EXPORT_COLUMNS) and not cells[-1].strip():
                cells = cells[:-1]
            row = dict(zip(EXPORT_COLUMNS, cells, strict=True))
            if row["Valuta"].strip() != "EUR":
                raise ValueError(f"{path.name}: row {row['Rbr']} is not in euro")
            stamp = row["Datum isplate"].strip()
            rows.append(
                ExportRow(
                    number=int(row["Rbr"]),
                    paid_on=date(int(stamp[:4]), int(stamp[4:6]), int(stamp[6:8])),
                    payer=" ".join(row["Isplatitelj"].split()),
                    recipient=" ".join(row["Primatelj"].split()),
                    oib=row["OIB"].strip(),
                    amount_eur=float(row["Iznos isplate"].replace(".", "").replace(",", ".")),
                    expense=" ".join(row["Vrsta rashoda/izdatka"].split()),
                )
            )
    return rows


def raw_frame(rows: list[ExportRow]) -> pl.DataFrame:
    """Export rows in the columns every payment parser returns (``parse.payments.RAW_COLUMNS``)."""
    from opcina_pipeline.parse.payments import RAW_COLUMNS, split_code

    records = []
    for row in rows:
        # Payroll rows list several accounts in one field ("3111 Plaće za redovan rad,
        # 3121 Ostali rashodi za zaposlene, ..."): the first one stands for the row.
        code, label = split_code(_SEVERAL_ACCOUNTS.split(row.expense)[0])
        records.append(
            {
                "paid_on": row.paid_on,
                "payer_name": row.payer,
                "recipient_name": row.recipient or None,
                "recipient_oib": row.oib or None,
                "economic_code": code,
                "economic_label": label,
                "function_code": None,
                "description": None,  # "Svrha isplate" can name people
                "amount_eur": row.amount_eur,
            }
        )
    return pl.DataFrame(records, schema=RAW_COLUMNS)


def write_cleaned(
    rows_by_month: dict[str, list[ExportRow]], out_dir: Path, known: frozenset[str]
) -> dict[str, int]:
    """Write what the site may publish to ``out_dir/<YYYY-MM>.csv``; rows written per month."""
    from opcina_pipeline.parse.payments import finish

    out_dir.mkdir(parents=True, exist_ok=True)
    months = {}
    for month in sorted(rows_by_month):
        cleaned = finish(raw_frame(rows_by_month[month]), DZS_CODE, "official", known)
        cleaned.select(CLEANED_COLUMNS).sort("paid_on", "payer_name", "recipient_name").write_csv(
            out_dir / f"{month}.csv"
        )
        months[month] = cleaned.height
    return months


# --- The official endpoint --------------------------------------------------------------


def official_urls(template: str, months: list[str]) -> dict[str, str]:
    """One URL per month when ``template`` has ``{year}``/``{month}``, else one URL."""
    if any(field in template for field in ("{year}", "{month}", "{month_int}")):
        return {m: template.format(year=m[:4], month=m[5:7], month_int=int(m[5:7])) for m in months}
    return {"all": template}


@dataclass
class OfficialResult:
    months: dict[str, int]  # month -> cleaned rows written
    notes: list[str]
    files: list  # raw downloads (fetch.http.Download)


def fetch_official(
    client,
    template: str,
    months: list[str],
    raw_dir: Path,
    out_dir: Path,
    known: frozenset[str],
    max_rows: int | None = None,
) -> OfficialResult:
    """Download the export(s) into ``raw_dir`` and clean them into ``out_dir``.

    Months already in ``out_dir`` and not in this answer stay as they are, so a night the
    endpoint answers badly keeps the last good months.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows: dict[str, dict[ExportRow, ExportRow]] = {}
    notes, files = [], []
    for key, url in official_urls(template, months).items():
        download = client.download(url, raw_dir / f"{key}.csv")
        files.append(download)
        try:
            found = read_export(download.path)
        except (ValueError, UnicodeDecodeError) as error:
            notes.append(f"{url} is not a payments export yet ({error})"[:300])
            continue
        if max_rows and len(found) >= max_rows:
            notes.append(
                f"{key}: {len(found)} rows, the request limit; the answer may be cut short"
            )
        for row in found:  # the same row in two answers counts once
            rows.setdefault(f"{row.paid_on:%Y-%m}", {}).setdefault(row, row)
    written = write_cleaned({m: list(r) for m, r in rows.items()}, out_dir, known)
    return OfficialResult(written, notes, files)
