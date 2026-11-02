"""Data spot-check (task G3): 10 figures per pilot, read again from the source files.

Every figure on a pilot's page (web/public/data/m/<slug>.json) is compared with the
raw file it came from (data/raw/), read here with plain openpyxl / fastexcel / json and
none of the pipeline's parsers, so a parsing mistake would show up as a mismatch.

    pipeline/.venv/Scripts/python scripts/spot_check.py > docs/spot-check.md

Exit code 1 if any figure differs.
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

import fastexcel
import openpyxl

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PAGES = ROOT / "web" / "public" / "data" / "m"
CENT = 0.011  # amounts must agree to the cent (float noise allowed)

PILOTS = [
    # slug, MinFin sheet, DZS name, OIB, payments platform
    ("lepoglava", "GRAD LEPOGLAVA", "Lepoglava", "79368224789", "proracunhr"),
    ("marusevec", "OPĆINA MARUŠEVEC", "Maruševec", "26670454549", "kipos"),
    ("sveti-ilija", "OPĆINA SVETI ILIJA", "Sveti Ilija", "10443118219", "kipos"),
    ("jalzabet", "OPĆINA JALŽABET", "Jalžabet", "59790184195", "kipos"),
    ("breznicki-hum", "OPĆINA BREZNIČKI HUM", "Breznički Hum", "35774913576", "ods"),
]
DZS = {
    "lepoglava": "02291",
    "marusevec": "02607",
    "sveti-ilija": "04383",
    "jalzabet": "01651",
    "breznicki-hum": "01511",
}


def eur(value: float | None) -> str:
    if value is None:
        return "–"
    return f"{value:,.2f} €".replace(",", "_").replace(".", ",").replace("_", ".")


# --- Budget: MinFin PR-RAS / RAS-funkcijski workbook -----------------------------------


def budget_rows(sheet: str, year: int) -> tuple[dict, dict, str]:
    """Economic positions and COFOG functions of one unit's sheet, for ``year``."""
    workbook = openpyxl.load_workbook(
        RAW / "minfin_budget" / "county.xlsx", read_only=True, data_only=True
    )
    rows = list(workbook[sheet].iter_rows(values_only=True))
    header = next(i for i, r in enumerate(rows) if "Pozicija u obrascu" in r)
    column = rows[header].index(f"Ostvareno u {year}")
    economic, functions, in_functions = {}, {}, False
    for row in rows[header + 1 :]:
        if str(row[0] or "").startswith("RASHODI PREMA FUNKCIJSKOJ"):
            in_functions = True
            continue
        position = str(row[2]).strip() if row[2] is not None else None
        if position is None:
            continue
        target = functions if in_functions else economic
        target.setdefault(position, row[column] or 0.0)
    return economic, functions, f"county.xlsx › {sheet} › „Ostvareno u {year}”"


def population(name: str, year: int) -> int:
    """DZS Gradovi u statistici, Tab-2: estimate on 31 December of ``year``."""
    workbook = openpyxl.load_workbook(
        RAW / "dzs_estimates" / "estimates.xlsx", read_only=True, data_only=True
    )
    rows = list(workbook["Tab-2."].iter_rows(values_only=True))
    header = next(r for r in rows if f"{year}." in r)
    column = header.index(f"{year}.")
    row = next(r for r in rows if r[0] == "Varaždinska" and r[2] == name)
    return row[column]


# --- Contracts: the file each award came from ------------------------------------------


def find_award(award: dict, oib: str) -> tuple[str, float | None, str]:
    """(source file, value found there, how it was found) for one recent award."""
    system = award["contractId"].split(":")[0]
    if system == "ted":
        for line in (
            (RAW / "contracts_ted" / "notices.jsonl").read_text(encoding="utf-8").splitlines()
        ):
            notice = json.loads(line)
            if award["contractId"].split(":", 2)[2] in (notice.get("contract-identifier") or []):
                value = sum(float(v) for v in notice.get("tender-value") or [])
                dates = notice.get("contract-conclusion-date") or [""]
                ok = (
                    dates[0][:10] == award["signedOn"]
                    and award["supplierOib"] in notice["winner-identifier"]
                )
                return (
                    f"contracts_ted/notices.jsonl › {notice['publication-number']}",
                    value,
                    "date, supplier OIB" + (" agree" if ok else " DIFFER"),
                )
        return "contracts_ted/notices.jsonl", None, "not found"
    if system == "municipal":
        eojn_id = award["contractId"].split("eojn-")[1]
        for path in sorted((RAW / "contracts_municipal" / oib).glob("*.xlsx")):
            workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
            for sheet in workbook.worksheets:
                rows = list(sheet.iter_rows(values_only=True))
                header = next((r for r in rows[:5] if "Ugovor" in r), None)
                if header is None:
                    continue
                col = {name: header.index(name) for name in header if name}
                for row in rows:
                    if str(row[col["Ugovor"]] or "").endswith(f"/contract-eo/{eojn_id}"):
                        net = (
                            row[col.get("Ukupni iznos (sa izmjenama) bez PDV-a")]
                            or row[col["Iznos bez PDV-a"]]
                        )
                        ok = str(row[col["OIB ugovaratelja"]]) == award["supplierOib"]
                        return (
                            f"contracts_municipal/{oib}/{path.name}",
                            float(net),
                            "contract URL, supplier OIB" + (" agree" if ok else " DIFFER"),
                        )
        return f"contracts_municipal/{oib}", None, "not found"
    # Old EOJN register export: supplier name and OIB share a cell, amounts are text.
    path = RAW / "contracts_eojn_legacy" / f"{oib}.xlsx"
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    signed = date.fromisoformat(award["signedOn"])
    for row in workbook["RPT_Ugovor"].iter_rows(values_only=True):
        dates = [c.date() for c in row if isinstance(c, datetime)]
        cells = [str(c) for c in row if c is not None]
        # The signing date is the first date cell; later ones are update timestamps.
        if any(award["supplierOib"] in c for c in cells) and dates[:1] == [signed]:
            amounts = [c for c in cells if c.endswith(" EUR") or c.endswith(" HRK")]
            text = amounts[0]
            value = float(text.split()[0].replace(".", "").replace(",", "."))
            if text.endswith("HRK"):
                value = round(value / 7.53450, 2)
            return (
                f"contracts_eojn_legacy/{oib}.xlsx › RPT_Ugovor",
                value,
                f"supplier OIB, date {signed:%d. %m. %Y.} agree; amount „{text}”",
            )
    return f"contracts_eojn_legacy/{oib}.xlsx", None, "not found"


# --- Payments: raw rows ----------------------------------------------------------------


def payment_rows(slug: str, platform: str) -> list[tuple[str, str, float]]:
    """(YYYY-MM, recipient OIB, amount in EUR) for every published row."""
    folder = RAW / "payments" / DZS[slug]
    out = []
    if platform == "kipos":
        data = json.loads((folder / "payments.json").read_text(encoding="utf-8"))
        for row in data[0]["tableData"]:
            out.append((row["DATUM"][:7], str(row.get("OIB") or ""), float(row["IZNOS"])))
    elif platform == "proracunhr":
        for path in sorted(folder.glob("*.json")):
            for row in json.loads(path.read_text(encoding="utf-8"))["data"]:
                if row["iznos_eur"]:
                    out.append((row["datum"][:7], row["oib"] or "", float(row["iznos_eur"])))
    return out


def ods_month_totals(slug: str) -> tuple[dict[str, tuple[float, str]], dict[str, dict[str, float]]]:
    """Breznički Hum: the "UKUPNO ZA <month>" total each monthly file states itself, and
    per month the amounts by recipient OIB (a continuation row, with no date or
    recipient, belongs to the row above; names are spelt differently month to month)."""
    months = {
        "SIJEČANJ": 1,
        "VELJAČA": 2,
        "OŽUJAK": 3,
        "TRAVANJ": 4,
        "SVIBANJ": 5,
        "LIPANJ": 6,
        "SRPANJ": 7,
        "KOLOVOZ": 8,
        "RUJAN": 9,
        "LISTOPAD": 10,
        "STUDENI": 11,
        "PROSINAC": 12,
    }
    totals, by_recipient = {}, {}
    for path in sorted((RAW / "payments" / DZS[slug]).glob("*.ods")):
        sheet = fastexcel.read_excel(path).load_sheet(0, header_row=None).to_polars()
        recipients: dict[str, float] = {}
        current, started = None, False
        for row in sheet.iter_rows():
            label = str(row[0] or "")
            if label.strip().startswith("Datum"):
                started = True
                continue
            if started and not label.upper().startswith("UKUPNO") and row[5] not in (None, ""):
                if row[2]:
                    current = str(row[3] or " ".join(str(row[2]).split())).strip()
                recipients[current] = recipients.get(current, 0.0) + float(
                    str(row[5]).replace(",", ".")
                )
            if label.upper().startswith("UKUPNO"):
                words = label.upper().replace(".", " ").split()
                month = next((months[w] for w in words if w in months), None)
                year = next((w[:4] for w in words if w[:4].isdigit()), None)
                if month and year:
                    totals[f"{year}-{month:02d}"] = (
                        float(str(row[5]).replace(",", ".")),
                        path.name,
                    )
                    by_recipient[f"{year}-{month:02d}"] = recipients
    return totals, by_recipient


# --- The report ------------------------------------------------------------------------


def check(results, slug, figure, page_value, source_value, where, tolerance=CENT, fmt=eur):
    ok = (
        source_value is not None
        and page_value is not None
        and abs(page_value - source_value) <= tolerance
    )
    results.append((slug, figure, fmt(page_value), fmt(source_value), where, ok))


def main() -> int:
    results = []
    for slug, sheet, dzs_name, oib, platform in PILOTS:
        page = json.loads((PAGES / f"{slug}.json").read_text(encoding="utf-8"))
        budget = page["budget"]
        year = budget["year"]
        economic, functions, where = budget_rows(sheet, year)
        check(
            results,
            slug,
            f"Prihodi {year} (X067)",
            budget["revenueTotalEur"],
            economic["X067"],
            where,
        )
        check(
            results,
            slug,
            f"Rashodi {year} (Y034)",
            budget["expenditureTotalEur"],
            economic["Y034"],
            where,
        )
        top = max(budget["revenueByType"], key=lambda i: i["amountEur"])
        check(
            results,
            slug,
            f"Najveći prihod: {top['code']} {top['label'][:30]}",
            top["amountEur"],
            economic[top["code"]],
            where,
        )
        top = max(budget["expenditureByFunction"], key=lambda i: i["amountEur"])
        check(
            results,
            slug,
            f"Najveća funkcija: {top['code']} {top['label'][:30]}",
            top["amountEur"],
            functions[top["code"]],
            where,
        )

        pop = population(dzs_name, page["population"]["year"])
        check(
            results,
            slug,
            f"Stanovnika {page['population']['year']}.",
            page["population"]["total"],
            pop,
            f"estimates.xlsx › Tab-2. › {dzs_name}",
            tolerance=0,
            fmt=lambda v: "–" if v is None else f"{v:,}".replace(",", "."),
        )
        check(
            results,
            slug,
            "Rashodi po stanovniku",
            budget["expenditurePerResidentEur"],
            round(economic["Y034"] / pop, 2),
            "Y034 / procjena stanovništva",
        )

        award = page["procurement"]["recentAwards"][0]
        file, value, how = find_award(award, oib)
        check(
            results,
            slug,
            f"Zadnji ugovor ({award['signedOn']}, {award['supplierName'][:22]})",
            award["valueEur"],
            value,
            f"{file}; {how}",
        )

        months = [m["month"] for m in page["payments"]["months"]]
        page_months = {m["month"]: m["totalEur"] for m in page["payments"]["months"]}
        last = months[-1]
        if platform == "ods":
            stated, by_recipient = ods_month_totals(slug)
            check(
                results,
                slug,
                f"Isplate {last}",
                page_months[last],
                stated.get(last, (None, ""))[0],
                f"{stated.get(last, (None, '?'))[1]} › „UKUPNO” (zbroj koji objavljuje općina)",
            )
            check(
                results,
                slug,
                f"Isplate, {len(months)} mjeseci",
                sum(page_months.values()),
                sum(stated[m][0] for m in months if m in stated)
                if all(m in stated for m in months)
                else None,
                "zbroj „UKUPNO” redaka mjesečnih datoteka",
            )
            recipient = page["payments"]["topRecipients"][0]
            found = sum(
                by_recipient.get(m, {}).get(recipient["oib"] or recipient["name"], 0.0)
                for m in months
            )
            check(
                results,
                slug,
                f"Najveći primatelj: {recipient['name'][:30]}",
                recipient["amountEur"],
                round(found, 2),
                f"mjesečne .ods datoteke, retci s OIB-om {recipient['oib']} (i retci nastavka)",
            )
        else:
            rows = [r for r in payment_rows(slug, platform) if r[0] in page_months]
            source = f"payments/{DZS[slug]}/" + (
                "payments.json (tableData)" if platform == "kipos" else "<godina>.json (data)"
            )
            check(
                results,
                slug,
                f"Isplate {last}",
                page_months[last],
                round(sum(a for m, _, a in rows if m == last), 2),
                f"{source}, svi retci tog mjeseca",
            )
            check(
                results,
                slug,
                f"Isplate, {len(months)} mjeseci",
                round(sum(page_months.values()), 2),
                round(sum(a for _, _, a in rows), 2),
                f"{source}, svi retci {months[0]} – {last}",
            )
            recipient = page["payments"]["topRecipients"][0]
            check(
                results,
                slug,
                f"Najveći primatelj: {recipient['name'][:30]}",
                recipient["amountEur"],
                round(sum(a for _, o, a in rows if o == recipient["oib"]), 2),
                f"{source}, retci s OIB-om {recipient['oib']}",
            )

    print("| Pilot | Brojka | Na stranici | U izvoru | Izvor | |")
    print("| --- | --- | --- | --- | --- | --- |")
    for slug, figure, shown, source, where, ok in results:
        mark = "✅" if ok else ("ℹ️" if ok is None else "❌")
        print(f"| {slug} | {figure} | {shown} | {source} | {where} | {mark} |")
    failed = [r for r in results if r[5] is False]
    checked = [r for r in results if r[5] is not None]
    print(
        f"\n{len(checked) - len(failed)} od {len(checked)} brojki se slaže s izvorom.",
        file=sys.stderr,
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
