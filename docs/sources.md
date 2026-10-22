# Data sources (task B10)

Every source the pipeline reads, how it was obtained, and what to watch out for. Machine-readable entries (URL, licence, local file) are in `pipeline/config/sources.toml`. Raw files go to `data/raw/<source>/` and are not committed. All sources were fetched on **22 October 2026** for Varaždin County.

## Budget execution

| | |
| --- | --- |
| Publisher | Ministarstvo financija |
| Page | [PR-RAS i RAS-funkc. za razdoblje 2019–2025, EURO](https://mfin.gov.hr/istaknute-teme/lokalna-samouprava/financijski-izvjestaji-jlp-r-s/pr-ras-i-ras-funkc-za-razdoblje-2019-2025-euro/3922) |
| File | `Lokalci FINALI 2019 2024 EURO.zip` (80 MB; the name says 2024 but it holds 2019–2025) → one xlsx per county; ours is `05 Varaždinska.xlsx` |
| Licence | Not stated (mfin.gov.hr terms page is empty) |
| Refresh | Yearly (this file: 24 July 2026). No half-year file on this page. |

Layout: one sheet per unit, named like the RKP register (`GRAD VARAŽDIN`, `OPĆINA BREZNIČKI HUM`), plus 5 aggregate sheets (`UKUPNO GRADOVI ` has a trailing space). Every sheet is 1157 × 16: metadata in rows 1–6 (`Razina: 22`, `Valuta: Euro`), header in row 7, data from row 10. Columns: `Račun iz rač. plana | Opis stavke | Pozicija u obrascu | Ostvareno u 2019 | … | Ostvareno u 2025` with `Indeks` columns in between.

Quirks:

- **No OIB or RKP in the file**; a unit is identified only by its sheet name.
- Rows 10–1018: economic classification (accounts 6, 61, 611…) mixed with derived codes: `X067` total revenue, `Y034` total expenditure, `Z006`–`Z009` employee counts, `11K` cash at period end. Key rows by `Pozicija u obrascu`, which is unique per sheet.
- Rows 1020–1157: COFOG functions at 2, 3 and 4 digits (`01`, `011`, `0111`, strings with leading zeros); `R1` = sum of 01–10.
- **COFOG total ≠ total expenditure**: `R1 = Y034 − account 367` (transfers to the unit's own budget users). Varaždin 2025: 79,710,828 − 21,110,045 = 58,600,783.
- All years, 2019–2022 included, are already in EUR. No kuna conversion is needed for this file (a separate HRK file covers 2002–2022).
- Account codes have mixed types (`' '`, `'9221x, 9222x'`, `96.97`): read column A as text. `Indeks` cells are Excel formulas: skip them. Column H header is mislabelled.
- Level 22 only: budget users (kindergartens, libraries) are not consolidated into their city.

Pilot totals 2025 (EUR): Varaždin revenue 73.71M / expenditure 79.71M; Ivanec 12.06M / 13.86M; Ludbreg 8.88M / 10.04M; Jalžabet 3.77M / 5.56M; Breznički Hum 0.995M / 1.189M.

## Budget users register (RKP)

| | |
| --- | --- |
| Publisher | Ministarstvo financija |
| Page | [RKPFI portal](https://rkpfi.drzavna-riznica.hr/PORTAL/Rkp); also on data.gov.hr as `registar-proracunskih-i-izvanproracunskih-korisnika` (4 static XLSX tables) |
| Access | `POST /PORTAL/Rkp/Export` with `__RequestVerificationToken` (from a GET of the page, with its cookie), `Year`, `Active=Active\|Inactive\|All` |
| Licence | Otvorena dozvola Republike Hrvatske |

Sheet `RKP registar`: `RKP broj | Naziv subjekta | Osobni identifikacijski broj | Matični broj | … | Statistička oznaka županije | Statistička oznaka grada/općine | Razina financijskog izvještavanja | … | RKP broj nadležne JLP(R)S | Nadležni proračun JLP(R)S`.

- Levels: 22 = a local unit's own budget, 21 = its budget users, 31 = decentralised-function users (schools, fire brigades).
- `RKP broj` comes as a number: pad to 5 digits. Four Varaždin County OIBs start with 0: keep OIBs as text.
- **`Statistička oznaka grada/općine` is the DZS code without its check digit** (`472 - VARAŽDIN` ↔ `04723`). `opcina master` joins on this.
- Budget users per pilot: Varaždin 19, Ivanec 3, Ludbreg 4, Jalžabet 1, Breznički Hum 0. These link procurement by institutions to their city (SPEC matching rule 1).

## Population

| | |
| --- | --- |
| Publisher | Državni zavod za statistiku (DZS) |
| Files | [Census 2021 by grad/općina](https://podaci.dzs.hr/media/td3jvrbu/popis_2021-stanovnistvo_po_gradovima_opcinama.xlsx), [by settlement](https://podaci.dzs.hr/media/rqybclnx/popis_2021-stanovnistvo_po_naseljima.xlsx), [estimates 2011–2025](https://podaci.dzs.hr/media/bz5hplcj/gradovi-u-statistici.xlsx) |
| Licence | Free reuse with attribution to DZS |

- Census by grad/općina, sheet `20.`: header on row 8; filter `Tip naselja == "Ukupno"` and `Spol == "sv."`; 5-year age bands. Already at municipality level, no roll-up needed.
- By settlement, sheet `1.`: same layout plus `Naselje`; municipality subtotal rows have an empty settlement. Headers contain line breaks and trailing spaces, so read columns by position.
- Estimates, sheet `Tab-2.`: header row 8; 31 Dec estimates for 2011–2025 (2012–2020 revised). DZS writes `-` for zero.
- Varaždin County: 159,487 (census 2021), 158,080 (estimate 2025).

## Codes (DZS / LAU)

| | |
| --- | --- |
| Publisher | Eurostat |
| File | [EU-27-LAU-2025-NUTS-2024.xlsx](https://ec.europa.eu/eurostat/web/nuts/local-administrative-units), sheet `HR` |
| Licence | © European Union, reuse with attribution |

- `LAU CODE` is the 5-digit DZS spatial-unit code (`04723`); `EU LAU CODE` is `HR_` + that code. The DZS code and LAU code are the same identifier.
- Varaždin County is `NUTS3 == "HR062"`: exactly 28 units.
- Do not take population from `EU-27-LAU-2021-Census-NUTS-2021.xlsx`: its HR column holds 2011 figures.
- DZS PxWeb still names 00850 "Donji Martijanec"; Eurostat and the census say "Martijanec".

## Postcodes

| | |
| --- | --- |
| Publisher | Hrvatska pošta d.d. |
| File | [mjestaRh.aspx](https://www.posta.hr/mjestaRh.aspx) (xlsx; `?vrsta=xml` for XML); on data.gov.hr as `naselje-i-odredisni-postanski-ured` |
| Licence | Not stated |

Columns `BrojPu | NazivPu | Naselje | Zupanija`: settlement → postcode, no municipality. `opcina postcodes` matches settlements to the census settlement list by name; three ambiguous names are resolved in `pipeline/config/postcode_overrides.csv`. Nine postcodes are shared by two or three municipalities (e.g. 42204: Gornji Kneginec, Jalžabet, Sveti Ilija), so a postcode search can return several results.

## Boundaries

| | |
| --- | --- |
| Publisher | Državna geodetska uprava (DGU) |
| Access | WFS is disabled (`geoportal.dgu.hr/services/inspire/au/wfs` → "Service WFS is disabled"). Download via the ATOM feed `https://geoportal.dgu.hr/services/atom/au/xml` → `INSPIRE_Administrative_Units_(AU).zip` |
| Licence | Otvorena dozvola |
| Refresh | Weekly (file dated 18 Oct 2026) |

The zip is 209 MB with one 601 MB GML in **EPSG:3035** covering all 50,192 units at every level. Filtered to Varaždin County: 28 municipalities (820 KB GeoJSON, 1,000–3,000 vertices each) and 303 settlements. Properties: `name` (no Grad/Općina prefix), `national_code` (= DZS code), `local_id`, `level`, `upper_name`. No OIB.

**Still to do:** the current GeoJSON was reprojected with a hand-written formula in a scratch script. Replace it with pipeline code using pyproj and simplify the polygons for the browser (task B6 / C11).

## Facilities

| Dataset | Publisher | Licence | Coordinates | Notes |
| --- | --- | --- | --- | --- |
| `osnovne-skole`, `srednje-skole`, `djecji-vrtici` on data.gov.hr (from e-Matica) | Ministarstvo znanosti, obrazovanja i mladih | Otvorena dozvola | No: address + `Mjesto` | National lists (926 / 443 / 885). County key is spelled differently in each file (`Župnija`, `Županija`, `Zupanija ` with trailing space). `Šifra` = e-Matica code. |
| Dječji vrtići Grada Varaždina | Grad Varaždin | Otvorena dozvola | No | `;`-separated, UTF-8 BOM, line breaks inside fields. **Contains names of responsible persons: drop those columns.** |
| Adresar ustanova u zdravstvu Varaždinske županije 2026 | Varaždinska županija | Otvorena dozvola | No | Only 6 county-level institutions; cp1250 encoding |
| OpenStreetMap via Overpass | OSM contributors | ODbL (attribution required) | Yes | `amenity`/`healthcare` = school, kindergarten, clinic, doctors, hospital, pharmacy, dentist; 162 elements in the county. Schools carry `ref:HR:e-matica`, a join key to the ministry lists. overpass-api.de returned 502; kumi.systems worked (data as of 15 Jul 2026). |

The HZZO practice-locations file (`hzzo-net.hr/hackathon/…`) did not respond.

| Pilot | Primary | Secondary | Kindergartens | OSM health points |
| --- | --- | --- | --- | --- |
| Varaždin | 9 | 11 | 14 | 17 |
| Ivanec | 2 | 2 | 1 | 4 |
| Ludbreg | 1 | 1 | 5 | 3 |
| Jalžabet | 1 | 0 | 1 | 0 |
| Breznički Hum | 1 | 0 | 0 | 0 |

## Monthly payments

None of the pilots mirrors its payments on data.gov.hr, and none of the portals states a licence.

| Pilot | Where | Format | Downloaded |
| --- | --- | --- | --- |
| Ludbreg | Otvoreni grad iTransparentnost | API: `GET https://api.otvorenigrad.hr/itransparentnost/isplate?lang=hr&format=csv&filters={"datum":{"values":["2025-10-01","2025-11-01"],"op":"BETWEEN"}}`, header `LC-Tenant: grad-ludbreg` (upper bound exclusive) | Oct 2025 – Sep 2026, 12 files |
| Ivanec | Same platform, `LC-Tenant: grad-ivanec` | CSV | Oct 2025 – Sep 2026, 12 files |
| Jalžabet | Kipos, `transparentnost-jalzabet.kipos.hr` | JSON from `dbapi.php?radim=search…`; the date filter is ignored, all years returned | 2022-01 – 2026-09, 7,676 rows |
| Breznički Hum | Monthly ODS files under `/images/isplate_iz_proracuna/<year>/` | ODS | May 2025 – Apr 2026 (publishing lags ~6 months) |
| Varaždin | `transparentni.varazdin.hr` (Infomare) | Search form behind reCAPTCHA v3 | **Not downloaded.** Ask the city for an export. |

Layouts:

- **Otvoreni grad (Ludbreg, Ivanec):** `Naziv isplatitelja;Datum;Primatelj;OIB;Mjesto;Proračunski korisnik;Valuta;Iznos na poziciji;Pozicija;Organizacijska klasifikacija;Programska klasifikacija;Izvor financiranja;Ekonomska klasifikacija;Funkcijska klasifikacija;Broj računa;Opis;…`. One row per budget position, so one payment can span several rows. Natural persons appear as `Fizičke osobe` with OIB `GDPR`. Classifications are "code name" in one string; the functional one is COFOG.
- **Kipos (Jalžabet):** `DATUM, GODINA, ISPLATITELJ, NAZIV, OIB, OPCINA, IZNOS (text), IDKONTO, IDKONTO_NAZIV, PROGRAM_ID, PROGRAM_NAZIV`. No COFOG, no description.
- **Breznički Hum ODS:** 6 header lines; `Datum | Naziv isplatitelja | Naziv primatelja | OIB primatelja | Sjedište primatelja | Način objave isplaćenog iznosa` (actually the amount) `| Vrsta rashoda i izdataka`. Continuation rows have a blank date and recipient; the last row is `UKUPNO`; amounts carry float noise.

**Security note:** Jalžabet's `dbapi.php` accepts a raw SQL fragment in a `filter` parameter. The pipeline must not use it. Consider reporting it to the municipality.

## Procurement

**Correction to SPEC.md:** the data.gov.hr dataset the spec cites as the national "contract register 2018–2023" (`247c96e7-…`) is **Grad Ivanec's own register**, published by Ivanec under Otvorena dozvola. No national EOJN dataset exists on data.gov.hr.

| Pilot | 2018–2023 | 2024 onwards |
| --- | --- | --- |
| Ivanec | data.gov.hr: `registar-ugovora-o-javnoj-nabavi-i-os-2018-2023.xlsx` (573 contracts) | data.gov.hr: `…-od-2024.g.-nadalje.xlsx` (241 contracts) |
| Varaždin, Ludbreg, Jalžabet, Breznički Hum | Old EOJN report form (`eojn.nn.hr` RptRegistarUgovora, one buyer at a time); not fetched | New EOJN `eojn.hr/contracts`; not fetched (see below) |

**Old system (Ivanec 2018–2023 file):** sheet `RPT_Ugovor`, merged cells, header on row 14 from column B: `Evidencijski broj nabave | Predmet nabave | CPV | Broj objave iz EOJN RH | Vrsta postupka | Naziv i OIB ugovaratelja | … | Datum sklapanja | Oznaka/broj ugovora | … | Iznos bez PDV-a | Iznos PDV-a | Ukupni iznos s PDV-om | …`.

- The buyer is only in the file title.
- Supplier name and OIB share one cell.
- Amounts are text like `25.000,00 HRK`. **The currency follows the record's last update, not the signing date** (28 contracts from 2022 are in EUR), so parse the suffix on every cell.
- 5 exact duplicate rows; one obvious VAT typo (row 38).

**New system (2024+ file):** sheet `Analytics`, header row 1, 34 columns.

- Buyer name and OIB, supplier name and OIB in separate columns; amounts are numeric EUR.
- Contract URL `https://eojn.hr/contract-eo/{id}` is a unique key.
- Includes amendment columns and `Status ugovora`.
- 216 of 241 rows are purchases exempt from the procurement law.
- One supplier OIB reads `KRIVO_SE_REGISTRIRALI_87607151174`.

**Access to eojn.hr for the other pilots:**

- The public grid's JSON endpoint needs an anonymous token scraped from the page.
- The official API (`/api/public/…`) needs an `X-API-Key`.
- `robots.txt` is `Disallow: /`, and about 45 quick requests trigger a temporary block.
- The pipeline should **not** scrape it. Options: request an API key from eojn@nn.hr, or export each pilot's contracts by hand from the public grid for the MVP.

Pilot buyer OIBs: Varaždin 13269011531, Ivanec 84121580205, Ludbreg 84947290034, Jalžabet 59790184195, Breznički Hum 35774913576. Pilot institutions seen as buyers: Dječji vrtić Ivančice Ivanec (37103102119), Dječji vrtić Radost Ludbreg (63026242663), Knjižnica i čitaonica "Mladen Kerstner" Ludbreg (52291394442). VARKOM d.o.o. (39048902955) serves several municipalities and cannot be attributed to one.
