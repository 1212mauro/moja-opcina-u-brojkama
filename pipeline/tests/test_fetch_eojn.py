import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs

import httpx
import polars as pl
import pytest
from openpyxl import Workbook

from opcina_pipeline.config import Source
from opcina_pipeline.fetch import eojn
from opcina_pipeline.fetch.base import FetchContext
from opcina_pipeline.fetch.http import PoliteClient

FIXTURES = Path(__file__).parent / "fixtures" / "eojn"
BREZNICKI_HUM = "35774913576"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def mock_client(handler) -> PoliteClient:
    """A PoliteClient without throttling whose requests go to ``handler``."""
    client = PoliteClient(min_interval=0, retries=0)
    client._http.close()
    client._http = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    return client


def register_xlsx(*contracts: tuple) -> bytes:
    """A miniature ReportViewer export: title rows, header on row 14, then contracts."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = eojn.LEGACY_SHEET
    sheet["B3"] = "REGISTAR UGOVORA"
    sheet["B7"] = "Naručitelj: Općina Breznički Hum"
    sheet["B14"] = "Evidencijski broj nabave"
    sheet["C14"] = "Predmet nabave"
    for offset, (number, subject) in enumerate(contracts):
        sheet.cell(15 + offset, 2, number)
        sheet.cell(15 + offset, 3, subject)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Old EOJN report: page parsing
# ---------------------------------------------------------------------------


def test_form_fields_skip_buttons_and_keep_hidden_values():
    fields = eojn.form_fields(fixture("legacy_report_page.html"))
    assert fields["__VIEWSTATE"] == "VIEWSTATE-1"
    assert fields["uiDatumAzuriranjaOd$validateHidden"] == "07/22/2026"
    assert fields["ctl04"] == ""
    assert "uiGenerateReport$ctl00" not in fields  # submit buttons are posted only when clicked
    assert "uiReports$ToggleParam$img" not in fields


def test_form_fields_take_first_option_of_select():
    fields = eojn.form_fields(fixture("legacy_search_page.html"))
    assert fields["uiFilter$Ddl_VrstaOsobeID"] == ""
    assert "uiFilterSearch" not in fields


def test_partner_lookup_url_is_absolute_and_unescaped():
    url = eojn.partner_lookup_url(fixture("legacy_report_page.html"))
    assert url.startswith("https://eojn.nn.hr/SPIN/APPLICATION/IPN/Common/SearchFrm.aspx?")
    assert "&guid=00000000-0000-0000-0000-000000000001" in url


def test_parse_partners_reads_id_name_and_oib():
    partners = eojn.parse_partners(fixture("legacy_search_results.html"))
    assert partners[0] == eojn.Partner("107710", "Općina Breznički Hum", BREZNICKI_HUM)
    assert [p.id for p in partners] == ["107710", "999999"]
    assert eojn.parse_partners(fixture("legacy_search_empty.html")) == []


def test_export_url_decodes_json_escapes():
    url = eojn.export_url(fixture("legacy_report_generated.html"))
    assert url.startswith("https://eojn.nn.hr/SPIN/APPLICATION/IPN/Reserved.ReportViewerWebControl")
    assert "&OpType=Export&" in url
    assert "ControlID=0123456789abcdef0123456789abcdef" in url
    assert url.endswith("&Format=EXCELOPENXML")


def test_report_errors_are_recognised():
    assert eojn.report_error(fixture("legacy_report_generated.html")) is None
    assert "Morate odabrati naručitelja" in eojn.report_error(
        fixture("legacy_report_no_buyer.html")
    )
    viewer = eojn.report_error(fixture("legacy_report_viewer_error.html"))
    assert viewer == "ReportViewer error: Object reference not set to an instance of an object."
    with pytest.raises(eojn.LegacyReportError, match="Morate odabrati"):
        eojn.export_url(fixture("legacy_report_no_buyer.html"))


def test_report_form_blanks_date_filters_and_selects_buyer():
    form = eojn.report_form(fixture("legacy_report_page.html"), "107710")
    assert form["ctl04"] == "107710"
    assert form["uiGenerateReport$ctl00"] == ""
    assert form["__VIEWSTATE"] == "VIEWSTATE-1"
    for name in ("textBox", "hidden", "validateHidden"):
        assert form[f"uiDatumAzuriranjaOd${name}"] == ""
        assert form[f"uiDatumAzuriranjaDo${name}"] == ""
    assert form["uiDatumAzuriranjaOd$enableHidden"] == "true"


# ---------------------------------------------------------------------------
# Old EOJN report: the whole fetch against a fake server
# ---------------------------------------------------------------------------


class FakeLegacyServer:
    def __init__(self, export: bytes, generate_status: int = 200):
        self.export = export
        self.generate_status = generate_status
        self.requests: list[tuple[str, str, dict]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        form = {
            k: v[0] for k, v in parse_qs(request.content.decode(), keep_blank_values=True).items()
        }
        path = request.url.path
        self.requests.append((request.method, path.rsplit("/", 1)[-1], form))
        if path.endswith("RptRegistarUgovora.aspx"):
            if request.method == "GET":
                return httpx.Response(200, text=fixture("legacy_report_page.html"))
            if self.generate_status != 200:
                return httpx.Response(self.generate_status)
            assert form["ctl04"] == "107710"
            return httpx.Response(200, text=fixture("legacy_report_generated.html"))
        if path.endswith("SearchFrm.aspx"):
            if request.method == "GET":
                return httpx.Response(200, text=fixture("legacy_search_page.html"))
            assert form["__EVENTTARGET"] == "uiFilterSearch"
            assert form["__VIEWSTATE"] == "SEARCH-VIEWSTATE"
            known = form["uiFilter$Txt_OIB"] == BREZNICKI_HUM
            page = "legacy_search_results.html" if known else "legacy_search_empty.html"
            return httpx.Response(200, text=fixture(page))
        if path.endswith("Reserved.ReportViewerWebControl.axd"):
            assert request.url.params["Format"] == "EXCELOPENXML"
            return httpx.Response(200, content=self.export)
        return httpx.Response(404)

    def count(self, method: str, page: str) -> int:
        return sum(1 for m, p, _ in self.requests if (m, p) == (method, page))


BUYERS = pl.DataFrame(
    {
        "oib": [BREZNICKI_HUM, "00000000005"],
        "name": ["OPĆINA BREZNIČKI HUM", "DJEČJI VRTIĆ BEZ ZAPISA"],
        "dzs_code": ["01511", "01511"],
        "kind": ["unit", "budget_user"],
    }
)


def test_fetch_legacy_registers_exports_each_known_buyer(tmp_path):
    server = FakeLegacyServer(register_xlsx(("1/2018", "Ceste"), ("2/2018", "Rasvjeta")))
    outcome = eojn.fetch_legacy_registers(mock_client(server), BUYERS, tmp_path)

    assert outcome.status == "ok"
    assert [f.path.name for f in outcome.files] == [f"{BREZNICKI_HUM}.xlsx"]
    assert "1 not in old EOJN: 00000000005" in outcome.message
    rows = eojn.sheet_values(tmp_path / f"{BREZNICKI_HUM}.xlsx")
    assert ("1/2018", "Ceste") in [tuple(v for v in r if v) for r in rows]
    partners = json.loads((tmp_path / "partners.json").read_text(encoding="utf-8"))
    assert partners == {
        BREZNICKI_HUM: [{"id": "107710", "name": "Općina Breznički Hum"}],
        "00000000005": [],
    }
    generate = [
        form for m, p, form in server.requests if (m, p) == ("POST", "RptRegistarUgovora.aspx")
    ]
    assert generate[0]["uiDatumAzuriranjaOd$textBox"] == ""
    assert generate[0]["__EVENTVALIDATION"] == "EVENTVALIDATION-1"


def test_fetch_legacy_registers_reuses_partner_ids_and_keeps_unchanged_files(tmp_path):
    export = register_xlsx(("1/2018", "Ceste"))
    eojn.fetch_legacy_registers(mock_client(FakeLegacyServer(export)), BUYERS, tmp_path)

    server = FakeLegacyServer(register_xlsx(("1/2018", "Ceste")))  # same cells, new file
    outcome = eojn.fetch_legacy_registers(mock_client(server), BUYERS, tmp_path)

    assert outcome.status == "unchanged"
    assert server.count("GET", "SearchFrm.aspx") == 0
    assert server.count("POST", "SearchFrm.aspx") == 0
    assert server.count("POST", "RptRegistarUgovora.aspx") == 1

    server = FakeLegacyServer(register_xlsx(("1/2018", "Ceste"), ("3/2019", "Vrtić")))
    outcome = eojn.fetch_legacy_registers(mock_client(server), BUYERS, tmp_path)
    assert outcome.status == "ok"
    assert outcome.files[0].changed


def test_fetch_legacy_registers_stops_when_blocked(tmp_path):
    server = FakeLegacyServer(register_xlsx(), generate_status=429)
    outcome = eojn.fetch_legacy_registers(mock_client(server), BUYERS, tmp_path)
    assert outcome.status == "failed"
    assert "HTTP 429" in outcome.message
    assert server.count("POST", "RptRegistarUgovora.aspx") == 1


def test_fetch_legacy_registers_rejects_non_xlsx_export(tmp_path):
    server = FakeLegacyServer(b"<html>session expired</html>")
    outcome = eojn.fetch_legacy_registers(mock_client(server), BUYERS[:1], tmp_path)
    assert outcome.status == "failed"
    assert "not an XLSX" in outcome.message
    assert not (tmp_path / f"{BREZNICKI_HUM}.xlsx").exists()


def test_register_path_falls_back_to_newest_export(tmp_path):
    folder = tmp_path / "minfin_budget_users"
    folder.mkdir()
    (folder / "registar_2025.xlsx").write_bytes(b"old")
    with pytest.raises(FileNotFoundError):
        eojn.register_path(tmp_path / "missing")
    assert eojn.register_path(tmp_path).name == "registar_2025.xlsx"
    (folder / "rkp_register.xlsx").write_bytes(b"new")
    assert eojn.register_path(tmp_path).name == "rkp_register.xlsx"


# ---------------------------------------------------------------------------
# New EOJN API
# ---------------------------------------------------------------------------


def test_api_time_uses_documented_format():
    assert eojn.api_time(datetime(2024, 1, 2, 3, 4, 5, 678912)) == "2024-01-02 03:04:05.6789"


def test_windows_cover_the_range_without_gaps():
    got = list(eojn.windows(datetime(2024, 1, 1), datetime(2024, 1, 10)))
    assert got == [
        (datetime(2024, 1, 1), datetime(2024, 1, 8)),
        (datetime(2024, 1, 8), datetime(2024, 1, 10)),
    ]


class FakeApi:
    """Answers like the eojn.hr API: search in the first week, a change event in the second."""

    def __init__(self, as_json_string: bool = False, status: int = 200):
        self.as_json_string = as_json_string
        self.status = status
        self.requests: list[httpx.Request] = []

    def respond(self, data) -> httpx.Response:
        if self.as_json_string:
            return httpx.Response(200, json=json.dumps(data))
        return httpx.Response(200, json=data)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status != 200:
            return httpx.Response(self.status)
        assert request.headers["X-API-Key"] == "test-key"
        params = request.url.params
        if request.url.path.endswith("/eContractRegister/contractsSearch"):
            first_week = params["publishedDateFrom"].startswith("2024-01-01")
            assert "publisheDateTo" in params  # sic, as in the OpenAPI spec
            if first_week:
                return self.respond(json.loads(fixture("api_contracts_search.json")))
            return self.respond({"contracts": []})
        if request.url.path.endswith("/eProcurementData/eventsForContractsByTime"):
            assert params["from"].endswith(".0000")
            second_week = params["from"].startswith("2024-01-08")
            return self.respond(
                json.loads(fixture("api_events.json")) if second_week else {"events": []}
            )
        if request.url.path.endswith("/eProcurementData/getContractData"):
            assert params["contractId"] == "1001"
            return self.respond(json.loads(fixture("api_contract_1001.json")))
        return httpx.Response(404)

    def paths(self) -> list[str]:
        return [r.url.path.rsplit("/", 1)[-1] for r in self.requests]


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


@pytest.mark.parametrize("as_json_string", [False, True])
def test_sync_contracts_backfills_scope_and_refreshes_changed(tmp_path, as_json_string):
    server = FakeApi(as_json_string=as_json_string)
    api = eojn.EojnApi(mock_client(server), "test-key")
    outcome = eojn.sync_contracts(api, [BREZNICKI_HUM], tmp_path, now=datetime(2024, 1, 10))

    assert outcome.status == "ok"
    contracts = read_jsonl(tmp_path / "contracts.jsonl")
    assert [c["contractId"] for c in contracts] == [1001]  # 2002 is out of scope
    assert contracts[0]["versionNumber"] == 1  # refreshed after the change event
    assert contracts[0]["totalAmount"]["value"] == 44000.0
    assert server.paths().count("getContractData") == 1  # 3003 is unknown: never fetched
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state == {"last_to": "2024-01-10T00:00:00"}


def test_sync_contracts_resumes_from_state_with_overlap(tmp_path):
    api = eojn.EojnApi(mock_client(FakeApi()), "test-key")
    eojn.sync_contracts(api, [BREZNICKI_HUM], tmp_path, now=datetime(2024, 1, 10))

    server = FakeApi()
    api = eojn.EojnApi(mock_client(server), "test-key")
    outcome = eojn.sync_contracts(api, [BREZNICKI_HUM], tmp_path, now=datetime(2024, 1, 12))

    assert outcome.status == "unchanged"
    search = [r for r in server.requests if r.url.path.endswith("contractsSearch")]
    assert len(search) == 1
    assert search[0].url.params["publishedDateFrom"] == "2024-01-09T00:00:00"
    assert [c["versionNumber"] for c in read_jsonl(tmp_path / "contracts.jsonl")] == [1]


def test_merge_contract_keeps_newest_version():
    contracts = {1: {"contractId": 1, "versionNumber": 2, "x": "new"}}
    assert not eojn.merge_contract(contracts, {"contractId": 1, "versionNumber": 1, "x": "old"})
    assert eojn.merge_contract(contracts, {"contractId": 1, "versionNumber": 2, "x": "fix"})
    assert contracts[1]["x"] == "fix"
    assert not eojn.merge_contract(contracts, {"versionNumber": 0})


def test_sync_contracts_reports_rejected_key(tmp_path):
    api = eojn.EojnApi(mock_client(FakeApi(status=401)), "bad-key")
    outcome = eojn.sync_contracts(api, [BREZNICKI_HUM], tmp_path, now=datetime(2024, 1, 10))
    assert outcome.status == "failed"
    assert "HTTP 401" in outcome.message
    assert not (tmp_path / "state.json").exists()


def test_contracts_eojn_is_skipped_without_key(tmp_path, scope, monkeypatch):
    monkeypatch.delenv(eojn.API_KEY_NAME, raising=False)
    source = Source("contracts_eojn", "EOJN", "NN", "https://eojn.hr", "", "", "contracts_eojn")
    ctx = FetchContext(source, mock_client(FakeApi()), scope, tmp_path)
    outcome = eojn.contracts_eojn(ctx)
    assert outcome.status == "skipped"
    assert "eojn@nn.hr" in outcome.message
