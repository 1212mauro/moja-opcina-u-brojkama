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


def contract(subject: str, value: float | None, signed_on: date | None) -> dict:
    return {
        "contract_key": f"eojn_legacy:{subject}",
        "system": "eojn_legacy",
        "dzs_code": "02607",
        "buyer_oib": "1",
        "buyer_name": "Općina",
        "buyer_kind": "unit",
        "subject": subject,
        "cpv": None,
        "procedure": None,
        "contract_number": None,
        "supplier_name": "Gradnja d.o.o.",
        "supplier_oib": "2",
        "signed_on": signed_on,
        "value_eur": value,
        "value_with_vat_eur": None,
        "value_original": None,
        "currency_original": "EUR",
        "source_run_id": "c-1",
    }


def test_annexes_change_totals_but_are_not_counted_as_awards():
    from opcina_pipeline.export import procurement_section

    rows = [
        contract("Rekonstrukcija doma", 100_000, date(2022, 3, 1)),
        contract("Rekonstrukcija doma – 1. dodatak ugovoru", -11.67, date(2022, 11, 29)),
        contract("Dodatni radovi na domu", 5_000, date(2022, 12, 1)),
    ]
    section = procurement_section(conform(pl.DataFrame(rows), "contract"))
    assert section.contract_count == 2
    assert section.total_value_eur == 104_988.33
    assert [a.subject for a in section.recent_awards] == [
        "Dodatni radovi na domu",
        "Rekonstrukcija doma",
    ]
    assert section.top_suppliers[0].contracts == 2


def test_procurement_without_any_signing_date_still_exports():
    from opcina_pipeline.export import procurement_section

    section = procurement_section(
        conform(pl.DataFrame([contract("Nabava", None, None)]), "contract")
    )
    assert section.data_from is None and section.contract_count == 1
    assert section.recent_awards == []


def test_old_runs_of_a_renamed_source_still_resolve():
    from opcina_pipeline.export import source_config

    assert source_config("contracts_ivanec").key == "contracts_municipal"


def test_no_category_chart_when_the_publisher_labels_nothing():
    unlabelled = [{**payment("2026-01", 10), "economic_label": None, "economic_code": None}]
    section = payments_section(
        conform(pl.DataFrame(unlabelled), "payment"), datetime(2026, 3, 1, tzinfo=UTC)
    )
    assert section.by_category == []
    # A few unlabelled rows among labelled ones still show, as "Ostalo".
    mixed = unlabelled + [payment("2026-01", 20)]
    section = payments_section(
        conform(pl.DataFrame(mixed), "payment"), datetime(2026, 3, 1, tzinfo=UTC)
    )
    assert [c.label for c in section.by_category] == ["Usluge tekućeg održavanja", "Ostalo"]


def test_the_unit_paying_itself_is_not_a_recipient():
    # Kipos lists what it does not itemise under the municipality's own name and OIB.
    own = {**payment("2026-01", 1_000_000, name="OPĆINA PRIMJER"), "recipient_oib": "11111111119"}
    rows = [own, payment("2026-01", 10)]
    section = payments_section(
        conform(pl.DataFrame(rows), "payment"), datetime(2026, 3, 1, tzinfo=UTC), "11111111119"
    )
    assert [r.name for r in section.top_recipients] == ["Tvrtka d.o.o."]
    assert section.months[0].total_eur == 1_000_010  # still money paid out
