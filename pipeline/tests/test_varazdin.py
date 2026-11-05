"""Varaždin's official payments export. All names and OIBs here are synthetic."""

from datetime import date

import polars as pl
import pytest

from opcina_pipeline import varazdin

HEADER = ";".join(varazdin.EXPORT_COLUMNS)
CITY = "GRAD VARAŽDIN UPRAVNI ODJEL"


def export(path, rows: list[str]) -> None:
    lines = [HEADER, *rows]
    path.write_text("﻿" + "\r\n".join(lines) + "\r\n", encoding="utf-8")


def row(*cells: str) -> str:
    return ";".join(cells)


# Rbr; date; payer; recipient; postcode; town; OIB; amount; currency; purpose; expense type
ROW_1 = row("1", "20261030", CITY, "GAMA D.O.O.", "42000", "VARAŽDIN", "44444444446",
            "1.201,29", "EUR", "Račun 7/26", "3222 Materijal i sirovine")  # fmt: skip
ROW_2 = row("2", "20261030", CITY, "Ivan Horvat", "42000", "VARAŽDIN", "12345678903",
            "80,00", "EUR", "Naknada Ivan Horvat", "3237 Intelektualne usluge")  # fmt: skip


def test_official_urls_per_month_or_one():
    months = ["2026-09", "2026-10"]
    assert varazdin.official_urls("https://x/{year}/{month}.csv", months) == {
        "2026-09": "https://x/2026/09.csv",
        "2026-10": "https://x/2026/10.csv",
    }
    assert varazdin.official_urls("https://x/?m={month_int}", ["2026-09"]) == {
        "2026-09": "https://x/?m=9"
    }
    assert varazdin.official_urls("https://example.com/", months) == {"all": "https://example.com/"}


def test_read_export_parses_dates_and_croatian_amounts(tmp_path):
    export(tmp_path / "a.csv", [ROW_1])
    (parsed,) = varazdin.read_export(tmp_path / "a.csv")
    assert (parsed.number, parsed.paid_on, parsed.amount_eur) == (1, date(2026, 10, 30), 1201.29)
    assert parsed.expense == "3222 Materijal i sirovine"


def test_read_export_refuses_another_layout_and_accepts_an_empty_answer(tmp_path):
    (tmp_path / "html.csv").write_text("<!doctype html>", encoding="utf-8")
    with pytest.raises(ValueError, match="not the payments export layout"):
        varazdin.read_export(tmp_path / "html.csv")
    (tmp_path / "empty.csv").write_bytes(b"")
    assert varazdin.read_export(tmp_path / "empty.csv") == []


def test_cleaned_files_hold_only_what_the_site_publishes(tmp_path):
    export(tmp_path / "a.csv", [ROW_1, ROW_2])
    rows = varazdin.read_export(tmp_path / "a.csv")
    known = frozenset({"44444444446"})
    assert varazdin.write_cleaned({"2026-10": rows}, tmp_path / "out", known) == {"2026-10": 2}
    path = tmp_path / "out" / "2026-10.csv"
    assert pl.read_csv(path).columns == varazdin.CLEANED_COLUMNS
    text = path.read_text(encoding="utf-8")
    # The person is kept only as an anonymous amount; descriptions are never written.
    assert "Horvat" not in text and "12345678903" not in text and "Račun" not in text
    assert "GAMA D.O.O." in text


def test_read_export_decodes_html_entities_before_splitting(tmp_path):
    escaped = row("3", "20261027", CITY, "ŠMEK&amp;SNACK j.d.o.o.", "42000", "Varaždin",
                  "", "430,32", "EUR", "", "3522 Subvencije", "")  # fmt: skip
    export(tmp_path / "a.csv", [escaped])
    (parsed,) = varazdin.read_export(tmp_path / "a.csv")
    assert (parsed.recipient, parsed.amount_eur) == ("ŠMEK&SNACK j.d.o.o.", 430.32)


def test_a_row_with_several_accounts_takes_the_first(tmp_path):
    payroll = row("4", "20261015", CITY, "Zaposlenici", "", "", "", "100,00", "EUR", "",
                  "3111 Plaće za redovan rad, 3121 Ostali rashodi, 3132 Doprinosi")  # fmt: skip
    export(tmp_path / "a.csv", [payroll])
    frame = varazdin.raw_frame(varazdin.read_export(tmp_path / "a.csv"))
    assert frame.select("economic_code", "economic_label").row(0) == (
        "3111",
        "Plaće za redovan rad",
    )
