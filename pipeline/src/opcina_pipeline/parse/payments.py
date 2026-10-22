"""Monthly payment disclosures (Naputak, NN 59/23) -> the ``payment`` table.

One parser per publishing platform (``config/payments.toml``), all producing the same
intermediate columns; ``finish`` then applies the rules shared by every platform:

* **Personal data.** A payment to a natural person keeps its amount, date and category
  but never a name or an OIB. ``natural_person_rule`` says which rule caught a row; the
  rules are listed there, in order. Publishers are inconsistent: one marks persons with
  the OIB "GDPR", another prints their name and personal OIB, a third writes "Isplata
  fizičkim osobama". So the publisher's own marking is not trusted alone.
* **Descriptions are not kept** (``description`` is always null). Otvoreni grad's free
  text names people even on payments to companies: employees on payroll rows ("Drugi
  dohodak <name>"), social-welfare beneficiaries whose utility bills the city pays
  ("<SURNAME NAME>, Troškovi vodne usluge"), work-contract holders. Free text cannot be
  scrubbed reliably, so none of it is republished.
* **Amounts** are euro, rounded to cents. Every platform publishes euro (Kipos already
  converts its 2022 kuna rows; checked against fixed fees such as the HRT licence).
* **economic_code** is the 4-digit account (odjeljak) of the published code, so payments
  join to ``budget_line``; ``economic_label`` is the publisher's own label.
* Rows that agree on every output column (one invoice split over budget positions or
  funding sources) are summed into one row.
"""

import json
import re
from collections.abc import Callable
from datetime import date
from pathlib import Path

import fastexcel
import polars as pl

from opcina_pipeline.config import load_sources
from opcina_pipeline.fetch.payments import load_platforms
from opcina_pipeline.tables import PAYMENT, conform, latest_run_id
from opcina_pipeline.text import ascii_fold

# Columns every platform parser returns, before the shared rules are applied.
RAW_COLUMNS = {
    "paid_on": pl.Date,
    "payer_name": pl.Utf8,
    "recipient_name": pl.Utf8,
    "recipient_oib": pl.Utf8,  # as published: "GDPR", blank, 10 digits, "SI123..."
    "economic_code": pl.Utf8,  # as published, any length
    "economic_label": pl.Utf8,
    "function_code": pl.Utf8,
    "description": pl.Utf8,
    "amount_eur": pl.Float64,
}


class ReconciliationError(ValueError):
    """A file's rows do not add up to the total it states."""


# --- OIB --------------------------------------------------------------------------------


def oib_is_valid(oib: str) -> bool:
    """ISO 7064 MOD 11,10 check digit of an 11-digit OIB."""
    if not re.fullmatch(r"\d{11}", oib):
        return False
    remainder = 10
    for digit in oib[:10]:
        remainder = (remainder + int(digit)) % 10 or 10
        remainder = remainder * 2 % 11
    return (11 - remainder) % 10 == int(oib[10])


def clean_oib(raw: str | None) -> str | None:
    """A valid Croatian OIB, or None.

    Spreadsheets drop leading zeros ("2371889218"), so 8-10 digits are padded back.
    Placeholders such as "00000000001" (used for foreign payees) pass the check digit
    but identify nobody, so they are dropped too.
    """
    digits = re.sub(r"\s", "", raw or "")
    if not re.fullmatch(r"\d{8,11}", digits):
        return None
    oib = digits.zfill(11)
    if oib.startswith("000000000") or not oib_is_valid(oib):
        return None
    return oib


# --- Natural persons --------------------------------------------------------------------

# Labels publishers use instead of a person's name (folded to ASCII lower case).
_AGGREGATE_LABEL = re.compile(
    r"fizick\w*\s+osob|\bzaposlen|\bplac[aeu]\b|neto\s+isplat|drugi\s+dohodak|stipendi"
    r"|bozicnic|uskrsnic|putni\s+nalo|gradanima|\bisplata\s+gradan|vijecnic|sjednic"
    r"|samozaloznik|sporedn\w*\s+zanimanj|ugovor\w*\s+o\s+djelu|autorsk\w*\s+ugovor"
)

# Words and abbreviations that mark an organisation or a registered business.
_ORG_WORDS = """
doo dd jdoo kd jtd gmbh ltd limited srl sro sa lda inc llc ag kg spa bv nv plc ab as oy
obrt opg sopg pg vl zadruga pz udruga drustvo klub savez zajednica zaklada fundacija
nk rk kk ok sk dvd vzo kud hgss hpd lag dsr grad opcina zupanija republika drzavni drzavna
proracun ministarstvo uprava ured agencija zavod fond sud mup hzzo hzmo hzz fina hep hrt hak
os ss dv vrtic skola centar institut fakultet sveuciliste knjiznica citaonica muzej
kazaliste galerija ustanova dom bolnica ljekarna ordinacija ambulanta poliklinika stanica
banka bank osiguranje leasing hotel hostel restoran bistro caffe cafe bar pizzeria konoba
apartmani apartman pansion trgovina servis studio media mediji promet prijevoz transport
gradnja biro projekt consulting konzalting savjetovanje commerce trade company group grupa
holding energija plin voda vodovod cistoca tisak naklada radio televizija tv novine vijesti
telekom software sustavi solutions systems tehnika elektro auto optika market shop net web
crkva zupa biskupija samostan taxi aerodrom aeroporto airport odvjetnik odvjetnica javni
biljeznik inzenjer geodet arhitekt sindikat stranka hdz sdp hns hss tours travel farma
hrvatska croatia international usluge usluga vlasnik vlasnica sv sveti sveta svetog
glazba limena bastina
""".split()
_ORG_STEMS = (
    "gradevin komunal odvjetni biljezni poljoprivred trgovin ugostitelj prijevoz autoprijevoz "
    "inzenjer informati dizajn marketing promidzb savjetova konzult consult ordinacij ljekarn "
    "veterinar zdravstv obrazovan ucilist energet kompjut computer turist gospodarstv proizvod "
    "nakladni tiskar"
).split()
_ORG = re.compile(
    r"\bd\.?\s?o\.?\s?o\b|\bd\.\s?d\b|\bs\.\s?[ar]\.|"
    + r"\b(?:"
    + "|".join(_ORG_WORDS)
    + r")\b|\b(?:"
    + "|".join(_ORG_STEMS)
    + r")"
)

# Common Croatian (and neighbouring) first names, folded. A recipient called like a person
# ("HORVAT IVAN", "Ivana Horvat") is treated as one even when an OIB is published.
FIRST_NAMES = frozenset(
    """
    adam adrian adrijan alan albert aleksandar alen alojz alojzije andrej andrija ante anton
    antonio antun armin bartol bartul benjamin berislav bernard blaz bojan boris borna bozidar
    bozo branimir branko bruno ciril cvjetko dalibor damir damjan danijel daniel darijan dario
    darijo darko david davor dejan denis dino dinko domagoj dominik dragan drago dragutin drazen
    dubravko duje dusan edi edo eduard emanuel emil enio erik ernest ervin fabijan filip franc
    frane franjo franko gabrijel goran gordan grga grgur hrvoje igor ilija imbro ivan ivano
    ivica ivo izidor jakov jakob janko josip josko joza jozo juraj jure jurica karlo kazimir
    kresimir kristijan kristian krsto krunoslav ladislav lovro leon leonardo leopold ljubomir
    ljudevit lucijan luka maksimilijan marcel marijan marin mario marjan marko martin mate matej
    mateo matija matko mihael mihajlo mihovil mijo milan milivoj miljenko miro miroslav mirko
    mislav mladen nedjeljko nenad neven nikica nikola niko nino ognjen oliver ozren patrik pavao
    pavle pero petar predrag rade radoslav radovan rajko ranko ratko renato robert roberto roko
    rudi rudolf sanjin sasa sebastijan silvio sime simun sinisa slaven slavko srecko stanko
    stefan stipe stipo stjepan stjepko tihomir tin tomislav tomo toni tvrtko valentin valter
    vedran velimir veljko vid viktor vilim vinko vitomir vjekoslav vladimir vlado vlatko zarko franz
    zdenko zdravko zeljko zlatan zlatko zoran zvonimir zvonko
    agneza ana anamarija anica anita anja anka ankica andrea andreja angela antonela antonija
    barbara barica biljana biserka blanka bozena bozica branka brankica cvijeta danica
    danijela daniela darija darinka davorka dijana diana dolores dora dragana dragica dubravka
    dunja durda durdica ela elena ema emilija ena eva gabrijela gordana hana helena ida ines
    irena iris iva ivana ivanka ivka ivona jadranka jagoda jana janja jasmina jasminka jasna
    jelena jelica josipa julija karla karmen kata katarina katica klara kornelija kristina
    laura lana lara lea leona lidija ljerka ljiljana ljubica lorena lucija magdalena maja manda
    mara marica marija marijana marina marta martina matea mateja melita mia mihaela mila milena
    milka mira mirela mirjana monika nada nadica natalija natasa nevenka nika nikolina nikoleta
    nina nives paula petra rebeka renata rozalija ruza ruzica sabina sandra sanja sara silvija
    sladana slavica smiljana snjezana sonja spomenka stefanija stefica suzana svjetlana tamara
    tanja tatjana tea tena terezija tihana tina valentina valerija vanja vedrana vera verica
    veronika vesna viktorija violeta vlasta zdenka zeljka zora zorica zrinka
    """.split()
)

# Accounts that only ever pay people: salaries and contributions (31xx), fees of the
# council and boards (3291), compensation of non-employees (3241), cash benefits to
# citizens and households (3721). Employees' travel and transport (321x) too, but only
# when the publisher names itself as the recipient: card payments abroad (hotels,
# taxis) under 321x are published without an OIB and are not people.
_PERSONAL_ACCOUNTS = re.compile(r"^(31|3241|3291|3721)")
_SELF_PERSONAL_ACCOUNTS = re.compile(r"^(31|321|3241|3291|3721)")
_PERSONAL_CONTRACT = re.compile(r"ugovor\w* o djelu|autorsk|honorar")


def _words(folded: str) -> list[str]:
    return re.findall(r"[a-z]+", folded)


def looks_like_person(name: str) -> bool:
    """A name shaped like a person's: "HORVAT IVAN", "Ivana Horvat", "I. Horvat"."""
    folded = ascii_fold(name)
    if _ORG.search(folded) or re.search(r"\d", folded):
        return False
    words = _words(folded)
    if 2 <= len(words) <= 4 and any(word in FIRST_NAMES for word in words):
        return True
    return bool(re.fullmatch(r"\s*[a-z]\.\s*[a-z]+(?:[\s-][a-z]+)?\s*", folded))


def natural_person_rule(
    name: str | None,
    raw_oib: str | None,
    economic_code: str | None,
    economic_label: str | None,
    payer_name: str | None = None,
) -> str | None:
    """Why this recipient is treated as a natural person, or None for a legal person.

    Rules, in order:

    1. ``publisher_gdpr``: the publisher withheld the OIB as "GDPR" (Otvoreni grad).
    2. ``aggregate_label``: a label standing for people, e.g. "Fizičke osobe",
       "Isplata zaposleniku", "Plaća za zaposlene", "NETO PLAĆE", "Drugi dohodak",
       "Ugovor o djelu", "Naknada za sjednice", "sporedno zanimanje".
    3. ``self_personal_account``: the payer names itself as the recipient (Kipos does
       this for payments it does not itemise) on a personal account (salaries, staff
       travel, council fees, cash benefits, work contracts).
    4. organisations (legal form, "obrt", "OPG", "vl.", "udruga", "grad", ...) stop here:
       they are legal persons or registered businesses the Naputak requires by name.
    5. ``person_name``: the name is shaped like a person's (a known first name among
       2-4 words, or an initial and a surname), whether or not an OIB is published.

    Rules 6 and 7 apply only when no valid OIB is published:

    6. ``personal_account``: salaries (31xx), non-employee compensation (3241), council
       fees (3291), cash benefits (3721), or a work or author contract in the label.
    7. ``surname_no_oib``: the name is one or two "-ić" surnames ("Horvatić").
    """
    folded = ascii_fold(name or "")
    label = ascii_fold(economic_label or "")
    code = economic_code or ""
    if (raw_oib or "").strip().upper() == "GDPR":
        return "publisher_gdpr"
    if _AGGREGATE_LABEL.search(folded):
        return "aggregate_label"
    if payer_name and " ".join(folded.split()) == " ".join(ascii_fold(payer_name).split()):
        if _SELF_PERSONAL_ACCOUNTS.match(code) or _PERSONAL_CONTRACT.search(label):
            return "self_personal_account"
    if _ORG.search(folded):
        return None
    if looks_like_person(name or ""):
        return "person_name"
    if clean_oib(raw_oib) is not None:
        return None
    if _PERSONAL_ACCOUNTS.match(code) or _PERSONAL_CONTRACT.search(label):
        return "personal_account"
    words = _words(folded)
    if 1 <= len(words) <= 2 and all(word.endswith("ic") for word in words):
        return "surname_no_oib"
    return None


# --- Text helpers -----------------------------------------------------------------------


def _clean(text: str | None) -> str | None:
    text = " ".join((text or "").replace("\xa0", " ").split())
    return text or None


def parse_amount(text: str | None) -> float | None:
    """ "1234.56", "1.234,56", "1234,56", "-12" -> float; blank -> None."""
    value = re.sub(r"[\s\xa0€]|EUR", "", text or "")
    if not value:
        return None
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    return float(value)


def parse_date(text: str | None) -> date | None:
    """ "03.01.2025.", "3.1.2025", "2025-01-03", "2025-01-03T00:00:00.000Z" -> date."""
    value = (text or "").strip()
    if not value:
        return None
    if match := re.match(r"(\d{4})-(\d{2})-(\d{2})", value):
        return date(*map(int, match.groups()))
    if match := re.fullmatch(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})\.?", value):
        day, month, year = map(int, match.groups())
        return date(year, month, day)
    raise ValueError(f"unrecognised date {text!r}")


def split_code(text: str | None) -> tuple[str | None, str | None]:
    """ "3111 Bruto plaće" -> ("3111", "Bruto plaće"); "Bruto plaće" -> (None, ...)."""
    value = _clean(text)
    if value is None:
        return None, None
    match = re.match(r"(\d+)\s*(.*)", value)
    if not match:
        return None, value
    return match.group(1), _clean(match.group(2))


# --- Platform parsers -------------------------------------------------------------------


def parse_otvorenigrad(folder: Path) -> pl.DataFrame:
    """iTransparentnost CSVs, one per month; an empty file is a month with no data."""
    frames = []
    for path in sorted(folder.glob("*.csv")):
        if not path.stat().st_size:
            continue
        raw = pl.read_csv(path, separator=";", infer_schema=False, encoding="utf8")
        if raw.is_empty():
            continue
        currencies = set(raw["Valuta"].drop_nulls().str.strip_chars()) - {"EUR"}
        if currencies:
            raise ValueError(f"{path.name}: unexpected currencies {sorted(currencies)}")
        rows = []
        for row in raw.iter_rows(named=True):
            # Payments booked against a liability account with no budget position
            # (e.g. 2317 obligations to employees) are listed without an amount.
            if parse_amount(row["Iznos na poziciji"]) is None:
                continue
            economic_code, economic_label = split_code(row["Ekonomska klasifikacija"])
            function_code, _ = split_code(row["Funkcijska klasifikacija"])
            rows.append(
                {
                    "paid_on": parse_date(row["Datum"]),
                    # A budget user (kindergarten, library) pays from the city's account.
                    "payer_name": _clean(row["Proračunski korisnik"])
                    or _clean(row["Naziv isplatitelja"]),
                    "recipient_name": _clean(row["Primatelj"]),
                    "recipient_oib": _clean(row["OIB"]),
                    "economic_code": economic_code,
                    "economic_label": economic_label,
                    "function_code": function_code,
                    "description": None,  # "Opis" names people; see the module docstring
                    "amount_eur": parse_amount(row["Iznos na poziciji"]),
                }
            )
        frames.append(pl.DataFrame(rows, schema=RAW_COLUMNS))
    return pl.concat(frames) if frames else pl.DataFrame(schema=RAW_COLUMNS)


def _kipos_rows(data) -> list[dict]:
    """The search answers ``[{"tableData": [...], "graphData": ...}]``; older dumps a list."""
    if isinstance(data, dict):
        data = [data]
    rows = []
    for item in data:
        if isinstance(item, dict) and "tableData" in item:
            rows.extend(item["tableData"])
        else:
            rows.append(item)
    return rows


def parse_kipos(folder: Path) -> pl.DataFrame:
    """Kipos ``payments.json``: every payment since the portal started. No COFOG."""
    path = folder / "payments.json"
    rows = []
    for row in _kipos_rows(json.loads(path.read_text(encoding="utf-8"))):
        rows.append(
            {
                "paid_on": parse_date(row["DATUM"]),
                "payer_name": _clean(row.get("ISPLATITELJ")),
                "recipient_name": _clean(row.get("NAZIV")),
                "recipient_oib": _clean(str(row.get("OIB") or "")),
                "economic_code": _clean(str(row.get("IDKONTO") or "")),
                "economic_label": _clean(row.get("IDKONTO_NAZIV")),
                "function_code": None,
                "description": None,
                "amount_eur": parse_amount(str(row["IZNOS"])),
            }
        )
    return pl.DataFrame(rows, schema=RAW_COLUMNS)


def _is_total_row(first_cell: str | None) -> bool:
    return ascii_fold(first_cell or "").startswith("ukupno")


# Croatian month names in any case form, by folded prefix ("siječanj", "veljače", ...).
_MONTH_PREFIXES = {
    "sijec": 1, "velj": 2, "ozuj": 3, "trav": 4, "svib": 5, "lip": 6,
    "srp": 7, "kolov": 8, "ruj": 9, "listop": 10, "stud": 11, "prosin": 12,
}  # fmt: skip


def stated_period(text: str | None) -> tuple[int, int] | None:
    """ "INFORMACIJE ... ZA SIJEČANJ 2025. GODINE", "UKUPNO ZA VELJAČU 2026." -> (y, m)."""
    match = re.search(r"\bza\s+([a-z]+)\s+(\d{4})", ascii_fold(text or ""))
    if not match:
        return None
    for prefix, month in _MONTH_PREFIXES.items():
        if match.group(1).startswith(prefix):
            return int(match.group(2)), month
    return None


def parse_ods_file(path: Path) -> tuple[pl.DataFrame, tuple[int, int] | None]:
    """One Breznički Hum monthly ODS -> (payments, (year, month) the file states).

    Layout: a few lines of unit details, a title ("... ZA SIJEČANJ 2025."), then the
    header row starting "Datum". A row with a blank date continues the payment above it
    (another account). The last row is "UKUPNO ZA <month>", whose amount must equal the
    sum of the rows to the cent, else ReconciliationError.

    A date in the file's month but an earlier year ("27.02.2025." in the February 2026
    file) is a typo for the file's year and is corrected.
    """
    sheet = fastexcel.read_excel(str(path)).load_sheet(0, header_row=None, dtypes="string")
    cells = sheet.to_polars()
    if cells.width < 7:
        raise ValueError(f"{path.name}: expected 7 columns, found {cells.width}")
    lines = [[_clean(cell) for cell in row[:7]] for row in cells.iter_rows()]
    header = next((i for i, row in enumerate(lines) if ascii_fold(row[0] or "") == "datum"), None)
    if header is None:
        raise ValueError(f"{path.name}: no header row starting with 'Datum'")
    period = next(filter(None, (stated_period(row[0]) for row in lines[:header])), None)

    rows, total, current = [], None, None
    for line in lines[header + 1 :]:
        day, payer, recipient, oib, _seat, amount_text, account = line
        if _is_total_row(day):
            total = parse_amount(amount_text)
            period = period or stated_period(day)
            break
        if not any((day, payer, recipient, oib, amount_text, account)):
            continue
        amount = parse_amount(amount_text)
        if amount is None:
            raise ValueError(f"{path.name}: row without an amount: {line}")
        if day:
            paid_on = parse_date(day)
            if period and paid_on.month == period[1] and paid_on.year < period[0]:
                paid_on = paid_on.replace(year=period[0])
            current = {
                "paid_on": paid_on,
                "payer_name": payer,
                "recipient_name": recipient,
                "recipient_oib": oib,
            }
        elif current is None:
            raise ValueError(f"{path.name}: continuation row before any payment: {line}")
        economic_code, economic_label = split_code(account)
        rows.append(
            {
                **current,
                "economic_code": economic_code,
                "economic_label": economic_label,
                "function_code": None,
                "description": None,
                "amount_eur": amount,
            }
        )
    if total is None:
        raise ReconciliationError(f"{path.name}: no UKUPNO row")
    parsed = round(sum(round(row["amount_eur"], 2) for row in rows), 2)
    if abs(parsed - round(total, 2)) >= 0.005:
        raise ReconciliationError(
            f"{path.name}: rows add up to {parsed:.2f}, UKUPNO says {total:.2f}"
        )
    return pl.DataFrame(rows, schema=RAW_COLUMNS), period


def parse_html_links(folder: Path) -> pl.DataFrame:
    """Monthly ODS files linked from the municipality's page (Breznički Hum).

    File names vary ("..._01-25.ods", "..._Ozujak_2024ods.ods", "isplate-..._1ods.ods"),
    so the month comes from inside the file; two files for one month are refused.
    """
    frames, seen = [], {}
    for path in sorted(folder.glob("*.ods")):
        frame, period = parse_ods_file(path)
        if period is not None and period in seen:
            raise ValueError(f"{path.name} and {seen[period]} both cover {period}")
        seen[period] = path.name
        frames.append(frame)
    return pl.concat(frames) if frames else pl.DataFrame(schema=RAW_COLUMNS)


PARSERS: dict[str, Callable[[Path], pl.DataFrame]] = {
    "otvorenigrad": parse_otvorenigrad,
    "kipos": parse_kipos,
    "html_links": parse_html_links,
}


# --- Shared rules -----------------------------------------------------------------------


def finish(raw: pl.DataFrame, dzs_code: str, source_run_id: str) -> pl.DataFrame:
    """Apply the personal-data rules, normalise codes and amounts, sum identical rows.

    Keeps a ``natural_person_rule`` column (dropped by ``conform``) for reporting.
    """
    records = []
    for row in raw.iter_rows(named=True):
        if row["paid_on"] is None or row["amount_eur"] is None:
            raise ValueError(f"{dzs_code}: payment without date or amount: {row}")
        account = row["economic_code"]
        rule = natural_person_rule(
            row["recipient_name"],
            row["recipient_oib"],
            account,
            row["economic_label"],
            row["payer_name"],
        )
        natural = rule is not None
        records.append(
            {
                "dzs_code": dzs_code,
                "paid_on": row["paid_on"],
                "month": row["paid_on"].strftime("%Y-%m"),
                "payer_name": row["payer_name"],
                "recipient_name": None if natural else row["recipient_name"],
                "recipient_oib": None if natural else clean_oib(row["recipient_oib"]),
                "natural_person": natural,
                "natural_person_rule": rule,
                "economic_code": account[:4] if account else None,
                "economic_label": row["economic_label"],
                "function_code": row["function_code"],
                "description": None if natural else row["description"],
                "amount_eur": round(row["amount_eur"], 2),
                "source_run_id": source_run_id,
            }
        )
    schema = {**PAYMENT, "natural_person_rule": pl.Utf8}
    df = pl.DataFrame(records, schema=schema)
    keys = [name for name in schema if name != "amount_eur"]
    return (
        df.group_by(keys, maintain_order=True)
        .agg(pl.col("amount_eur").sum().round(2))
        .select(list(schema))
        .sort("paid_on", maintain_order=True)
    )


def parse_unit(dzs_code: str, entry: dict, folder: Path, source_run_id: str) -> pl.DataFrame:
    """All payments of one municipality, with the ``natural_person_rule`` column."""
    platform = entry["platform"]
    if platform not in PARSERS:
        raise ValueError(f"{dzs_code}: no parser for platform {platform!r}")
    return finish(PARSERS[platform](folder), dzs_code, source_run_id)


def build_payments(
    raw_dir: Path | None = None, platforms: dict[str, dict] | None = None
) -> pl.DataFrame:
    """Every configured municipality with files on disk, conformed to ``payment``."""
    raw_dir = raw_dir or load_sources()["payments"].path
    platforms = platforms if platforms is not None else load_platforms()
    run_id = latest_run_id("payments")
    frames = []
    for code, entry in sorted(platforms.items()):
        folder = raw_dir / code
        if entry["platform"] == "unavailable" or not folder.is_dir():
            continue
        frames.append(parse_unit(code, entry, folder, run_id))
    if not frames:
        raise LookupError(f"no payment files under {raw_dir}")
    return conform(pl.concat(frames), "payment")
