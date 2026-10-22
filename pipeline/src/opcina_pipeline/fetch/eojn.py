"""Public procurement contracts from EOJN RH (task C1).

Two systems, two fetchers; both keep only buyers in scope (``buyers.read_scope_buyers``:
the municipalities and their budget users, SPEC matching rule 1).

``contracts_eojn_legacy``: the old EOJN (eojn.nn.hr), contract register 2018-2023.
The public report ``RptRegistarUgovora.aspx`` is an ASP.NET WebForms page with a
Microsoft ReportViewer 11. It only reports one buyer at a time (generating without a
buyer answers "Morate odabrati naručitelja"; the header's ``linkViewReportAllData``
postback only yields a ReportViewer error), so there is no national export. Per buyer:

1. ``GET RptRegistarUgovora.aspx``: session cookie, ``__VIEWSTATE`` and the buyer
   lookup URL ``uiPartner__Url`` (``Common/SearchFrm.aspx?providerKey=...&guid=...``).
2. ``GET`` that lookup URL, then post it back with ``__EVENTTARGET=uiFilterSearch`` and
   ``uiFilter$Txt_OIB=<oib>``: grid rows ``uiView_gridResults_Row_<partner id>`` with
   name, person type, registration number and OIB. Partner ids are stable, so they
   are cached in ``partners.json`` and the lookup runs once per OIB.
3. ``POST RptRegistarUgovora.aspx`` with the page's form, every date filter blank
   (the page defaults to "updated in the last three months"), ``ctl04=<partner id>``
   and the submit button ``uiGenerateReport$ctl00``. The answer renders the
   ReportViewer, whose init script carries ``ExportUrlBase`` (bound to the session).
4. ``GET <ExportUrlBase>EXCELOPENXML``: the whole register as XLSX, sheet ``RPT_Ugovor``
   (the format of the Ivanec file on data.gov.hr). CSV export answers HTTP 500.

Step 3 for the next buyer reuses the page returned by the previous step 3, so a run
costs two requests per buyer once the partner ids are cached. A file whose cell
values did not change is left untouched.

``contracts_eojn``: the new EOJN (eojn.hr, 2024 onwards) through its official API
(``X-API-Key``; eojn.hr's robots.txt disallows everything else, so the public grid is
never used). Each run walks time windows from the last processed ``to`` (state file,
minus one day of overlap) to now:

- ``eContractRegister/contractsSearch?publishedDateFrom&publisheDateTo`` returns full
  contract records (``ContractRegisterViewModel``) published in the window; records
  whose ``contractingAuthority.identificationNumber`` is in scope are kept.
- ``eProcurementData/eventsForContractsByTime?from&to`` lists contracts with events
  (changes) in the window; those already kept are refreshed with
  ``eProcurementData/getContractData?contractId=``. Contracts never seen are out of
  scope (every contract in the new system was published after the backfill start).

Records are merged by ``contractId`` into ``contracts.jsonl``, one raw API object per
line, sorted by id.
"""

import html
import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import polars as pl
from openpyxl import load_workbook

from opcina_pipeline.buyers import read_scope_buyers
from opcina_pipeline.config import load_sources
from opcina_pipeline.fetch.base import FetchContext, Outcome, fetcher
from opcina_pipeline.fetch.http import Download, PoliteClient, file_sha256

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

BLOCKED_STATUSES = {403, 429}


def scope_buyers(ctx: FetchContext) -> pl.DataFrame:
    register = load_sources()["minfin_budget_users"].path
    if not register.exists():
        raise FileNotFoundError(f"{register} missing; fetch minfin_budget_users first")
    return read_scope_buyers(ctx.master(), register)


def _write_if_changed(path: Path, text: str) -> Download:
    """Write ``text`` atomically unless the file already holds exactly that."""
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return Download(path, False, file_sha256(path), path.stat().st_size)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)
    return Download(path, True, file_sha256(path), path.stat().st_size)


# ---------------------------------------------------------------------------
# Old EOJN (eojn.nn.hr): contract register report, 2018-2023
# ---------------------------------------------------------------------------

LEGACY_HOST = "https://eojn.nn.hr"
LEGACY_REPORT_URL = f"{LEGACY_HOST}/Spin/application/ipn/JavniReporti/RptRegistarUgovora.aspx"
LEGACY_SHEET = "RPT_Ugovor"
EXPORT_FORMAT = "EXCELOPENXML"
PARTNER_FIELD = "ctl04"  # hidden key field the lookup popup fills (uiPartner__SetVals)
GENERATE_BUTTON = "uiGenerateReport$ctl00"
DATE_FILTERS = ("uiDatumObjave", "uiDatumAzuriranja", "uiDatumSklapanja")


class LegacyReportError(RuntimeError):
    """The report page answered with a message instead of a report."""


class _FormParser(HTMLParser):
    """Collects what a browser would post: named inputs, selects and textareas."""

    SKIPPED_TYPES = {"submit", "button", "image", "reset", "file"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fields: dict[str, str] = {}
        self._select: str | None = None
        self._select_first: str | None = None
        self._textarea: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k: v or "" for k, v in attrs}
        name = a.get("name")
        if tag == "input" and name:
            kind = a.get("type", "text").lower()
            if kind in self.SKIPPED_TYPES:
                return
            if kind in {"checkbox", "radio"} and "checked" not in a:
                return
            self.fields[name] = a.get("value", "")
        elif tag == "select" and name:
            self._select, self._select_first = name, None
            self.fields[name] = ""
        elif tag == "option" and self._select:
            value = a.get("value", "")
            if self._select_first is None:
                self._select_first = value
                self.fields[self._select] = value
            if "selected" in a:
                self.fields[self._select] = value
        elif tag == "textarea" and name:
            self._textarea = name
            self.fields[name] = ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self._select = None
        elif tag == "textarea":
            self._textarea = None

    def handle_data(self, data: str) -> None:
        if self._textarea:
            self.fields[self._textarea] += data


def form_fields(page: str) -> dict[str, str]:
    """The values a browser would post back for ``page`` (buttons excluded)."""
    parser = _FormParser()
    parser.feed(page)
    return parser.fields


def _input_value(page: str, element_id: str) -> str:
    match = re.search(rf'<input\b[^>]*\bid="{re.escape(element_id)}"[^>]*>', page)
    value = re.search(r'\bvalue="([^"]*)"', match.group(0)) if match else None
    if not value:
        raise LegacyReportError(f"{element_id} not found on the report page")
    return html.unescape(value.group(1))


def partner_lookup_url(page: str) -> str:
    """Absolute URL of the buyer lookup popup (SearchFrm.aspx) for this page's session."""
    return LEGACY_HOST + _input_value(page, "uiPartner__Url")


@dataclass(frozen=True)
class Partner:
    id: str
    name: str
    oib: str


def _cell_text(cell: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", cell)).strip()


def parse_partners(page: str) -> list[Partner]:
    """Rows of the lookup grid: Tvrtka/Naziv, Vrsta osobe, Matični broj, OIB."""
    partners = []
    rows = re.finditer(r'<tr\b[^>]*\bid="uiView_gridResults_Row_(\d+)"[^>]*>(.*?)</tr>', page, re.S)
    for row in rows:
        cells = [_cell_text(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", row.group(2), re.S)]
        partners.append(
            Partner(row.group(1), cells[0] if cells else "", cells[-1] if cells else "")
        )
    return partners


def report_error(page: str) -> str | None:
    """The page's alert or ReportViewer error message, if it shows one instead of a report."""
    alert = re.search(r'alert\(unescape\("([^"]*)"\)\)', page)
    if alert:
        return html.unescape(alert.group(1))
    if re.search(r'name="uiReports\$ctl09\$VisibilityState\$ctl00" value="Error"', page):
        items = re.findall(r"<li[^>]*>(.*?)</li>", page, re.S)
        return "ReportViewer error: " + ("; ".join(_cell_text(i) for i in items) or "unknown")
    return None


def export_url(page: str, export_format: str = EXPORT_FORMAT) -> str:
    """The ReportViewer's export URL for the report just generated on ``page``."""
    match = re.search(r'"ExportUrlBase":"((?:[^"\\]|\\.)*)"', page)
    if not match:
        raise LegacyReportError(report_error(page) or "no ExportUrlBase in the report page")
    return LEGACY_HOST + json.loads(f'"{match.group(1)}"') + export_format


def report_form(page: str, partner_id: str) -> dict[str, str]:
    """Postback that generates the full register of one buyer (all date filters blank)."""
    fields = form_fields(page)
    for name in list(fields):
        if name.startswith(DATE_FILTERS) and not name.endswith("$enableHidden"):
            fields[name] = ""
    fields.update(
        {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            PARTNER_FIELD: partner_id,
            "uiPartner": "",
            GENERATE_BUTTON: "",
        }
    )
    return fields


def sheet_values(source: Path | bytes) -> list[tuple]:
    """All cell values of the register sheet, to tell a real change from a re-export."""
    workbook = load_workbook(
        BytesIO(source) if isinstance(source, bytes) else source, read_only=True
    )
    try:
        return [tuple(row) for row in workbook[LEGACY_SHEET].iter_rows(values_only=True)]
    finally:
        workbook.close()


class LegacyRegister:
    """One browser-like session on the old EOJN contract register report."""

    def __init__(self, client: PoliteClient):
        self.client = client
        self._page: str | None = None

    @property
    def page(self) -> str:
        if self._page is None:
            self._page = self.client.get(LEGACY_REPORT_URL).text
        return self._page

    def reset(self) -> None:
        """Forget the current page (and its view state); the next call starts afresh."""
        self._page = None

    def find_partners(self, oib: str) -> list[Partner]:
        """Partner ids the old EOJN uses for ``oib`` (usually one, sometimes none)."""
        url = partner_lookup_url(self.page)
        search = self.client.get(url).text
        fields = form_fields(search)
        fields.update(
            {"__EVENTTARGET": "uiFilterSearch", "__EVENTARGUMENT": "", "uiFilter$Txt_OIB": oib}
        )
        results = self.client.post(url, data=fields).text
        return [p for p in parse_partners(results) if p.oib == oib]

    def export(self, partner_id: str, dest: Path) -> Download:
        """Generate one buyer's register and save its XLSX export to ``dest``."""
        page = self.client.post(LEGACY_REPORT_URL, data=report_form(self.page, partner_id)).text
        self._page = page
        error = report_error(page)
        if error:
            raise LegacyReportError(error)
        response = self.client.get(export_url(page))
        if not response.content.startswith(b"PK"):
            raise LegacyReportError(f"export is not an XLSX file ({len(response.content)} bytes)")
        return _store_export(response.content, dest)


def _store_export(content: bytes, dest: Path) -> Download:
    try:
        new_values = sheet_values(content)
    except Exception as error:
        raise LegacyReportError(f"export has no {LEGACY_SHEET} sheet: {error}") from error
    if dest.exists() and sheet_values(dest) == new_values:
        return Download(dest, False, file_sha256(dest), dest.stat().st_size)
    tmp = dest.with_name(dest.name + ".part")
    tmp.write_bytes(content)
    tmp.replace(dest)
    return Download(dest, True, file_sha256(dest), dest.stat().st_size)


def _read_partner_cache(path: Path) -> dict[str, list[dict]]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _is_blocked(error: Exception) -> bool:
    return (
        isinstance(error, httpx.HTTPStatusError) and error.response.status_code in BLOCKED_STATUSES
    )


def fetch_legacy_registers(client: PoliteClient, buyers: pl.DataFrame, out_dir: Path) -> Outcome:
    """Export the old-EOJN register of every buyer to ``out_dir/<oib>.xlsx``.

    A buyer with several partner records gets ``<oib>_<partner id>.xlsx`` per record.
    Buyers the old system does not know are listed in the message, not treated as errors.
    """
    cache_path = out_dir / "partners.json"
    partners = _read_partner_cache(cache_path)
    session = LegacyRegister(client)
    files: list[Download] = []
    missing: list[str] = []
    errors: list[str] = []

    for oib, name in buyers.select("oib", "name").iter_rows():
        try:
            # Only found partners are cached: an empty answer is looked up again next
            # run, so a transient page error never hides a buyer for good.
            records = partners.get(oib)
            if not records:
                records = [{"id": p.id, "name": p.name} for p in session.find_partners(oib)]
                if records:
                    partners[oib] = records
                    cache_path.write_text(
                        json.dumps(partners, ensure_ascii=False, indent=2, sort_keys=True),
                        encoding="utf-8",
                    )
            if not records:
                missing.append(oib)
                continue
            for record in records:
                stem = oib if len(records) == 1 else f"{oib}_{record['id']}"
                files.append(_export_with_retry(session, record["id"], out_dir / f"{stem}.xlsx"))
        except Exception as error:  # noqa: BLE001 - one buyer must not stop the others
            if _is_blocked(error):
                status = error.response.status_code
                return Outcome(
                    "failed", files, f"stopped: eojn.nn.hr answered HTTP {status} at {oib}"
                )
            errors.append(f"{oib} {name}: {type(error).__name__}: {error}")
            session.reset()

    message = f"{len(files)} registers for {buyers.height} buyers"
    if missing:
        message += f"; {len(missing)} not in old EOJN: {', '.join(missing)}"
    if errors:
        return Outcome("failed", files, message + "; errors: " + " | ".join(errors))
    return Outcome.from_downloads(files, message)


def _export_with_retry(session: LegacyRegister, partner_id: str, dest: Path) -> Download:
    """Export once; on a report error start a fresh session (expired view state) and retry."""
    try:
        return session.export(partner_id, dest)
    except LegacyReportError:
        session.reset()
        return session.export(partner_id, dest)


@fetcher("contracts_eojn_legacy")
def contracts_eojn_legacy(ctx: FetchContext) -> Outcome:
    return fetch_legacy_registers(ctx.client, scope_buyers(ctx), ctx.out_dir)


# ---------------------------------------------------------------------------
# New EOJN (eojn.hr): official API, 2024 onwards
# ---------------------------------------------------------------------------

API_BASE = "https://eojn.hr/api/public"
SEARCH_URL = f"{API_BASE}/eContractRegister/contractsSearch"
EVENTS_URL = f"{API_BASE}/eProcurementData/eventsForContractsByTime"
CONTRACT_URL = f"{API_BASE}/eProcurementData/getContractData"
API_KEY_NAME = "EOJN_API_KEY"

API_START = datetime(2024, 1, 1)  # the new EOJN register starts in 2024
WINDOW = timedelta(days=7)
# Windows are computed in UTC while the server works in Croatian time; re-reading the
# last day of the previous run covers the offset (records merge by id).
OVERLAP = timedelta(days=1)
# At most this many windows per run (~half a year, ~5 minutes at eojn.hr's pace): the
# first backfill from 2024 then completes over a few nightly runs instead of
# outlasting the job timeout, which would lose its progress.
MAX_WINDOWS_PER_RUN = 26

CONTRACTS_FILE = "contracts.jsonl"
STATE_FILE = "state.json"


class ApiKeyRejected(RuntimeError):
    pass


def api_time(moment: datetime) -> str:
    """The query format the API documents: ``yyyy-MM-dd HH:mm:ss.ffff``."""
    return moment.strftime("%Y-%m-%d %H:%M:%S.") + f"{moment.microsecond // 100:04d}"


def windows(start: datetime, end: datetime, size: timedelta = WINDOW) -> Iterator[tuple]:
    """Consecutive ``(from, to)`` pairs covering ``start``..``end``."""
    while start < end:
        stop = min(start + size, end)
        yield start, stop
        start = stop


def _json(response: httpx.Response) -> Any:
    """Response body as JSON; the spec's examples are JSON strings, so unwrap one level."""
    data = response.json() if response.content else None
    if isinstance(data, str):
        data = json.loads(data) if data.strip() else None
    return data


def buyer_oib(contract: dict) -> str | None:
    authority = contract.get("contractingAuthority") or {}
    oib = authority.get("identificationNumber")
    return str(oib).strip() if oib else None


def contract_id(contract: dict) -> int | None:
    value = contract.get("contractId")
    return int(value) if value is not None else None


class EojnApi:
    """The few read-only calls of the official eojn.hr API the pipeline needs."""

    def __init__(self, client: PoliteClient, api_key: str):
        self.client = client
        self.headers = {"X-API-Key": api_key, "Accept": "application/json"}

    def _get(self, url: str, params: dict) -> Any:
        try:
            return _json(self.client.get(url, params=params, headers=self.headers))
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                raise ApiKeyRejected(
                    f"eojn.hr refused the API key (HTTP {error.response.status_code})"
                ) from error
            raise

    def contracts_published(self, start: datetime, end: datetime) -> list[dict]:
        """``ContractsRegisterSearchResponseModel.contracts`` published in the window."""
        data = self._get(
            SEARCH_URL,
            {"publishedDateFrom": start.isoformat(), "publisheDateTo": end.isoformat()},
        )
        if isinstance(data, dict):
            data = data.get("contracts")
        return [c for c in data or [] if isinstance(c, dict)]

    def changed_contract_ids(self, start: datetime, end: datetime) -> set[int]:
        """``EventsResponse.events[].objectId`` for contract events in the window."""
        data = self._get(EVENTS_URL, {"from": api_time(start), "to": api_time(end)})
        events = data.get("events") if isinstance(data, dict) else None
        return {int(e["objectId"]) for e in events or [] if e.get("objectId") is not None}

    def contract(self, contract_id: int) -> dict | None:
        """``ContractRegisterViewModel`` of one contract."""
        data = self._get(CONTRACT_URL, {"contractId": contract_id})
        return data if isinstance(data, dict) and data else None


def read_contracts(path: Path) -> dict[int, dict]:
    if not path.exists():
        return {}
    contracts = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            contracts[contract_id(record)] = record
    return contracts


def contracts_text(contracts: dict[int, dict]) -> str:
    return "".join(
        json.dumps(contracts[cid], ensure_ascii=False, sort_keys=True) + "\n"
        for cid in sorted(contracts)
    )


def merge_contract(contracts: dict[int, dict], record: dict) -> bool:
    """Keep the newest version of a contract; True if ``contracts`` changed."""
    cid = contract_id(record)
    if cid is None:
        return False
    current = contracts.get(cid)
    if current is not None and (current.get("versionNumber") or 0) > (
        record.get("versionNumber") or 0
    ):
        return False
    if current == record:
        return False
    contracts[cid] = record
    return True


def _read_state(path: Path) -> datetime | None:
    if not path.exists():
        return None
    return datetime.fromisoformat(json.loads(path.read_text(encoding="utf-8"))["last_to"])


def _write_state(path: Path, last_to: datetime) -> None:
    path.write_text(json.dumps({"last_to": last_to.isoformat()}, indent=2), encoding="utf-8")


def sync_contracts(
    api: EojnApi,
    buyer_oibs: Iterable[str],
    out_dir: Path,
    now: datetime | None = None,
) -> Outcome:
    """Bring ``out_dir/contracts.jsonl`` up to date with the windows since the last run."""
    scope = set(buyer_oibs)
    contracts_path = out_dir / CONTRACTS_FILE
    state_path = out_dir / STATE_FILE
    contracts = read_contracts(contracts_path)
    original = contracts_text(contracts)
    before = len(contracts)
    end = (now or datetime.now(UTC)).replace(tzinfo=None)
    last_to = _read_state(state_path)
    start = max(API_START, last_to - OVERLAP) if last_to else API_START

    refreshed = 0
    processed_to = start
    try:
        for index, (window_start, window_end) in enumerate(windows(start, end)):
            if index == MAX_WINDOWS_PER_RUN:
                break
            published = set()
            for record in api.contracts_published(window_start, window_end):
                if buyer_oib(record) in scope:
                    merge_contract(contracts, record)
                    published.add(contract_id(record))
            for cid in sorted(api.changed_contract_ids(window_start, window_end)):
                if cid not in contracts or cid in published:
                    continue
                record = api.contract(cid)
                if record and merge_contract(contracts, record):
                    refreshed += 1
            # Saved per window, so an interrupted backfill resumes where it stopped.
            _write_if_changed(contracts_path, contracts_text(contracts))
            _write_state(state_path, window_end)
            processed_to = window_end
    except ApiKeyRejected as error:
        return Outcome("failed", message=str(error))

    text = contracts_text(contracts)
    download = _write_if_changed(contracts_path, text)
    download = Download(download.path, text != original, download.sha256, download.bytes)
    message = (
        f"{len(contracts)} contracts in scope ({len(contracts) - before} new, "
        f"{refreshed} refreshed from events) up to {processed_to:%Y-%m-%d %H:%M} UTC"
    )
    if processed_to < end:
        message += "; backfill continues next run"
    return Outcome.from_downloads([download], message)


@fetcher("contracts_eojn")
def contracts_eojn(ctx: FetchContext) -> Outcome:
    api_key = ctx.secret(API_KEY_NAME)
    if not api_key:
        return Outcome("skipped", message=f"{API_KEY_NAME} not set: request a key from eojn@nn.hr")
    buyers = scope_buyers(ctx)
    return sync_contracts(EojnApi(ctx.client, api_key), buyers["oib"].to_list(), ctx.out_dir)
