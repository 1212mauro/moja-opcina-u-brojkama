import json
from datetime import date
from pathlib import Path

import polars as pl
import pytest
from openpyxl import load_workbook

from opcina_pipeline.parse import contracts as c
from opcina_pipeline.tables import CONTRACT, HRK_PER_EUR

# Trimmed copies of public registers of Grad Ivanec (old EOJN export, Ivanec's own
# data.gov.hr files), an API file shaped like tests/fixtures/eojn, a TED award notice of
# Breznički Hum (contact persons removed) and a copy of it made joint with a second
# buyer; laid out like data/raw/.
RAW = Path(__file__).parent / "fixtures" / "parse_contracts"
TED_NOTICES = RAW / "contracts_ted" / "notices"
IVANEC = "84121580205"
BREZNICKI_HUM = "35774913576"
VRTIC_IVANEC = "37103102119"


@pytest.fixture
def buyers() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "oib": [IVANEC, VRTIC_IVANEC, BREZNICKI_HUM],
            "name": ["GRAD IVANEC", "DJEČJI VRTIĆ IVANČICE IVANEC", "OPĆINA BREZNIČKI HUM"],
            "dzs_code": ["01562", "01562", "01511"],
            "kind": ["unit", "budget_user", "unit"],
        }
    )


@pytest.fixture
def runs_log(tmp_path) -> Path:
    path = tmp_path / "source_runs.jsonl"
    lines = [
        {"id": "contracts_eojn-1", "source": "contracts_eojn", "status": "ok"},
        {"id": "contracts_eojn_legacy-1", "source": "contracts_eojn_legacy", "status": "ok"},
        {"id": "contracts_municipal-1", "source": "contracts_municipal", "status": "unchanged"},
        {"id": "contracts_ted-1", "source": "contracts_ted", "status": "ok"},
    ]
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


# --- values --------------------------------------------------------------------------


def test_to_eur_converts_kuna_at_the_fixed_rate_and_keeps_the_original():
    money = c.to_eur("25.000,00 HRK")
    assert money == c.Money(round(25000 / HRK_PER_EUR, 2), "25.000,00 HRK", "HRK")
    assert money.eur == 3318.07


def test_to_eur_reads_the_currency_of_each_cell():
    assert c.to_eur("6.260,00 EUR") == c.Money(6260.0, "6.260,00 EUR", "EUR")
    assert c.to_eur("1.234.567,89 EUR").eur == 1234567.89
    assert c.to_eur("- 87,94 HRK").eur == -11.67
    assert c.to_eur("150 kn").currency == "HRK"


def test_to_eur_numbers_need_a_currency():
    assert c.to_eur(8636, "EUR") == c.Money(8636.0, "8.636,00 EUR", "EUR")
    assert c.to_eur(None) is None
    assert c.to_eur("  ") is None
    with pytest.raises(ValueError):
        c.to_eur(100)
    with pytest.raises(ValueError):
        c.to_eur("=(9623.25*25%) +9623.25")


def test_split_supplier():
    assert c.split_supplier("SEVOI d.o.o. 86157498303") == ("SEVOI d.o.o.", "86157498303")
    # Foreign identifiers are cut from the name but are not OIBs.
    assert c.split_supplier("APR, Poslovno svetovanje d.o.o. SI23566965") == (
        "APR, Poslovno svetovanje d.o.o.",
        None,
    )
    assert c.split_supplier("MK Projekt ") == ("MK Projekt", None)
    assert c.split_supplier(None) == (None, None)


def test_small_parsers():
    assert c.find_oib("KRIVO_SE_REGISTRIRALI_87607151174") == "87607151174"
    assert c.parse_cpv("39715210-2") == "39715210"
    assert c.parse_cpv("42512000 - Klimatizacijski uređaji") == "42512000"
    assert c.parse_cpv("") is None
    assert c.parse_date("14.06.2022.") == date(2022, 6, 14)
    assert c.parse_date("2024-01-02T00:00:00+01:00") == date(2024, 1, 2)
    assert c.clean_subject("Tromjesečna evidencija ugovora: Toneri: Toneri") == "Toneri"
    assert c.clean_subject("Tromjesečna evidencija ugovora: Ceste: Zimska služba") == (
        "Ceste: Zimska služba"
    )
    assert c.normalise_number(" Ugovor br. 41/2020-SZH ") == "41/2020-szh"
    assert c.normalise_number("KLASA: 406-01/19-01/1") == "klasa:406-01/19-01/1"


# --- layouts -------------------------------------------------------------------------


def test_parse_register_reads_the_old_eojn_export():
    df = c.parse_register(RAW / "contracts_eojn_legacy" / f"{IVANEC}.xlsx", IVANEC, "eojn_legacy")
    # 8 data rows below the header; the spacer row and the footer are not contracts.
    assert df.height == 7
    first = df.row(0, named=True)
    assert first["contract_number"] == "3/18"
    assert first["supplier_name"] == "SEVOI d.o.o."
    assert first["supplier_oib"] == "86157498303"
    assert first["signed_on"] == date(2018, 1, 9)
    assert first["cpv"] == "73300000"
    assert first["procedure"] == "Jednostavna nabava"
    assert first["value_original"] == "25.000,00 HRK"
    assert first["currency_original"] == "HRK"
    assert first["value_eur"] == 3318.07
    assert first["value_with_vat_eur"] == round(31250 / HRK_PER_EUR, 2)
    assert first["record_id"].startswith(f"{IVANEC}:")
    # A 2022 contract updated after the changeover is published in euro.
    eur_2022 = df.filter(pl.col("contract_number") == "669/22").row(0, named=True)
    assert (eur_2022["currency_original"], eur_2022["value_eur"]) == ("EUR", 13792.55)


def test_value_eur_is_the_net_value_even_with_a_vat_typo():
    df = c.parse_register(RAW / "contracts_eojn_legacy" / f"{IVANEC}.xlsx", IVANEC, "eojn_legacy")
    typo = df.filter(pl.col("contract_number") == "302/18").row(0, named=True)
    assert typo["value_eur"] == round(336817.47 / HRK_PER_EUR, 2)
    assert typo["vat_eur"] > typo["value_eur"]  # 8.420.437,00 HRK as published
    assert typo["value_with_vat_eur"] == round(421021.84 / HRK_PER_EUR, 2)


def test_parse_grid_reads_the_new_eojn_export():
    df = c.parse_grid(RAW / "contracts_municipal" / IVANEC / "registar-2024.xlsx")
    assert df.height == 3  # the trailing empty row is skipped
    aris = df.filter(pl.col("contract_number") == "876/23").row(0, named=True)
    assert (aris["record_id"], aris["eojn_id"]) == ("eojn-2620", "2620")
    assert aris["buyer_oib"] == IVANEC
    assert aris["cpv"] == "71242000"
    assert (aris["value_eur"], aris["value_with_vat_eur"], aris["vat_eur"]) == (
        6260.0,
        7825.0,
        1565.0,
    )
    assert aris["currency_original"] == "EUR"
    fortis = df.filter(pl.col("supplier_name") == "fortis labor d.o.o.").row(0, named=True)
    assert fortis["supplier_oib"] == "87607151174"


def test_parse_api_records_skips_reversed_contracts():
    df = c.parse_api_file(RAW / "contracts_eojn" / "contracts.jsonl")
    assert sorted(df["eojn_id"].to_list()) == ["1001", "246843", "4004"]
    hum = df.filter(pl.col("eojn_id") == "1001").row(0, named=True)
    assert hum["buyer_oib"] == BREZNICKI_HUM
    assert hum["subject"] == "Održavanje nerazvrstanih cesta"
    assert hum["contract_number"] == "UG-1/2024"
    assert hum["supplier_oib"] == "00000000001"
    assert hum["signed_on"] == date(2024, 1, 2)
    assert (hum["value_eur"], hum["value_with_vat_eur"]) == (44000.0, 55000.0)
    assert hum["procedure"] == "Otvoreni postupak"


def test_parse_grid_finds_the_header_below_a_title_row(tmp_path):
    # Lepoglava's exports put the register's title above the header.
    workbook = load_workbook(RAW / "contracts_municipal" / IVANEC / "registar-2024.xlsx")
    workbook["Analytics"].insert_rows(1)
    workbook["Analytics"]["A1"] = "REGISTAR SKLOPLJENIH UGOVORA U 2024. GODINI"
    workbook.save(tmp_path / "titled.xlsx")
    assert c.parse_grid(tmp_path / "titled.xlsx").height == 3


def test_parse_municipal_dir_reads_each_publisher_folder():
    df, skipped = c.parse_municipal_dir(RAW / "contracts_municipal")
    assert skipped == [f"{IVANEC}/evidencija-2015.xlsx"]
    assert set(df["system"]) == {"municipal"}
    assert df.height == 4 + 3


def test_parse_ted_notice_gives_one_row_per_signed_contract():
    rows = c.parse_ted_notice(TED_NOTICES / "209718-2025.xml")
    assert [r["record_id"] for r in rows] == ["209718-2025:CON-0001", "209718-2025:CON-0002"]
    lot1, lot2 = rows
    assert {lot1["buyer_oib"], lot2["buyer_oib"]} == {BREZNICKI_HUM}
    # A consortium: every member named, the first one's OIB kept.
    assert lot1["supplier_name"] == "LABOS d.o.o.; CONTECH d.o.o.; ROMING CONSTRUCTIONS d.o.o."
    assert lot1["supplier_oib"] == "48114293272"
    assert (lot1["signed_on"], lot1["value_eur"]) == (date(2024, 10, 9), 169000.0)
    assert lot1["contract_number"] == "2186-24-02-24-21 za grupu 1"
    assert lot1["procedure"] == "Otvoreni postupak"
    # Two lots: the lot's own name follows the procedure's.
    lot_name = lot2["subject"].split(": ")[-1]
    assert lot_name.startswith("Usluga kontrole glavnog i izvedbenog projekta za projekt")
    assert (lot2["supplier_name"], lot2["value_eur"]) == ("StruDes d.o.o.", 9800.0)
    assert lot2["value_with_vat_eur"] is None  # TED gives values without VAT only


def test_parse_ted_dir_keeps_a_contract_once_across_notices(tmp_path):
    # A later notice of the same procedure repeats contracts already reported.
    (tmp_path / "notices").mkdir()
    notice = (TED_NOTICES / "209718-2025.xml").read_bytes()
    (tmp_path / "notices" / "209718-2025.xml").write_bytes(notice)
    (tmp_path / "notices" / "10-2026.xml").write_bytes(notice)
    df = c.parse_ted_dir(tmp_path)
    assert df["record_id"].to_list() == ["209718-2025:CON-0001", "209718-2025:CON-0002"]


def test_parse_ted_notice_skips_joint_procurement():
    # Several buyers: eForms does not say which one signed which contract.
    assert c.parse_ted_notice(TED_NOTICES / "999999-2025.xml") == []


# --- deduplication and the table ----------------------------------------------------


def test_deduplicate_prefers_eojn_then_legacy_then_municipal(runs_log):
    parsed, _, _ = c.parse_all(RAW, runs_log)
    kept, dropped = c.deduplicate(parsed)
    reasons = {(s, r): n for s, r, n in dropped.group_by("system", "reason").len().iter_rows()}
    assert reasons == {
        # 243/23 is registered twice, identically, in both registers.
        ("eojn_legacy", "exact"): 1,
        ("municipal", "exact"): 1,
        # Ivanec's 2018-2023 file repeats the old register (3/18, 302/18, 243/23) ...
        ("municipal", "dup_of:eojn_legacy"): 4,
        # ... its 2024 grid holds 876/23 (signed 2023, re-entered in 2024) and a
        # contract the API also has (same EOJN id).
        ("municipal", "dup_of:eojn"): 1,
    }
    municipal = kept.filter(pl.col("system") == "municipal")
    # Number "31" is reused: the 2025 NET COMPUTERS order went to the API row, and is
    # not taken for the old register's 2019 IVKOM-PLIN contract.
    assert municipal["supplier_name"].to_list() == ["fortis labor d.o.o."]
    assert kept.filter(pl.col("contract_number") == "31").height == 2


def test_number_matches_need_the_same_supplier():
    row = dict.fromkeys(c.PARSED)
    a = {**row, "system": "eojn_legacy", "record_id": "a", "buyer_oib": IVANEC}
    a.update(contract_number="Ugovor o radovima", supplier_oib="11111111111")
    b = {**a, "system": "municipal", "record_id": "b", "supplier_oib": "22222222222"}
    c_ = {**a, "system": "municipal", "record_id": "c", "contract_number": "UGOVOR O RADOVIMA"}
    kept, dropped = c.deduplicate(pl.DataFrame([a, b, c_], schema=c.PARSED))
    assert kept["record_id"].to_list() == ["a", "b"]
    assert dropped["record_id"].to_list() == ["c"]


def test_rows_without_number_match_on_parties_date_and_value():
    row = dict.fromkeys(c.PARSED)
    a = {**row, "system": "eojn", "record_id": "1", "eojn_id": "1", "buyer_oib": IVANEC}
    a.update(supplier_oib="11111111111", signed_on=date(2024, 3, 1), value_eur=100.0)
    b = {**a, "system": "municipal", "record_id": "x", "eojn_id": None}
    d = {**b, "record_id": "y", "value_eur": 200.0}
    kept, _ = c.deduplicate(pl.DataFrame([b, a, d], schema=c.PARSED))
    assert sorted(kept["record_id"].to_list()) == ["1", "y"]


def test_ted_rows_match_a_register_row_signed_the_same_day():
    row = dict.fromkeys(c.PARSED)
    a = {**row, "system": "eojn_legacy", "record_id": "a", "buyer_oib": IVANEC}
    a.update(contract_number="12/24", supplier_oib="11111111111", signed_on=date(2024, 5, 6))
    ted = {**a, "system": "ted", "record_id": "t", "contract_number": "KLASA: 406-01/24"}
    other_day = {**ted, "record_id": "u", "signed_on": date(2024, 5, 7)}
    # A register row is never matched by day: lots of one supplier share a day.
    same_day = {**a, "system": "municipal", "record_id": "m", "contract_number": "13/24"}
    kept, dropped = c.deduplicate(pl.DataFrame([a, ted, other_day, same_day], schema=c.PARSED))
    assert sorted(kept["record_id"].to_list()) == ["a", "m", "u"]
    assert dropped.select("record_id", "reason").rows() == [("t", "dup_of:eojn_legacy")]


def test_combine_contracts_builds_the_contract_table(buyers, runs_log):
    parsed, run_ids, _ = c.parse_all(RAW, runs_log)
    df = c.combine_contracts(parsed, buyers, run_ids)
    assert df.schema == pl.Schema(CONTRACT)
    assert df["contract_key"].is_unique().all()
    assert df.filter(pl.col("buyer_oib") == "00000000009").is_empty()  # out of scope
    assert dict(df.group_by("system").len().iter_rows()) == {
        "eojn": 2,
        "eojn_legacy": 6,
        "municipal": 1,
        "ted": 2,
    }
    ted = df.filter(pl.col("system") == "ted")
    assert set(ted["source_run_id"]) == {"contracts_ted-1"}
    hum = df.filter(pl.col("buyer_oib") == BREZNICKI_HUM).row(0, named=True)
    assert hum["contract_key"] == "eojn:1001"
    assert (hum["dzs_code"], hum["buyer_kind"]) == ("01511", "unit")
    assert hum["source_run_id"] == "contracts_eojn-1"
    legacy = df.filter(pl.col("system") == "eojn_legacy")
    assert set(legacy["source_run_id"]) == {"contracts_eojn_legacy-1"}
    assert set(legacy["buyer_name"]) == {"GRAD IVANEC"}
    assert df.filter(pl.col("system") == "municipal")["contract_key"].to_list() == [
        "municipal:eojn-34239"
    ]


def test_contract_keys_are_stable_across_runs(buyers, runs_log):
    first = c.combine_contracts(*c.parse_all(RAW, runs_log)[:1], buyers, {})
    again = c.combine_contracts(*c.parse_all(RAW, runs_log)[:1], buyers, {})
    assert first["contract_key"].to_list() == again["contract_key"].to_list()


def test_without_the_api_the_municipal_grid_row_is_kept(buyers, runs_log):
    parsed, run_ids, _ = c.parse_all(RAW, runs_log)
    without_api = parsed.filter(pl.col("system") != "eojn")
    df = c.combine_contracts(without_api, buyers, run_ids)
    assert set(df["system"]) == {"eojn_legacy", "municipal", "ted"}
    # The NET COMPUTERS order now comes from Ivanec's own grid.
    assert "municipal:eojn-246843" in df["contract_key"].to_list()
