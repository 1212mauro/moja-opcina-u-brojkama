from pathlib import Path

import openpyxl
import polars as pl
import pytest

from opcina_pipeline.parse.budget import (
    check_budget,
    load_layout,
    parse_sheet,
    parse_workbook,
    read_workbook,
)
from opcina_pipeline.tables import conform

LAYOUT_PATH = Path(__file__).parents[1] / "config" / "budget_layout.toml"
HEADER = [
    "Račun iz rač. plana",
    "Opis stavke",
    "Pozicija u obrascu",
    "Ostvareno u 2024",
    "Indeks 2024/2023",
    "Ostvareno u 2025",
    "Indeks 2025/2024",
]


def metadata(unit: str, currency: str = "Euro") -> list[list]:
    return [
        [None, "Obrasci PR-RAS i RAS-funkcijski za: "],
        [None, "Testna županija"],
        [None, unit],
        ["Razina:", "22"],
        ["Izvještajno razdoblje:", "I-XII"],
        ["Valuta: ", currency],
    ]


def line(account, label, position, y2024, y2025) -> list:
    """A data row; the Indeks cells are formulas, as in the real file."""
    return [account, label, position, y2024, "=IF(D1>0,E1/D1,0)", y2025, "=IF(F1>0,G1/F1,0)"]


# Consistent totals: X067 = 6 + 7, Y034 = Z005 + 4, R1 = 01 + 02 = Y034 - 367.
BODY = [
    [1, 2, 3, 4, 5, 6, 7],  # column numbers under the header
    ["PRIHODI I RASHODI, PRIMICI I IZDACI PREMA EKONOMSKOJ KLASIFIKACIJI", None, None, None],
    line(6, "Prihodi poslovanja", 6, 80, 100),
    line(61, "Prihodi od poreza", 61, 80, 100),
    line(611, "Porez i prirez na dohodak", 611, 80, 100),
    line(3, "Rashodi poslovanja", 3, 60, 90),
    line(36, "Pomoći", 36, 0, 30),
    line(367, "Prijenosi proračunskim korisnicima", 367, 0, 30),
    line("3824", "Donacije neprofitnim organizacijama", "3824", None, 0),
    line(" ", "Ukupni rashodi poslovanja", "Z005", 60, 90),
    line(7, "Prihodi od prodaje nefinancijske imovine", 7, 0, 20),
    line(4, "Rashodi za nabavu nefinancijske imovine", 4, 0, 10),
    line(" ", "UKUPNI PRIHODI", "X067", 80, 120),
    line(" ", "UKUPNI RASHODI", "Y034", 60, 100),
    line("96, 97", "Obračunati prihodi - nenaplaćeni", 96.97, 0, 5),
    line(92213, "Višak primitaka - preneseni", 92213, 1, 2),
    [None],
    ["RASHODI PREMA FUNKCIJSKOJ KLASIFIKACIJI"],
    line("01", "Opće javne usluge", "01", 60, 50),
    line("011", "Izvršna i zakonodavna tijela", "011", 60, 50),
    line("0111", "Izvršna i zakonodavna tijela", "0111", 60, 50),
    line("02", "Obrana", "02", 0, 20),
    line(None, "Kontrolni zbroj", "R1", 60, 70),
]


def sheet_rows(unit: str = "GRAD TESTNI", body: list[list] = BODY, **kwargs) -> list[list]:
    return [*metadata(unit, **kwargs), HEADER, *body]


def write_workbook(path: Path, sheets: dict[str, list[list]]) -> Path:
    workbook = openpyxl.Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        for row in rows:
            sheet.append(row)
    workbook.save(path)
    return path


@pytest.fixture
def layout():
    return load_layout(LAYOUT_PATH)


@pytest.fixture
def master() -> pl.DataFrame:
    return pl.DataFrame({"official_name": ["GRAD TESTNI"], "dzs_code": ["09999"]})


def read_sheet(tmp_path: Path, rows: list[list]) -> pl.DataFrame:
    path = write_workbook(tmp_path / "budget.xlsx", {"GRAD TESTNI": rows})
    return read_workbook(path)["GRAD TESTNI"]


def amount(df: pl.DataFrame, code: str, year: int) -> float:
    return df.filter(pl.col("code") == code, pl.col("year") == year)["amount_eur"].item()


def test_parses_codes_as_text_with_classification_and_level(tmp_path, layout):
    df = parse_sheet(read_sheet(tmp_path, sheet_rows()), layout)

    codes = df.filter(pl.col("year") == 2025).select("code", "classification", "level")
    assert codes.rows() == [
        ("6", "economic", 1),
        ("61", "economic", 2),
        ("611", "economic", 3),
        ("3", "economic", 1),
        ("36", "economic", 2),
        ("367", "economic", 3),
        ("3824", "economic", 4),
        ("Z005", "derived", 0),
        ("7", "economic", 1),
        ("4", "economic", 1),
        ("X067", "derived", 0),
        ("Y034", "derived", 0),
        ("96,97", "derived", 0),  # Excel's number 96.97, mapped back by an alias
        ("92213", "economic", 5),
        ("01", "function", 2),  # leading zeros kept
        ("011", "function", 3),
        ("0111", "function", 4),
        ("02", "function", 2),
        ("R1", "derived", 0),
    ]
    assert set(df["period"]) == {"FY"}
    assert (
        df.filter(pl.col("code") == "611")["label"].to_list() == ["Porez i prirez na dohodak"] * 2
    )


def test_melts_years_and_skips_header_numbers_and_indeks(tmp_path, layout):
    df = parse_sheet(read_sheet(tmp_path, sheet_rows()), layout)

    assert sorted(df["year"].unique()) == [2024, 2025]
    # The column-number row under the header ("3" in Pozicija, 6 in 2025) is not data.
    assert amount(df, "3", 2025) == 90
    assert amount(df, "X067", 2024) == 80


def test_drops_empty_amounts_and_keeps_zeros(tmp_path, layout):
    df = parse_sheet(read_sheet(tmp_path, sheet_rows()), layout)

    assert df.filter(pl.col("code") == "3824")["year"].to_list() == [2025]
    assert amount(df, "3824", 2025) == 0
    assert amount(df, "7", 2024) == 0


def test_finds_header_when_leading_rows_are_empty(tmp_path, layout):
    rows = [[None], [None], *sheet_rows()]
    df = parse_sheet(read_sheet(tmp_path, rows), layout)
    assert amount(df, "Y034", 2025) == 100


def test_refuses_a_sheet_in_another_currency(tmp_path, layout):
    grid = read_sheet(tmp_path, sheet_rows(currency="Kuna"))
    with pytest.raises(ValueError, match="Valuta"):
        parse_sheet(grid, layout)


def test_refuses_repeated_positions(tmp_path, layout):
    body = [*BODY[:3], line(6, "Prihodi poslovanja (ponovno)", 6, 1, 2), *BODY[3:]]
    with pytest.raises(ValueError, match="more than once"):
        parse_sheet(read_sheet(tmp_path, sheet_rows(body=body)), layout)


def test_refuses_a_sheet_without_function_heading(tmp_path, layout):
    body = [row for row in BODY if row[:1] != ["RASHODI PREMA FUNKCIJSKOJ KLASIFIKACIJI"]]
    with pytest.raises(ValueError, match="FUNKCIJSKOJ"):
        parse_sheet(read_sheet(tmp_path, sheet_rows(body=body)), layout)


def test_workbook_maps_units_and_skips_aggregates(tmp_path, layout, master):
    path = write_workbook(
        tmp_path / "budget.xlsx",
        {"UKUPNO GRADOVI ": sheet_rows("UKUPNO GRADOVI"), "GRAD TESTNI": sheet_rows()},
    )
    df = parse_workbook(read_workbook(path), master, layout)

    assert set(df["dzs_code"]) == {"09999"}
    budget = conform(df.with_columns(source_run_id=pl.lit("minfin_budget-test")), "budget_line")
    assert budget.height == df.height
    check_budget(budget)


def test_workbook_refuses_unknown_sheets_and_missing_units(tmp_path, layout, master):
    path = write_workbook(tmp_path / "budget.xlsx", {"GRAD NEPOZNATI": sheet_rows()})
    sheets = read_workbook(path)
    with pytest.raises(ValueError, match="neither units nor known aggregates"):
        parse_workbook(sheets, master, layout)
    with pytest.raises(ValueError, match="no sheet"):
        parse_workbook({}, master, layout)


def test_check_budget_reports_totals_that_do_not_add_up(tmp_path, layout):
    df = parse_sheet(read_sheet(tmp_path, sheet_rows()), layout).with_columns(
        dzs_code=pl.lit("09999")
    )
    check_budget(df)

    broken = df.with_columns(
        amount_eur=pl.when(pl.col("code") == "R1", pl.col("year") == 2025)
        .then(75.0)
        .otherwise(pl.col("amount_eur"))
    )
    with pytest.raises(ValueError, match="cofog_vs_r1: 09999 2025") as error:
        check_budget(broken)
    assert "r1_vs_y034_less_367: 09999 2025" in str(error.value)
