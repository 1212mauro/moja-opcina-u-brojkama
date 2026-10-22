from datetime import UTC, date, datetime

import polars as pl

from opcina_pipeline.export import clean_label, payments_section
from opcina_pipeline.tables import conform


def payment(month: str, amount: float, name: str | None = "Tvrtka d.o.o.") -> dict:
    year, mon = map(int, month.split("-"))
    return {
        "dzs_code": "02445",
        "paid_on": date(year, mon, 10),
        "month": month,
        "payer_name": "Grad",
        "recipient_name": name,
        "recipient_oib": None,
        "natural_person": name is None,
        "economic_code": "3232",
        "economic_label": "Usluge tekućeg održavanja",
        "function_code": None,
        "description": None,
        "amount_eur": amount,
        "source_run_id": "payments-1",
    }


def test_payment_window_is_twelve_calendar_months_without_the_current_one():
    rows = [payment(f"2025-{m:02d}", 100) for m in range(1, 13)]
    rows += [payment(f"2026-{m:02d}", 100) for m in (1, 2, 4)]  # March 2026 never published
    rows += [payment("2026-05", 5)]  # month in progress at export time
    section = payments_section(
        conform(pl.DataFrame(rows), "payment"), datetime(2026, 5, 9, tzinfo=UTC)
    )

    months = [m.month for m in section.months]
    assert months[0] == "2025-05" and months[-1] == "2026-04"
    assert "2026-03" not in months and "2026-05" not in months
    assert len(months) == 11


def test_natural_persons_never_appear_among_top_recipients():
    rows = [payment("2026-01", 1_000_000, name=None), payment("2026-01", 10)]
    section = payments_section(
        conform(pl.DataFrame(rows), "payment"), datetime(2026, 3, 1, tzinfo=UTC)
    )
    assert [r.name for r in section.top_recipients] == ["Tvrtka d.o.o."]


def test_clean_label_drops_form_notes():
    assert clean_label("Prihodi od poreza (šifre 611+612+613)") == "Prihodi od poreza"
    assert clean_label("Opće javne usluge (šifre 011+012+013+014 do 018)") == "Opće javne usluge"
    assert clean_label("Rashodi za zaposlene") == "Rashodi za zaposlene"
