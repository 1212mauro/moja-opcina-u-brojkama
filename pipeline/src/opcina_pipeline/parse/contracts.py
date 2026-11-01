"""Public procurement contracts (tasks C3, C5, C6) -> the ``contract`` table.

Four inputs, one row per contract:

- ``contracts_eojn_legacy``: one old-EOJN register export per buyer,
  ``<oib>.xlsx`` (or ``<oib>_<partner id>.xlsx``), sheet ``RPT_Ugovor``. The buyer is
  the file's OIB. Header on row 14 from column B, merged cells, a footer of notes.
  Supplier name and OIB share one cell; amounts are text such as ``25.000,00 HRK``
  whose currency follows the record's last update, so it is read per cell.
- ``contracts_municipal``: registers that towns and municipalities publish themselves
  on data.gov.hr, in ``<publisher OIB>/`` folders. Old exports use the ``RPT_Ugovor``
  layout, 2024 onwards the new EOJN's ``Analytics`` grid (buyer and supplier OIB in
  their own columns, numeric EUR, contract URL with the EOJN id). Other layouts (the
  2015 "Evidencija ugovora" sheets: every contract the town signed, gross values only,
  formulas as text) are skipped and logged.
- ``contracts_eojn``: ``contracts.jsonl`` from the new EOJN API, one
  ``ContractRegisterViewModel`` per line (only once an API key is set).
- ``contracts_ted``: contract award notices on TED (eForms XML), 2024 onwards, for
  procurement above the EU thresholds. One row per signed contract; its value is the
  winning tender's (without VAT), or a framework agreement's re-estimated value. Joint
  procurement notices are skipped: eForms does not say which buyer signed which contract.

Amounts: ``value_eur`` is the value without VAT (``Iznos bez PDV-a``), so a wrong VAT
figure in a register never changes totals. Kuna amounts are converted once at the
fixed rate (``to_eur``); the published text and its currency are kept.

Deduplication (C6): the same contract can be in several systems. Systems are taken in
priority order eojn > eojn_legacy > municipal > ted; a row is dropped when a
higher-priority system already has a contract with the same EOJN contract id, the same
buyer and normalised contract number, or, for rows without a number, the same buyer,
supplier OIB, signing date and net value. TED numbers contracts its own way, so a TED
row is also dropped when another system has a contract of the same buyer with the same
supplier signed on the same day. Inside one system only exact duplicate rows collapse:
registers reuse a contract number for separate lots or annual orders.
"""

import hashlib
import json
import logging
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any, NamedTuple

import polars as pl
from openpyxl import load_workbook

from opcina_pipeline.buyers import read_scope_buyers
from opcina_pipeline.config import config_path, load_sources
from opcina_pipeline.tables import HRK_PER_EUR, conform, latest_run_id
from opcina_pipeline.text import ascii_fold

log = logging.getLogger(__name__)

# Highest priority first: the new EOJN is the live register, the old one its archive,
# a municipality's own file a cross-check, TED only the contracts above EU thresholds.
SYSTEMS = ("eojn", "eojn_legacy", "municipal", "ted")
SOURCE_OF_SYSTEM = {
    "eojn": "contracts_eojn",
    "eojn_legacy": "contracts_eojn_legacy",
    "municipal": "contracts_municipal",
    "ted": "contracts_ted",
}

# Columns of the parsed rows, before the buyer join; ``vat_eur`` and ``eojn_id`` only
# serve checks and deduplication.
PARSED = {
    "system": pl.Utf8,
    "record_id": pl.Utf8,
    "eojn_id": pl.Utf8,
    "buyer_oib": pl.Utf8,
    "subject": pl.Utf8,
    "cpv": pl.Utf8,
    "procedure": pl.Utf8,
    "contract_number": pl.Utf8,
    "supplier_name": pl.Utf8,
    "supplier_oib": pl.Utf8,
    "signed_on": pl.Date,
    "value_eur": pl.Float64,
    "value_with_vat_eur": pl.Float64,
    "vat_eur": pl.Float64,
    "value_original": pl.Utf8,
    "currency_original": pl.Utf8,
}

# ---------------------------------------------------------------------------
# Values
# ---------------------------------------------------------------------------


class Money(NamedTuple):
    eur: float
    original: str  # as published, e.g. "25.000,00 HRK"
    currency: str  # "EUR" | "HRK"


_AMOUNT = re.compile(
    r"(?P<sign>-)?\s*(?P<number>\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+\.\d{1,2}|\d+(?:,\d+)?)"
    r"\s*(?P<currency>HRK|KN|EUR|€)?\.?",
    re.IGNORECASE,
)


def to_eur(value: Any, currency: str | None = None) -> Money | None:
    """Euro value of a published amount; ``None`` when the cell is empty.

    Text in the Croatian format carries its own currency (``"25.000,00 HRK"``,
    ``"- 87,94 HRK"``, ``"1.200,50 EUR"``); a bare number needs ``currency``. Kuna is
    converted at the fixed changeover rate (C3) and rounded to the cent.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        number, unit = float(value), currency
        original = f"{_hr_number(number)} {(unit or '').upper()}".strip()
    else:
        original = " ".join(str(value).split())
        if not original:
            return None
        match = _AMOUNT.fullmatch(original)
        if not match:
            raise ValueError(f"unrecognised amount {value!r}")
        number = _number(match["number"])
        if match["sign"]:
            number = -number
        unit = match["currency"] or currency
    unit = {"KN": "HRK", "€": "EUR"}.get((unit or "").upper(), (unit or "").upper())
    if unit not in ("EUR", "HRK"):
        raise ValueError(f"amount {value!r} has no known currency")
    eur = number / HRK_PER_EUR if unit == "HRK" else number
    return Money(round(eur, 2), original, unit)


def _number(text: str) -> float:
    """Croatian ("25.000,00", "1.234", "1234,5") or dot-decimal ("1234.56") number."""
    if "," in text:
        return float(text.replace(".", "").replace(",", "."))
    if re.fullmatch(r"\d+\.\d{1,2}", text):
        return float(text)
    return float(text.replace(".", ""))


def _hr_number(number: float) -> str:
    """``1234.5`` -> ``"1.234,50"``."""
    return f"{number:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text or None


def parse_date(value: Any) -> date | None:
    """A cell holding a date: ``datetime``, ``"14.06.2022."``, ``"2024-01-02T00:00:00+01:00"``."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    match = re.fullmatch(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\.?", text)
    if match:
        day, month, year = map(int, match.groups())
        return date(year, month, day)
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", text)
    if match:
        return date(*map(int, match.groups()))
    raise ValueError(f"unrecognised date {value!r}")


def parse_cpv(value: Any) -> str | None:
    """The 8-digit CPV code of ``"39715210-2"`` or ``"42512000 - Klimatizacijski uređaji"``."""
    match = re.match(r"\s*(\d{8})", str(value or ""))
    return match.group(1) if match else None


def find_oib(value: Any) -> str | None:
    """The one 11-digit OIB in a cell (``"KRIVO_SE_REGISTRIRALI_87607151174"`` included)."""
    found = re.findall(r"(?<!\d)\d{11}(?!\d)", str(value or ""))
    return found[0] if len(found) == 1 else None


# A trailing identifier: an OIB, or a foreign tax / registration number (SI23566965).
_TRAILING_ID = re.compile(r"\s+((?:[A-Z]{2})?\d{7,13})$")


def split_supplier(cell: Any) -> tuple[str | None, str | None]:
    """``"SEVOI d.o.o. 86157498303"`` -> ``("SEVOI d.o.o.", "86157498303")``.

    Foreign identifiers are cut from the name but not kept as an OIB.
    """
    text = _text(cell)
    if text is None:
        return None, None
    match = _TRAILING_ID.search(text)
    if not match:
        return text, None
    ident = match.group(1)
    name = text[: match.start()].strip() or text
    return name, ident if re.fullmatch(r"\d{11}", ident) else None


_QUARTERLY = "Tromjesečna evidencija ugovora: "


def clean_subject(value: Any) -> str | None:
    """Drops the old register's ``"Tromjesečna evidencija ugovora: X: X"`` wrapper."""
    text = _text(value)
    if text is None or not text.startswith(_QUARTERLY):
        return text
    rest = text[len(_QUARTERLY) :]
    half = (len(rest) - 2) // 2
    if rest[half : half + 2] == ": " and rest[:half] == rest[half + 2 :]:
        return rest[:half]
    return rest


def normalise_number(value: Any) -> str | None:
    """Contract number as a match key: no case, accents, spaces or "Ugovor br." prefix."""
    text = _text(value)
    if text is None:
        return None
    key = re.sub(r"\s+", "", ascii_fold(text))
    key = re.sub(r"^(?:ugovor|narudzbenica)?(?:broj|br\.)?:?", "", key)
    key = key.strip(".,;:-")
    return key or None


# ---------------------------------------------------------------------------
# Old-EOJN register layout (RPT_Ugovor): legacy exports and Ivanec 2018-2023
# ---------------------------------------------------------------------------

REGISTER_SHEET = "RPT_Ugovor"
REGISTER_FIRST_HEADER = "Evidencijski broj nabave"
REGISTER_COLUMNS = {
    "subject": "Predmet nabave",
    "cpv": "CPV",
    "procedure": "Vrsta postupka",
    "supplier": "Naziv i OIB ugovaratelja",
    "signed_on": "Datum sklapanja",
    "contract_number": "Oznaka/broj ugovora",
    "net": "Iznos bez PDV-a",
    "vat": "Iznos PDV-a",
    "gross": "Ukupni iznos s PDV-om",
    "published": "Datum objave",
}
REGISTER_FOOTER = ("*", "Puno značenje")


def _sheet_rows(path: Path, sheet: str) -> list[tuple]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        rows = [tuple(row) for row in workbook[sheet].iter_rows(values_only=True)]
    finally:
        workbook.close()
    width = max((len(r) for r in rows), default=0)
    return [r + (None,) * (width - len(r)) for r in rows]


def _register_records(rows: list[tuple]) -> Iterable[dict[str, Any]]:
    """Data rows of an RPT_Ugovor sheet as ``{field: cell}`` (``REGISTER_COLUMNS`` keys)."""
    header_at = next(
        (i for i, row in enumerate(rows) if REGISTER_FIRST_HEADER in map(_text, row)), None
    )
    if header_at is None:
        raise ValueError(f"no {REGISTER_FIRST_HEADER!r} header row")
    header = [_text(c) for c in rows[header_at]]
    index = {}
    for field, title in REGISTER_COLUMNS.items():
        if title not in header:
            raise ValueError(f"register has no column {title!r}")
        index[field] = header.index(title)
    first = header.index(REGISTER_FIRST_HEADER)
    for row in rows[header_at + 1 :]:
        lead = _text(row[first]) or ""
        if lead.startswith(REGISTER_FOOTER):
            break
        record = {field: row[i] for field, i in index.items()}
        # Spacer rows carry only "Ne" (EU funds) and timestamps.
        if any(_text(record[f]) for f in ("subject", "supplier", "net", "contract_number")):
            yield record


def _register_id(record: dict[str, Any]) -> str:
    """Stable id of a register row: its publication time plus the fields that identify it.

    ``Datum objave`` alone is not unique (batch imports share one timestamp), and the
    contract number is reused across lots and orders; amounts are left out because
    updates change them.
    """
    published = record["published"]
    parts = [
        published.isoformat() if isinstance(published, datetime) else _text(published),
        _text(record["contract_number"]),
        _text(record["supplier"]),
        str(parse_date(record["signed_on"])),
        _text(record["subject"]),
        parse_cpv(record["cpv"]),
    ]
    text = "|".join(p or "" for p in parts)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def parse_register(
    path: Path, buyer_oib: str, system: str, id_prefix: str | None = None
) -> pl.DataFrame:
    """One old-EOJN register export (sheet ``RPT_Ugovor``) of one buyer.

    ``record_id`` is ``<id_prefix or buyer OIB>:<hash>`` (``_register_id``).
    """
    rows = []
    for record in _register_records(_sheet_rows(path, REGISTER_SHEET)):
        supplier_name, supplier_oib = split_supplier(record["supplier"])
        net = to_eur(record["net"])
        vat = to_eur(record["vat"])
        gross = to_eur(record["gross"])
        rows.append(
            {
                "system": system,
                "record_id": f"{id_prefix or buyer_oib}:{_register_id(record)}",
                "eojn_id": None,
                "buyer_oib": buyer_oib,
                "subject": clean_subject(record["subject"]),
                "cpv": parse_cpv(record["cpv"]),
                "procedure": _text(record["procedure"]),
                "contract_number": _text(record["contract_number"]),
                "supplier_name": supplier_name,
                "supplier_oib": supplier_oib,
                "signed_on": parse_date(record["signed_on"]),
                "value_eur": net.eur if net else None,
                "value_with_vat_eur": gross.eur if gross else None,
                "vat_eur": vat.eur if vat else None,
                "value_original": net.original if net else None,
                "currency_original": net.currency if net else None,
            }
        )
    return _frame(rows)


# ---------------------------------------------------------------------------
# New-EOJN grid export layout (Analytics): Ivanec 2024 onwards
# ---------------------------------------------------------------------------

GRID_SHEET = "Analytics"
GRID_COLUMNS = {
    "url": "Ugovor",
    "buyer_oib": "OIB Naručitelja",
    "subject": "Predmet nabave",
    "lot": "Naziv grupe",
    "cpv": "CPV",
    "procedure": "Vrsta postupka",
    "contract_number": "Broj ugovora",
    "supplier_name": "Naziv ugovaratelja",
    "supplier_oib": "OIB ugovaratelja",
    "signed_on": "Datum sklapanja",
    "net": "Iznos bez PDV-a",
    "gross": "Iznos s PDV-om",
    # Amended totals; the API's ``totalAmount`` is the amended value too.
    "net_total": "Ukupni iznos (sa izmjenama) bez PDV-a",
    "gross_total": "Ukupni iznos (sa izmjenama) s PDV-om",
}
EOJN_CONTRACT_URL = re.compile(r"/contract-eo/(\d+)")


def parse_grid(path: Path, system: str = "municipal") -> pl.DataFrame:
    """A new-EOJN contract grid export (sheet ``Analytics``).

    The header is row 1 as exported; some publishers add a title row above it.
    """
    rows = _sheet_rows(path, GRID_SHEET)
    start = next((i for i, row in enumerate(rows[:5]) if GRID_COLUMNS["url"] in map(_text, row)), 0)
    header = [_text(c) for c in rows[start]]
    index = {}
    for field, title in GRID_COLUMNS.items():
        if title not in header:
            raise ValueError(f"grid has no column {title!r}")
        index[field] = header.index(title)
    out = []
    for row in rows[start + 1 :]:
        record = {field: row[i] for field, i in index.items()}
        url = _text(record["url"])
        if not url:
            continue
        match = EOJN_CONTRACT_URL.search(url)
        if not match:
            raise ValueError(f"unrecognised contract URL {url!r}")
        net = to_eur(_first(record["net_total"], record["net"]), "EUR")
        gross = to_eur(_first(record["gross_total"], record["gross"]), "EUR")
        subject = _text(record["subject"])
        lot = _text(record["lot"])
        out.append(
            {
                "system": system,
                "record_id": f"eojn-{match.group(1)}",
                "eojn_id": match.group(1),
                "buyer_oib": find_oib(record["buyer_oib"]),
                "subject": f"{subject}: {lot}" if subject and lot else subject or lot,
                "cpv": parse_cpv(record["cpv"]),
                "procedure": _text(record["procedure"]),
                "contract_number": _text(record["contract_number"]),
                "supplier_name": _text(record["supplier_name"]),
                "supplier_oib": find_oib(record["supplier_oib"]),
                "signed_on": parse_date(record["signed_on"]),
                "value_eur": net.eur if net else None,
                "value_with_vat_eur": gross.eur if gross else None,
                "vat_eur": round(gross.eur - net.eur, 2) if net and gross else None,
                "value_original": net.original if net else None,
                "currency_original": net.currency if net else None,
            }
        )
    return _frame(out)


def _first(*values: Any) -> Any:
    return next((v for v in values if v is not None and v != ""), None)


# ---------------------------------------------------------------------------
# New EOJN API (contracts.jsonl)
# ---------------------------------------------------------------------------


def _money(amount: dict | None) -> Money | None:
    if not amount or amount.get("value") is None:
        return None
    return to_eur(amount["value"], amount.get("currency") or "EUR")


def _description(item: dict | None, key: str) -> str | None:
    return _text((item or {}).get(key))


def parse_api_records(records: Iterable[dict]) -> pl.DataFrame:
    """``ContractRegisterViewModel`` objects from the new EOJN API; reversed ones dropped."""
    rows = []
    for record in records:
        if record.get("isReversed"):
            continue
        cid = record.get("contractId")
        if cid is None:
            continue
        operators = [o for o in record.get("economicOperators") or [] if isinstance(o, dict)]
        names = [n for n in (_text(o.get("name")) for o in operators) if n]
        oibs = [find_oib(o.get("identificationNumber")) for o in operators]
        net = _money(record.get("totalAmount"))
        gross = _money(record.get("totalAmountVAT"))
        subject = _text(record.get("procedureName"))
        lot = _text(record.get("lotName"))
        rows.append(
            {
                "system": "eojn",
                "record_id": str(cid),
                "eojn_id": str(cid),
                "buyer_oib": find_oib(
                    (record.get("contractingAuthority") or {}).get("identificationNumber")
                ),
                "subject": f"{subject}: {lot}" if subject and lot else subject or lot,
                "cpv": parse_cpv(_description(record.get("cpv"), "number")),
                "procedure": _description(record.get("procedureType"), "description"),
                "contract_number": _text(record.get("referenceNumber")),
                "supplier_name": "; ".join(names) or None,
                "supplier_oib": oibs[0] if oibs else None,
                "signed_on": parse_date(record.get("contractingDate")),
                "value_eur": net.eur if net else None,
                "value_with_vat_eur": gross.eur if gross else None,
                "vat_eur": round(gross.eur - net.eur, 2) if net and gross else None,
                "value_original": net.original if net else None,
                "currency_original": net.currency if net else None,
            }
        )
    return _frame(rows)


def parse_api_file(path: Path) -> pl.DataFrame:
    lines = path.read_text(encoding="utf-8").splitlines()
    return parse_api_records(json.loads(line) for line in lines if line.strip())


# ---------------------------------------------------------------------------
# TED contract award notices (eForms XML)
# ---------------------------------------------------------------------------

EFORMS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "efac": "http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1",
    "efbc": "http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1",
}


def _x(node: ET.Element | None, path: str) -> str | None:
    return _text(node.findtext(path, namespaces=EFORMS)) if node is not None else None


def _amount(node: ET.Element | None) -> Money | None:
    if node is None or not _text(node.text):
        return None
    return to_eur(float(node.text), node.get("currencyID") or "EUR")


def parse_ted_notice(path: Path) -> list[dict]:
    """Signed contracts of one award notice; ``[]`` for a joint procurement."""
    root = ET.parse(path).getroot()
    result = root.find(".//efac:NoticeResult", EFORMS)
    buyers = root.findall("cac:ContractingParty", EFORMS)
    if result is None or len(buyers) != 1:
        return []

    # ORG-xxxx -> (name, OIB); a company can list several ids (e.g. "TED94" and its OIB).
    orgs: dict[str | None, tuple[str | None, str | None]] = {}
    for company in root.iterfind(".//efac:Organizations/efac:Organization/efac:Company", EFORMS):
        ids = [e.text for e in company.iterfind("cac:PartyLegalEntity/cbc:CompanyID", EFORMS)]
        orgs[_x(company, "cac:PartyIdentification/cbc:ID")] = (
            _x(company, "cac:PartyName/cbc:Name"),
            next((oib for oib in map(find_oib, ids) if oib), None),
        )
    buyer = _x(buyers[0], "cac:Party/cac:PartyIdentification/cbc:ID")

    project = root.find("cac:ProcurementProject", EFORMS)
    title = _x(project, "cbc:Name")
    lots = {
        _x(lot, "cbc:ID"): _x(lot, "cac:ProcurementProject/cbc:Name")
        for lot in root.iterfind("cac:ProcurementProjectLot", EFORMS)
    }
    procedure = _x(root, "cac:TenderingProcess/cbc:Description") or _x(
        root, "cac:TenderingProcess/cbc:ProcedureCode"
    )
    cpv = parse_cpv(_x(project, "cac:MainCommodityClassification/cbc:ItemClassificationCode"))

    # TPA-xxxx -> its tenderers (ORG-xxxx); TEN-xxxx -> the tender.
    parties = {
        _x(tp, "cbc:ID"): [_x(t, "cbc:ID") for t in tp.iterfind("efac:Tenderer", EFORMS)]
        for tp in result.iterfind("efac:TenderingParty", EFORMS)
    }
    tenders = {_x(t, "cbc:ID"): t for t in result.iterfind("efac:LotTender", EFORMS)}
    # Framework agreements carry their value on the lot result, not on the tender.
    framework: dict[str | None, ET.Element | None] = {}
    for lot_result in result.iterfind("efac:LotResult", EFORMS):
        value = lot_result.find("efac:FrameworkAgreementValues/efbc:ReestimatedValueAmount", EFORMS)
        for tender in lot_result.iterfind("efac:LotTender", EFORMS):
            framework[_x(tender, "cbc:ID")] = value

    rows = []
    for contract in result.iterfind("efac:SettledContract", EFORMS):
        chosen = [
            tenders[t]
            for t in (_x(ref, "cbc:ID") for ref in contract.iterfind("efac:LotTender", EFORMS))
            if t in tenders
        ]
        if not chosen:
            continue
        values = [
            _amount(t.find("cac:LegalMonetaryTotal/cbc:PayableAmount", EFORMS))
            or _amount(framework.get(_x(t, "cbc:ID")))
            for t in chosen
        ]
        net = round(sum(v.eur for v in values if v), 2) if all(values) else None
        suppliers = [
            orgs.get(org, (None, None))
            for org in parties.get(_x(chosen[0], "efac:TenderingParty/cbc:ID"), [])
        ]
        lot = None
        if len(lots) > 1:
            names = [lots.get(_x(t, "efac:TenderLot/cbc:ID")) for t in chosen]
            lot = "; ".join(n for n in names if n and n != title) or None
        rows.append(
            {
                "system": "ted",
                "record_id": f"{path.stem}:{_x(contract, 'cbc:ID')}",
                "eojn_id": None,
                "buyer_oib": orgs.get(buyer, (None, None))[1],
                "subject": f"{title}: {lot}" if title and lot else title or lot,
                "cpv": cpv,
                "procedure": procedure,
                "contract_number": _x(contract, "efac:ContractReference/cbc:ID"),
                "supplier_name": "; ".join(n for n, _ in suppliers if n) or None,
                "supplier_oib": suppliers[0][1] if suppliers else None,
                "signed_on": parse_date(_x(contract, "cbc:IssueDate")),
                "value_eur": net,
                "value_with_vat_eur": None,
                "vat_eur": None,
                "value_original": f"{_hr_number(net)} EUR" if net is not None else None,
                "currency_original": "EUR" if net is not None else None,
            }
        )
    return rows


def parse_ted_dir(folder: Path) -> pl.DataFrame:
    """Every notice in ``notices/`` (``<publication number>.xml``)."""
    rows = []
    for path in sorted((folder / "notices").glob("*.xml")):
        parsed = parse_ted_notice(path)
        if not parsed:
            log.info("contracts_ted: %s has no single-buyer contract", path.name)
        rows.extend(parsed)
    return _frame(rows)


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


def _frame(rows: list[dict]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=PARSED, orient="row") if rows else pl.DataFrame(schema=PARSED)


def parse_legacy_dir(folder: Path) -> pl.DataFrame:
    """Every ``<oib>[_<partner id>].xlsx`` export of the old EOJN register."""
    frames = [
        parse_register(path, path.stem.split("_")[0], "eojn_legacy", id_prefix=path.stem)
        for path in sorted(folder.glob("*.xlsx"))
    ]
    return pl.concat(frames) if frames else _frame([])


def parse_municipal_file(path: Path, buyer_oib: str) -> pl.DataFrame | None:
    """A municipality's own register in either EOJN layout; ``None`` for anything else."""
    workbook = load_workbook(path, read_only=True)
    sheets = workbook.sheetnames
    workbook.close()
    if REGISTER_SHEET in sheets:
        return parse_register(path, buyer_oib, "municipal")
    if GRID_SHEET in sheets:
        return parse_grid(path, "municipal")
    return None


def parse_municipal_dir(folder: Path) -> tuple[pl.DataFrame, list[str]]:
    """Every publisher's own registers (``<oib>/*.xlsx``); also the files skipped."""
    frames, skipped = [], []
    for path in sorted(folder.glob("*/*.xlsx")):
        name = f"{path.parent.name}/{path.name}"
        try:
            df = parse_municipal_file(path, path.parent.name)
        except ValueError as error:
            log.warning("contracts_municipal: skipped %s: %s", name, error)
            df = None
        if df is None:
            log.warning("contracts_municipal: skipped %s: not an EOJN register layout", name)
            skipped.append(name)
        else:
            frames.append(df)
    return (pl.concat(frames) if frames else _frame([])), skipped


# ---------------------------------------------------------------------------
# Deduplication and the contract table
# ---------------------------------------------------------------------------


def _match_keys(row: dict) -> list[tuple]:
    """Keys under which two systems' rows are the same contract.

    Registers reuse a number for many orders (one procurement reference, a generic
    "Ugovor o radovima"), so the number is qualified by the supplier OIB, or by the
    signing date when there is no OIB.
    """
    keys = []
    if row["eojn_id"]:
        keys.append(("eojn", row["eojn_id"]))
    number = normalise_number(row["contract_number"])
    if number:
        keys.append(("number", row["buyer_oib"], number, row["supplier_oib"] or row["signed_on"]))
    elif row["supplier_oib"] and row["signed_on"] and row["value_eur"] is not None:
        keys.append(
            ("parties", row["buyer_oib"], row["supplier_oib"], row["signed_on"], row["value_eur"])
        )
    return keys


def _day_key(row: dict) -> tuple | None:
    """Same buyer, supplier and signing day: how a TED row finds its register row."""
    if row["supplier_oib"] and row["signed_on"]:
        return ("day", row["buyer_oib"], row["supplier_oib"], row["signed_on"])
    return None


CONTENT = [c for c in PARSED if c != "record_id"]


def deduplicate(parsed: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Kept rows, and dropped rows with a ``reason`` (``exact`` or ``dup_of:<system>``)."""
    # Exact duplicates inside one system: identical in every parsed field.
    exact = parsed.with_columns(_dup=pl.int_range(pl.len()).over(CONTENT, order_by="record_id"))
    dropped = [exact.filter(pl.col("_dup") > 0).drop("_dup").with_columns(reason=pl.lit("exact"))]
    rows = exact.filter(pl.col("_dup") == 0).drop("_dup")

    seen: dict[tuple, str] = {}
    keep: list[bool] = []
    reasons: list[str | None] = []
    for system in SYSTEMS:
        part = rows.filter(pl.col("system") == system)
        new: dict[tuple, str] = {}
        for row in part.iter_rows(named=True):
            keys = _match_keys(row)
            day = _day_key(row)
            # Every row registers its day key, but only TED rows are matched by it.
            lookup = keys + [day] if system == "ted" and day else keys
            hit = next((seen[k] for k in lookup if k in seen), None)
            keep.append(hit is None)
            reasons.append(f"dup_of:{hit}" if hit else None)
            if hit is None:
                new.update({k: system for k in keys + ([day] if day else [])})
        seen.update({k: v for k, v in new.items() if k not in seen})
    ordered = pl.concat([rows.filter(pl.col("system") == s) for s in SYSTEMS])
    ordered = ordered.with_columns(
        _keep=pl.Series(keep, dtype=pl.Boolean), reason=pl.Series(reasons, dtype=pl.Utf8)
    )
    dropped.append(ordered.filter(~pl.col("_keep")).drop("_keep"))
    kept = ordered.filter(pl.col("_keep")).drop("_keep", "reason")
    return kept, pl.concat(dropped)


def _with_keys(df: pl.DataFrame) -> pl.DataFrame:
    """``contract_key = "<system>:<record id>"``, unique.

    The few register rows that share every identifying field but differ in amount
    (split orders) get ``#2``, ``#3``... in a deterministic order.
    """
    df = df.with_columns(
        contract_key=pl.concat_str([pl.col("system"), pl.col("record_id")], separator=":")
    )
    n = pl.int_range(pl.len()).over("contract_key", order_by=CONTENT)
    return df.with_columns(
        contract_key=pl.when(n > 0)
        .then(pl.concat_str([pl.col("contract_key"), (n + 1).cast(pl.Utf8)], separator="#"))
        .otherwise(pl.col("contract_key"))
    )


def combine_contracts(
    parsed: pl.DataFrame, buyers: pl.DataFrame, run_ids: dict[str, str]
) -> pl.DataFrame:
    """Deduplicated contracts of buyers in scope, as the ``contract`` table."""
    kept, _ = deduplicate(parsed)
    df = _with_keys(kept).join(
        buyers.select(
            pl.col("oib").alias("buyer_oib"),
            pl.col("name").alias("buyer_name"),
            "dzs_code",
            pl.col("kind").alias("buyer_kind"),
        ),
        on="buyer_oib",
        how="inner",
    )
    df = df.with_columns(
        source_run_id=pl.col("system").replace_strict(
            {s: run_ids.get(SOURCE_OF_SYSTEM[s]) for s in SYSTEMS}, return_dtype=pl.Utf8
        )
    )
    return conform(df, "contract").sort("dzs_code", "buyer_oib", "signed_on", "contract_key")


def parse_all(
    raw_dir: Path | None = None, runs_log: Path | None = None
) -> tuple[pl.DataFrame, dict[str, str], list[str]]:
    """Parsed rows of every input present, run ids of the sources read, skipped files.

    ``raw_dir`` and ``runs_log`` default to ``data/raw`` and its ``source_runs.jsonl``.
    """
    sources = load_sources()
    frames, run_ids, skipped = [], {}, []
    for system in SYSTEMS:
        key = SOURCE_OF_SYSTEM[system]
        path = raw_dir / sources[key].file if raw_dir else sources[key].path
        if not path.exists():
            continue  # contracts_eojn until an API key is set
        if system == "eojn":
            frames.append(parse_api_file(path))
        elif system == "eojn_legacy":
            frames.append(parse_legacy_dir(path))
        elif system == "ted":
            frames.append(parse_ted_dir(path))
        else:
            municipal, skipped = parse_municipal_dir(path)
            frames.append(municipal)
        run_ids[key] = latest_run_id(key, runs_log)
    return (pl.concat(frames) if frames else _frame([])), run_ids, skipped


def build_contracts() -> pl.DataFrame:
    master = pl.read_csv(config_path("municipalities.csv"), infer_schema_length=0)
    buyers = read_scope_buyers(master, load_sources()["minfin_budget_users"].path)
    parsed, run_ids, _ = parse_all()
    return combine_contracts(parsed, buyers, run_ids)
