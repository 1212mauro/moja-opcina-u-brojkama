"""Monthly payments parser: platforms, personal-data rules, ODS reconciliation.

All names and OIBs in these tests and fixtures are synthetic.
"""

import json
import zipfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

import polars as pl
import pytest

from opcina_pipeline.parse import payments as P
from opcina_pipeline.tables import PAYMENT

FIXTURES = Path(__file__).parent / "fixtures" / "parse_payments"
RUN = "payments-test"


# --- ODS fixtures, written as files so the reader under test is the real one ---------

_CONTENT = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
    ' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"'
    ' xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.2">'
    '<office:body><office:spreadsheet><table:table table:name="List1">{rows}'
    "</table:table></office:spreadsheet></office:body></office:document-content>"
)
_MANIFEST = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">'
    '<manifest:file-entry manifest:full-path="/"'
    ' manifest:media-type="application/vnd.oasis.opendocument.spreadsheet"/>'
    '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
    "</manifest:manifest>"
)


def _cell(value) -> str:
    if value is None:
        return "<table:table-cell/>"
    if isinstance(value, float | int):
        return (
            f'<table:table-cell office:value-type="float" office:value="{value!r}">'
            f"<text:p>{value}</text:p></table:table-cell>"
        )
    return (
        '<table:table-cell office:value-type="string">'
        f"<text:p>{escape(value)}</text:p></table:table-cell>"
    )


def write_ods(path: Path, rows: list[list]) -> Path:
    body = "".join(
        "<table:table-row>" + "".join(_cell(v) for v in row) + "</table:table-row>" for row in rows
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.spreadsheet")
        archive.writestr("META-INF/manifest.xml", _MANIFEST, zipfile.ZIP_DEFLATED)
        archive.writestr("content.xml", _CONTENT.format(rows=body), zipfile.ZIP_DEFLATED)
    return path


PAYER = "Općina Primjer"
EMPTY = [None] * 7
HEADER = [
    "Datum ",
    "Naziv isplatitelja ",
    "Naziv primatelja",
    "OIB primatelja",
    "Sjedište  primatelja",
    "Način objave isplaćenog iznosa",
    "Vrsta rashoda i izdataka",
]


def ods_rows(total="1515.42", title="INFORMACIJE O TROŠENJU SREDSTAVA ZA SIJEČANJ 2026. GODINE"):
    rows = [
        [PAYER, *EMPTY[1:]],
        ["Sjedište: Primjer", *EMPTY[1:]],
        ["Adresa: Primjer 1", *EMPTY[1:]],
        ["Matični broj: 00000000", *EMPTY[1:]],
        ["OIB: 12345678903", *EMPTY[1:]],
        EMPTY,
        [title, *EMPTY[1:]],
        EMPTY,
        HEADER,
        [
            "05.01.2026.",
            PAYER,
            "Plaća za zaposlene za 12/25",
            None,
            None,
            1000.1,
            "3111 Bruto plaće",
        ],
        # Continuation row: same payment, another account.
        [None, None, None, None, None, 165.02, "3132 Doprinos na bruto "],
        # Year typo (2025 in the January 2026 file); leading zero of the OIB dropped;
        # float noise in the amount.
        [
            "10.01.2025.",
            PAYER,
            "Zeta d.o.o.",
            "9876543211",
            "Primjer",
            100.304,
            "3234 Komunalne usluge",
        ],  # fmt: skip
        [
            "12.01.2026.",
            PAYER,
            "Mrazić",
            None,
            None,
            50,
            "3237 Intelektualne i osobne usluge (ugovor o djelu)",
        ],  # fmt: skip
        [
            "2026-01-20T00:00:00",
            PAYER,
            "Isplata fizičkim osobama",
            None,
            None,
            "200",
            "3721 Naknade građanima i kućanstvima u novcu",
        ],  # fmt: skip
        EMPTY,
    ]
    if total is not None:
        rows.append(["UKUPNO ZA SIJEČANJ 2026.", None, None, None, None, total, None])
    return rows


# --- OIB ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("oib", "valid"),
    [("12345678903", True), ("12345678904", False), ("1234567890", False), ("GDPR", False)],
)
def test_oib_check_digit(oib, valid):
    assert P.oib_is_valid(oib) is valid


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("12345678903", "12345678903"),
        ("  12345678903 ", "12345678903"),
        ("9876543211", "09876543211"),  # leading zero lost in a spreadsheet
        ("12345678904", None),  # bad check digit
        ("00000000001", None),  # placeholder for foreign payees
        ("GDPR", None),
        ("SI12250821", None),
        ("", None),
        (None, None),
    ],
)
def test_clean_oib(raw, clean):
    assert P.clean_oib(raw) == clean


# --- Personal data rules -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "oib", "code", "label", "payer", "rule"),
    [
        ("Fizičke osobe", "GDPR", "372120", "Naknade", "GRAD PRIMJER", "publisher_gdpr"),
        # The GDPR marker wins even on a company name.
        ("PRIMJER d.o.o.", "GDPR", "3232", "Usluge", "GRAD PRIMJER", "publisher_gdpr"),
        ("Isplata fizičkoj osobi (novčana pomoć)", None, "3721", "", None, "aggregate_label"),
        ("Isplata zaposleniku", None, "3214", "", None, "aggregate_label"),
        ("PLAĆA PK - NETO PLAĆA PK", "", "3111", "", None, "aggregate_label"),
        ("Naknada za sjednice", None, "3291", "", None, "aggregate_label"),
        ("Ugovor o djelu 01/26", None, "3237", "", None, "aggregate_label"),
        (
            "Pero Perić, sporedno zanimanje, soboslikar",
            "22222222226",
            "3232",
            "",
            None,
            "aggregate_label",
        ),  # fmt: skip
        (
            "OPĆINA PRIMJER",
            "09876543211",
            "3111",
            "PLAĆE",
            "OPĆINA PRIMJER",
            "self_personal_account",
        ),  # fmt: skip
        ("Horvat Ivana", "22222222226", "3237", "", None, "person_name"),
        ("IVANA HORVAT", None, "3237", "", None, "person_name"),
        ("Šimić-Horvat Ana Marija", "22222222226", "3299", "", None, "person_name"),
        ("I. Horvat", None, "3299", "", None, "person_name"),
        (
            "Mrazić",
            None,
            "3237",
            "Intelektualne usluge (ugovor o djelu)",
            None,
            "personal_account",
        ),  # fmt: skip
        ("Primjerić", None, "3299", "Ostalo", None, "surname_no_oib"),
        # Legal persons and registered businesses keep their name.
        (
            "OPĆINA PRIMJER",
            "09876543211",
            "3431",
            "USLUGE PLATNOG PROMETA",
            "OPĆINA PRIMJER",
            None,
        ),  # fmt: skip
        ("ALFA GRADNJA d.o.o.", "12345678903", "3232", "", None, None),
        ("DELTA, OBRT ZA USLUGE, VL. ANA ANIĆ", "01234567896", "3239", "", None, None),
        ("OPG Ivan Horvat", "22222222226", "3299", "", None, None),
        ("Udruga Sveti Marko", "33333333335", "3811", "", None, None),
        ("Javni bilježnik Ivana Horvat", "22222222226", "3237", "", None, None),
        ("FOREIGN HOTEL LTD", "00000000001", "3211", "Službena putovanja", None, None),
        ("METRO LONDON", "", "3211", "Službena putovanja", None, None),
        ("VARKOM", "39048902955", "3721", "Naknade građanima", None, None),
        ("Porez na dohodak", None, "3299", "", None, None),
    ],
)
def test_natural_person_rule(name, oib, code, label, payer, rule):
    assert P.natural_person_rule(name, oib, code, label, payer) == rule


def test_finish_blanks_names_oibs_and_descriptions_of_natural_persons():
    raw = pl.DataFrame(
        [
            {
                "paid_on": date(2026, 1, 5),
                "payer_name": "GRAD PRIMJER",
                "recipient_name": "Horvat Ivana",
                "recipient_oib": "22222222226",
                "economic_code": "323790",
                "economic_label": "Ostale intelektualne usluge",
                "function_code": "0820",
                "description": "radionica - Ivana Horvat",
                "amount_eur": 10.004,
            }
        ],
        schema=P.RAW_COLUMNS,
    )
    row = P.finish(raw, "99999", RUN).row(0, named=True)
    assert row["natural_person"] is True
    assert row["natural_person_rule"] == "person_name"
    assert (row["recipient_name"], row["recipient_oib"], row["description"]) == (None,) * 3
    assert (row["economic_code"], row["month"], row["amount_eur"]) == ("3237", "2026-01", 10.0)


# --- Helpers ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "value"),
    [("1391.00", 1391.0), ("1.234,56", 1234.56), ("12,5", 12.5), ("-20.00", -20.0),
     (" 3 000 ", 3000.0), ("", None), (None, None)],
)  # fmt: skip
def test_parse_amount(text, value):
    assert P.parse_amount(text) == value


@pytest.mark.parametrize(
    "text",
    ["03.01.2025.", "3.1.2025", "2025-01-03", "2025-01-03T00:00:00.000Z", "03. 01. 2025."],
)
def test_parse_date(text):
    assert P.parse_date(text) == date(2025, 1, 3)


def test_parse_date_rejects_unknown_format():
    with pytest.raises(ValueError, match="unrecognised date"):
        P.parse_date("siječanj 2025")


@pytest.mark.parametrize(
    ("text", "period"),
    [
        ("INFORMACIJA O TROŠENJU SREDSTAVA ZA  SIJEČANJ 2025. GODINIE", (2025, 1)),
        ("INFORMACIJE O TROŠENJU SREDSTAVA ZA OŽUJAK 2026.GODINE", (2026, 3)),
        ("UKUPNO ZA VELJAČU 2026.", (2026, 2)),
        ("UKUPNO ZA STUDENI 2024.", (2024, 11)),
        ("Općina Primjer", None),
    ],
)
def test_stated_period(text, period):
    assert P.stated_period(text) == period


# --- Otvoreni grad ---------------------------------------------------------------------


def test_otvorenigrad():
    df = P.finish(P.parse_otvorenigrad(FIXTURES / "otvorenigrad"), "01562", RUN)
    # The row without an amount is dropped; the two positions of one invoice are summed;
    # the two anonymous benefit rows of one day are summed too.
    assert df.height == 7
    assert df["description"].is_null().all()

    company = df.filter(pl.col("recipient_oib") == "12345678903").row(0, named=True)
    assert company["amount_eur"] == 1250.5
    assert company["economic_code"] == "3232"
    assert company["economic_label"] == "Usluge tekućeg i investicijskog održavanja"
    assert company["function_code"] == "0451"
    assert company["paid_on"] == date(2026, 1, 15)

    natural = df.filter(pl.col("natural_person"))
    assert natural["recipient_name"].is_null().all()
    assert natural["recipient_oib"].is_null().all()
    assert sorted(natural["natural_person_rule"]) == [
        "person_name",
        "publisher_gdpr",
        "publisher_gdpr",
    ]
    assert sorted(natural["amount_eur"]) == [150.0, 500.0, 812.4]
    assert "Horvat Ivana" not in df["recipient_name"].to_list()

    hotel = df.filter(pl.col("recipient_name") == "FOREIGN HOTEL LTD").row(0, named=True)
    assert hotel["recipient_oib"] is None and hotel["natural_person"] is False

    refund = df.filter(pl.col("recipient_name") == "BETA d.o.o.").row(0, named=True)
    assert refund["payer_name"] == "DJEČJI VRTIĆ PRIMJER"
    assert refund["recipient_oib"] == "33333333335"
    assert refund["amount_eur"] == -20.0

    interest = df.filter(pl.col("recipient_name") == "BANKA KAMATE POOL").row(0, named=True)
    assert interest["function_code"] is None and interest["recipient_oib"] is None


def test_otvorenigrad_refuses_other_currencies(tmp_path):
    text = (FIXTURES / "otvorenigrad" / "2026-01.csv").read_text(encoding="utf-8")
    (tmp_path / "2026-01.csv").write_text(text.replace('"EUR"', '"HRK"'), encoding="utf-8")
    with pytest.raises(ValueError, match="currencies"):
        P.parse_otvorenigrad(tmp_path)


# --- Kipos -----------------------------------------------------------------------------


def test_kipos():
    df = P.finish(P.parse_kipos(FIXTURES / "kipos"), "01651", RUN)
    assert df.height == 6
    assert df["function_code"].is_null().all()
    by_code = {row["economic_code"]: row for row in df.iter_rows(named=True)}

    assert by_code["3232"]["recipient_name"] == "GAMA D.O.O."
    assert by_code["3232"]["recipient_oib"] == "44444444446"
    # The municipality naming itself on a salary payment stands for its employees.
    assert by_code["3111"]["natural_person"] is True
    assert by_code["3111"]["recipient_name"] is None
    # ...but on bank fees it is just itself.
    assert by_code["3431"]["recipient_name"] == "OPĆINA PRIMJER"
    assert by_code["3431"]["natural_person"] is False
    # A person published by name and OIB.
    assert by_code["3237"]["natural_person"] is True
    assert by_code["3237"]["recipient_oib"] is None
    # A sole trader keeps the registered business name.
    assert by_code["3239"]["recipient_name"] == "DELTA, OBRT ZA USLUGE, VL. ANA ANIĆ"
    # Analytic sub-accounts are cut to the 4-digit account; refunds stay negative.
    assert by_code["3811"]["amount_eur"] == -5.0
    assert by_code["3811"]["month"] == "2022-01"


def test_kipos_accepts_a_plain_list(tmp_path):
    rows = (FIXTURES / "kipos" / "payments.json").read_text(encoding="utf-8")
    plain = json.loads(rows)[0]["tableData"]
    (tmp_path / "payments.json").write_text(json.dumps(plain), encoding="utf-8")
    assert P.parse_kipos(tmp_path).height == 6


# --- Breznički Hum ODS -----------------------------------------------------------------


def test_ods_file(tmp_path):
    raw, period = P.parse_ods_file(write_ods(tmp_path / "Informacije_01-26.ods", ods_rows()))
    assert period == (2026, 1)
    assert raw.height == 5
    df = P.finish(raw, "01511", RUN)
    assert round(df["amount_eur"].sum(), 2) == 1515.42
    assert df["month"].unique().to_list() == ["2026-01"]  # the 2025 typo is corrected

    salary = df.filter(pl.col("economic_code").is_in(["3111", "3132"]))
    assert salary.height == 2
    assert salary["natural_person"].all()
    assert set(salary["paid_on"]) == {date(2026, 1, 5)}  # continuation row inherits

    zeta = df.filter(pl.col("recipient_name") == "Zeta d.o.o.").row(0, named=True)
    assert zeta["recipient_oib"] == "09876543211"
    assert zeta["amount_eur"] == 100.3
    assert zeta["paid_on"] == date(2026, 1, 10)

    assert df.filter(pl.col("natural_person")).height == 4
    assert df.filter(pl.col("natural_person"))["recipient_name"].is_null().all()


def test_ods_reconciliation_failure(tmp_path):
    path = write_ods(tmp_path / "bad.ods", ods_rows(total="1515.43"))
    with pytest.raises(P.ReconciliationError, match="1515.42.*1515.43"):
        P.parse_ods_file(path)


def test_ods_without_total(tmp_path):
    with pytest.raises(P.ReconciliationError, match="no UKUPNO"):
        P.parse_ods_file(write_ods(tmp_path / "x.ods", ods_rows(total=None)))


def test_ods_two_files_for_one_month(tmp_path):
    write_ods(tmp_path / "Informacije_01-26.ods", ods_rows())
    write_ods(tmp_path / "Informacije_Sijecanj_2026.ods", ods_rows())
    with pytest.raises(ValueError, match="both cover"):
        P.parse_html_links(tmp_path)


# --- build_payments --------------------------------------------------------------------


def test_build_payments(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "latest_run_id", lambda source: f"{source}-run")
    raw = tmp_path / "payments"
    for code, name in [("01562", "otvorenigrad"), ("01651", "kipos")]:
        (raw / code).mkdir(parents=True)
        for file in (FIXTURES / name).iterdir():
            (raw / code / file.name).write_bytes(file.read_bytes())
    (raw / "01511").mkdir()
    write_ods(raw / "01511" / "Informacije_01-26.ods", ods_rows())
    platforms = {
        "04723": {"platform": "unavailable", "reason": "captcha"},
        "01562": {"platform": "otvorenigrad", "tenant": "x"},
        "01651": {"platform": "kipos", "base_url": "x"},
        "01511": {"platform": "html_links", "page": "x", "pattern": "x"},
        "02445": {"platform": "otvorenigrad", "tenant": "y"},  # nothing on disk yet
    }
    # An explicit known-OIB set keeps the test off the real RKP register in data/raw/.
    df = P.build_payments(raw, platforms, known_oibs=frozenset())
    assert dict(df.schema) == PAYMENT
    assert sorted(df["dzs_code"].unique()) == ["01511", "01562", "01651"]
    assert set(df["source_run_id"]) == {"payments-run"}
    natural = df.filter(pl.col("natural_person"))
    assert natural["recipient_name"].is_null().all() and natural["recipient_oib"].is_null().all()
    assert df["description"].is_null().all()


def test_recipient_without_org_marker_needs_a_known_oib():
    from opcina_pipeline.parse.payments import natural_person_rule

    known = frozenset({"94577403194"})
    # No legal form, no first name on the list, valid OIB: only a known OIB keeps the name.
    assert (
        natural_person_rule("NISKOGRADNJA HUĐEK", "94577403194", "3232", "Usluge", None, known)
        is None
    )
    assert (
        natural_person_rule("KOVAČ ŽELJANA", "69435151530", "3721", "Pomoći", None, known)
        == "unverified"
    )
    # Organisations recognised by their name never need the OIB check.
    assert (
        natural_person_rule("Primjer d.o.o.", "69435151530", "3232", "Usluge", None, known) is None
    )
    # Without a known-OIB list the old behaviour stands (used by unit tests of other rules).
    assert natural_person_rule("KOVAČ ŽELJANA", "69435151530", "3721", "Pomoći") is None
