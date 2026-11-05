"""Varaždin's hand-saved payment exports. All names and OIBs here are synthetic."""

from datetime import date

import polars as pl
import pytest

from opcina_pipeline import varazdin

HEADER = ";".join(varazdin.EXPORT_COLUMNS)


def export(path, rows: list[str]) -> None:
    path.write_text("﻿" + HEADER + "\r\n" + "\r\n".join(rows) + "\r\n", encoding="utf-8")


CITY = "GRAD VARAŽDIN UPRAVNI ODJEL"


def row(*cells: str) -> str:
    return ";".join(cells)


# Rbr; date; payer; recipient; postcode; town; OIB; amount; currency; purpose; expense type
ROW_1 = row("1", "20261030", CITY, "GAMA D.O.O.", "42000", "VARAŽDIN", "44444444446",
            "1.201,29", "EUR", "Račun 7/26", "3222 Materijal i sirovine")  # fmt: skip
ROW_2 = row("2", "20261030", CITY, "Ivan Horvat", "42000", "VARAŽDIN", "12345678903",
            "80,00", "EUR", "Naknada Ivan Horvat", "3237 Intelektualne usluge")  # fmt: skip
ROW_3 = row("3", "20261002", "DJEČJI VRTIĆ VARAŽDIN", "GAMA D.O.O.", "42000", "VARAŽDIN",
            "44444444446", "10,00", "EUR", "", "3222 Materijal i sirovine")  # fmt: skip
ROW_5 = row("5", "20261001", CITY, "DELTA D.O.O.", "42000", "VARAŽDIN", "55555555557",
            "5,00", "EUR", "", "3223 Energija")  # fmt: skip


def test_export_link_is_the_portals_own_page_link():
    link = varazdin.export_link("2026-10")
    assert link.startswith("https://transparentni.varazdin.hr/Pretraga/GetExport/Godine%3D2026")
    assert "Mjeseci%3D10%26Uprave%3D0" in link
    assert "preskoci%3D0%26uzmi%3D80" in link and link.endswith("?exportType=1")
    assert "preskoci%3D160%26uzmi%3D80" in varazdin.export_link("2026-10", page=3)


def test_read_export_parses_dates_and_croatian_amounts(tmp_path):
    export(tmp_path / "a.csv", [ROW_1])
    (row,) = varazdin.read_export(tmp_path / "a.csv")
    assert (row.number, row.paid_on, row.amount_eur) == (1, date(2026, 10, 30), 1201.29)
    assert row.expense == "3222 Materijal i sirovine"


def test_read_export_refuses_another_layout(tmp_path):
    (tmp_path / "a.csv").write_text("Datum;Iznos\n1;2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not a transparentni.varazdin.hr export"):
        varazdin.read_export(tmp_path / "a.csv")


def test_import_cleans_dedups_and_reports_gaps(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    inbox.mkdir()
    export(inbox / "page1.csv", [ROW_1, ROW_2, ROW_3])
    export(inbox / "page1-again.csv", [ROW_1, ROW_2, ROW_3])  # the same page saved twice
    export(inbox / "GetExport", [ROW_5])  # row 4 never saved; saved without an extension

    result = varazdin.import_inbox(inbox, out, known_oibs=frozenset({"44444444446"}))

    assert result.months == {"2026-10": 4}  # 7 rows saved, the repeated page collapses
    assert sorted(result.moved) == ["GetExport", "page1-again.csv", "page1.csv"]
    assert [p.name for p in inbox.iterdir()] == ["done"] and len(
        list((inbox / "done").iterdir())
    ) == 3
    assert any("rows 4 are missing" in w for w in result.warnings)

    cleaned = pl.read_csv(out / "2026-10.csv", infer_schema=False)
    assert cleaned.columns == varazdin.CLEANED_COLUMNS
    text = (out / "2026-10.csv").read_text(encoding="utf-8")
    # The person is kept only as an anonymous amount; descriptions never leave the inbox.
    assert "Horvat" not in text and "12345678903" not in text and "Račun" not in text
    assert "GAMA D.O.O." in text
    # A company by its legal form keeps its name; an OIB failing the checksum is dropped.
    assert "DELTA D.O.O.,," in text


def test_import_rebuilds_a_month_from_all_saved_pages(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    inbox.mkdir()
    export(inbox / "page1.csv", [ROW_1])
    varazdin.import_inbox(inbox, out, known_oibs=frozenset())
    export(inbox / "page2.csv", [ROW_3])  # saved a week later
    varazdin.import_inbox(inbox, out, known_oibs=frozenset())
    assert pl.read_csv(out / "2026-10.csv").height == 2


def test_nothing_to_import(tmp_path):
    result = varazdin.import_inbox(tmp_path, tmp_path / "out", known_oibs=frozenset())
    assert (result.months, result.moved) == ({}, [])


def test_an_empty_page_past_the_end_is_no_rows(tmp_path):
    (tmp_path / "empty.csv").write_bytes(b"")
    assert varazdin.read_export(tmp_path / "empty.csv") == []
