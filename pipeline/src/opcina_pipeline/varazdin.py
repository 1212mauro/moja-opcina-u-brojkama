"""Grad Varaždin's payments, from CSV exports a person saves by hand.

transparentni.varazdin.hr checks every search with reCAPTCHA v3, so the pipeline never
requests anything from it. Once a month someone opens the portal's export link in their
own browser (``opcina varazdin-link 2026-10`` prints it) and saves the CSV into
``data/inbox/varazdin/``. Then, on any local run (``opcina fetch payments`` or
``opcina import-varazdin``):

1. every CSV in the inbox and in ``done/`` is read (export layout: ``EXPORT_COLUMNS``) and
   its rows are grouped by payment month, so saving a page twice or a month in several
   pages is fine: exact duplicate rows collapse;
2. each month is checked: gaps in the row numbers and a first payment late in the month
   (pages not saved) are reported;
3. the payment privacy rules (``parse.payments.finish``) are applied and only what the
   site may publish is written to ``pipeline/manual/payments/04723/<YYYY-MM>.csv``, which
   is committed to git: no names or OIBs of individuals, no descriptions;
4. new inbox files move to ``done/`` (git-ignored, kept so a month can be rebuilt).

The ``manual`` payments platform copies the cleaned files into ``data/raw`` on every
run, locally and in the nightly job, which never sees the inbox.
"""

import csv
import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from urllib.parse import quote

import polars as pl

from opcina_pipeline.config import repo_root

DZS_CODE = "04723"
OIB = "13269011531"
INBOX = Path("data") / "inbox" / "varazdin"
CLEANED = Path("pipeline") / "manual" / "payments" / DZS_CODE

EXPORT_URL = "https://transparentni.varazdin.hr/Pretraga/GetExport/{query}?exportType=1"
PAGE_SIZE = 80  # rows per page, as the portal's own table loads them
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


def export_link(month: str, page: int = 1) -> str:
    """The portal's CSV export link for ``month`` ("YYYY-MM"), all payers, one page.

    The same link the portal's "CSV" button carries after a search, for opening in a
    browser by hand. The pipeline itself never requests it.
    """
    year, mon = (int(part) for part in month.split("-"))
    params = {
        "Godine": year,
        "Mjeseci": mon,
        "Uprave": 0,
        "Poslovnice": "",
        "VrsteIzdataka": "",
        "GodinaIsplate": "",
        "IbanIsplate": "",
        "OIBPrimatelja": "",
        "NazivPrimatelja": "",
        "MjestoPrimatelja": "",
        "PTTPrimatelja": "",
        "OpisIsplate": "",
        "IznosObveze": "",
        "OpisKnjizenja": "",
        "IznosIsplateOd": "",
        "IznosIsplateDo": "",
        "Valuta": 191,  # euro
        "IsplataUplata": 10,
        "preskoci": (page - 1) * PAGE_SIZE,
        "uzmi": PAGE_SIZE,
        "RazdobljeOd": "",
        "RazdobljeDo": "",
    }
    query = "&".join(f"{key}={value}" for key, value in params.items())
    return EXPORT_URL.format(query=quote(query, safe=""))


# --- Reading exports --------------------------------------------------------------------


@dataclass(frozen=True)
class ExportRow:
    number: int  # "Rbr", the row number in the portal's result list
    paid_on: date
    payer: str
    recipient: str
    oib: str
    amount_eur: float
    expense: str  # "3222 Materijal i sirovine"
    file: str


def read_export(path: Path) -> list[ExportRow]:
    """One saved export. Refuses anything that is not the portal's CSV layout."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f, delimiter=";")
        header = next(reader, None)
        if header is None:
            return []  # a page past the end of the month can come back empty
        if header != EXPORT_COLUMNS:
            raise ValueError(
                f"{path.name}: not a transparentni.varazdin.hr export (header {header})"
            )
        rows = []
        for cells in reader:
            if not any(cell.strip() for cell in cells):
                continue
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
                    file=path.name,
                )
            )
    return rows


def _content(row: ExportRow) -> tuple:
    """A row without where it came from: the same page saved twice gives equal content."""
    return (row.number, row.paid_on, row.payer, row.recipient, row.oib, row.amount_eur, row.expense)


def month_report(month: str, rows: list[ExportRow]) -> list[str]:
    """Warnings about pages that may be missing from a month."""
    warnings = []
    numbers = sorted({row.number for row in rows})
    per_number = {}
    for row in rows:
        per_number.setdefault(row.number, set()).add(_content(row))
    if any(len(contents) > 1 for contents in per_number.values()):
        # Different rows share a number: the files count from 1 each, so gaps cannot be seen.
        warnings.append(f"{month}: row numbers restart in each file; gaps cannot be checked")
    else:
        missing = sorted(set(range(1, numbers[-1] + 1)) - set(numbers))
        if missing:
            warnings.append(f"{month}: rows {_ranges(missing)} are missing (pages not saved?)")
    first = min(row.paid_on for row in rows)
    if first.day > 5:
        warnings.append(
            f"{month}: the earliest payment is on {first:%d.%m.}; the first days of the month "
            "may be on pages not saved yet"
        )
    return warnings


def _ranges(numbers: list[int]) -> str:
    spans, start, prev = [], numbers[0], numbers[0]
    for n in numbers[1:] + [None]:
        if n is not None and n == prev + 1:
            prev = n
            continue
        spans.append(f"{start}" if start == prev else f"{start}–{prev}")
        if n is not None:
            start = prev = n
    return ", ".join(spans)


# --- Import -----------------------------------------------------------------------------


def raw_frame(rows: list[ExportRow]) -> pl.DataFrame:
    """Export rows in the columns every payment parser returns (``parse.payments.RAW_COLUMNS``)."""
    from opcina_pipeline.parse.payments import RAW_COLUMNS, split_code

    records = []
    for row in rows:
        code, label = split_code(row.expense)
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


@dataclass
class ImportResult:
    months: dict[str, int]  # month -> cleaned rows written
    warnings: list[str]
    moved: list[str]  # inbox files moved to done/


def import_inbox(
    inbox: Path | None = None,
    out_dir: Path | None = None,
    known_oibs: frozenset[str] | None = None,
) -> ImportResult:
    """Clean every month found in the inbox (and in ``done/``) into ``out_dir``."""
    from opcina_pipeline.parse.payments import known_business_oibs

    inbox = inbox or repo_root() / INBOX
    out_dir = out_dir or repo_root() / CLEANED
    done = inbox / "done"
    # Any file name: browsers save the export as "GetExport", "*.tmp" or "*.csv". The
    # header check in read_export decides what is an export.
    new_files = sorted(p for p in inbox.glob("*") if p.is_file() and not p.name.startswith("."))
    if not new_files:
        return ImportResult({}, [], [])
    known = known_oibs if known_oibs is not None else known_business_oibs()

    rows: dict[str, dict[tuple, ExportRow]] = {}
    touched: set[str] = set()  # only these months are rewritten; others stay as committed
    old_files = sorted(p for p in done.glob("*") if p.is_file())
    for path in old_files + new_files:
        for row in read_export(path):
            month = f"{row.paid_on:%Y-%m}"
            rows.setdefault(month, {}).setdefault(_content(row), row)
            if path in new_files:
                touched.add(month)
    months, warnings = write_cleaned({m: list(rows[m].values()) for m in touched}, out_dir, known)

    done.mkdir(exist_ok=True)
    for path in new_files:
        shutil.move(path, done / path.name)
    return ImportResult(months, warnings, [path.name for path in new_files])


def write_cleaned(
    rows_by_month: dict[str, list[ExportRow]], out_dir: Path, known: frozenset[str]
) -> tuple[dict[str, int], list[str]]:
    """Check each month and write what the site may publish to ``out_dir/<YYYY-MM>.csv``."""
    from opcina_pipeline.parse.payments import finish

    out_dir.mkdir(parents=True, exist_ok=True)
    months, warnings = {}, []
    for month in sorted(rows_by_month):
        month_rows = rows_by_month[month]
        warnings += month_report(month, month_rows)
        cleaned = finish(raw_frame(month_rows), DZS_CODE, "manual", known)
        cleaned.select(CLEANED_COLUMNS).sort("paid_on", "payer_name", "recipient_name").write_csv(
            out_dir / f"{month}.csv"
        )
        months[month] = cleaned.height
    return months, warnings


# --- Official export endpoint -----------------------------------------------------------
#
# Varaždin was asked (Nov 2026) for an official, automatable export. Until it exists,
# `official_url` in payments.toml points at a placeholder; a response that is not a
# payments export is reported and skipped, so the nightly run does not fail over it.


def official_urls(template: str, months: list[str]) -> dict[str, str]:
    """One URL per month when ``template`` has ``{year}``/``{month}``, else one URL."""
    if "{year}" in template or "{month}" in template:
        return {m: template.format(year=m[:4], month=m[5:7], month_int=int(m[5:7])) for m in months}
    return {"all": template}


@dataclass
class OfficialResult:
    months: dict[str, int]  # month -> cleaned rows written
    notes: list[str]
    files: list  # raw downloads (fetch.http.Download), kept outside git


def fetch_official(
    client, template: str, months: list[str], raw_dir: Path, out_dir: Path, known: frozenset[str]
) -> OfficialResult:
    """Download the official export(s) into ``raw_dir`` and clean them into ``out_dir``.

    The response must be the portal's CSV layout (``EXPORT_COLUMNS``); if the city's
    official export turns out different, ``read_export`` is the place to adapt.
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    rows: dict[str, dict[tuple, ExportRow]] = {}
    notes, files = [], []
    for key, url in official_urls(template, months).items():
        download = client.download(url, raw_dir / f"{key}.csv")
        files.append(download)
        try:
            found = read_export(download.path)
        except (ValueError, UnicodeDecodeError) as error:
            notes.append(f"official endpoint {url} is not a payments export yet ({error})"[:300])
            continue
        for row in found:
            rows.setdefault(f"{row.paid_on:%Y-%m}", {}).setdefault(_content(row), row)
    written, warnings = write_cleaned(
        {m: list(r.values()) for m, r in rows.items()}, out_dir, known
    )
    return OfficialResult(written, notes + warnings, files)
