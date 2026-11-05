# Data sources (task B10)

Every source the pipeline reads, how it is fetched, and what to watch out for. Machine-readable entries (URL, licence, fetch options) are in `pipeline/config/sources.toml`. Raw files go to `data/raw/<source>/` and are not committed. Layouts below were checked on **22 October 2026** for Varaždin County.

## How fetching works

Every source is fetched automatically; there are no manual steps.

- `opcina fetch` downloads all sources (`opcina fetch <key> …` for some). Each fetcher lives in `pipeline/src/opcina_pipeline/fetch/`.
- Where a publisher puts the year in file names (MinFin, Eurostat, DGU), the fetcher follows links from a stable page instead of storing a dated URL, so new yearly files are picked up without config edits.
- Downloads are polite: a project User-Agent, a pause between requests to the same host (6 s for eojn.hr, 3 s for eojn.nn.hr), retries with backoff on 429/5xx, and ETag/Last-Modified so unchanged files are not downloaded again.
- A file is "changed" only if its data changed: xlsx packaging parts (creation times, relationship ids) and per-source volatile parts (`ignore_parts`) are ignored.
- A failed download never replaces the last good file.
- Every run appends one line per source to `data/raw/source_runs.jsonl`: status (`ok`, `unchanged`, `skipped`, `unavailable`, `failed`), file hashes and a note. This is the provenance every figure links back to.
- `.github/workflows/fetch.yml` runs this nightly at 03:30 UTC, keeps `data/raw/` in the Actions cache between runs, shows a status table on the run page and fails (emailing the maintainer) when a source fails.
- Credentials come only from environment variables / repository secrets: `EOJN_API_KEY` for the new EOJN API.

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

The fetcher streams the GML out of the zip (no 600 MB file on disk), keeps the 2nd-order unit whose national code is the MinFin county number (`05`) and the 3rd-order units pointing to it, and reprojects with pyproj (`posList` is northing, easting). Output: `dgu_boundaries/municipalities.geojson`, full resolution, WGS84.

`opcina boundaries` simplifies them for the browser with `shapely.coverage_simplify` (tolerance 0.0004°, about 40 m), which simplifies each shared border once so neighbours never overlap or gap: 34k → 7.3k vertices, 146 KB, written to `web/public/data/boundaries.geojson` in the contract's `Boundaries` shape.

## Facilities

| Dataset | Publisher | Licence | Coordinates | Notes |
| --- | --- | --- | --- | --- |
| `osnovne-skole`, `srednje-skole`, `djecji-vrtici` on data.gov.hr (from e-Matica) | Ministarstvo znanosti, obrazovanja i mladih | Otvorena dozvola | No: address + `Mjesto` | National lists (926 / 443 / 885). County key is spelled differently in each file (`Župnija`, `Županija`, `Zupanija ` with trailing space). `Šifra` = e-Matica code. |
| Dječji vrtići Grada Varaždina | Grad Varaždin | Otvorena dozvola | No | `;`-separated, UTF-8 BOM, line breaks inside fields. **Contains names of responsible persons: drop those columns.** |
| Adresar ustanova u zdravstvu Varaždinske županije 2026 | Varaždinska županija | Otvorena dozvola | No | Only 6 county-level institutions; cp1250 encoding |
| OpenStreetMap via Overpass | OSM contributors | ODbL (attribution required) | Yes | `amenity`/`healthcare` = school, kindergarten, clinic, doctors, hospital, pharmacy, dentist; 163 elements in the county (22 Oct 2026). The fetcher selects the county by `ISO3166-2=HR-05` (same numbering as MinFin) and tries several Overpass instances in turn. Schools carry `ref:HR:e-matica`, a join key to the ministry lists. |

The HZZO practice-locations file (`hzzo-net.hr/hackathon/…`) did not respond. The ministry registries are fetched as national JSON from data.gov.hr (`schools_primary`, `schools_secondary`, `kindergartens`), so they scale to every county; the two city/county-specific lists above are not fetched (OSM covers health facilities, and the Varaždin kindergarten list contains personal data).

| Pilot | Primary | Secondary | Kindergartens | OSM health points |
| --- | --- | --- | --- | --- |
| Varaždin | 9 | 11 | 14 | 17 |
| Ivanec | 2 | 2 | 1 | 4 |
| Ludbreg | 1 | 1 | 5 | 3 |
| Jalžabet | 1 | 0 | 1 | 0 |
| Breznički Hum | 1 | 0 | 0 | 0 |

## Monthly payments

None of the portals states a licence. `pipeline/config/payments.toml` maps each municipality to its platform; covering another municipality on a supported platform is a config entry. The fetcher keeps 13 months and re-checks the newest months (or files) on each run.

| Pilot | Where | Format | Downloaded (2 Nov 2026) |
| --- | --- | --- | --- |
| Lepoglava | proracun.hr, `kid=37` | JSON per year from `GET https://proracun.hr/dt_i_data.php?kid=37&g=<year>`, the call the site's own table makes; no robots.txt. Fields `datum, stranka, mjesto, posta, oib, iznos_eur, iznos_kn, vrsta_rashoda, opis`. Lepoglava leaves `vrsta_rashoda` blank, so its page has no category chart. Individuals appear as "Uplata fizičkoj osobi". | Nov 2025 – Oct 2026 |
| Maruševec | Kipos, `transparentnost-marusevec.kipos.hr` | JSON, as Jalžabet | 2022-01 – 2026-09, 9,401 rows |
| Sveti Ilija | Kipos, `transparentnost-sveti-ilija.kipos.hr` | JSON, as Jalžabet | 2022-07 – 2026-09, 7,206 rows |
| Jalžabet | Kipos, `transparentnost-jalzabet.kipos.hr` | JSON from `dbapi.php?radim=search…` (answers `[{"tableData": [...]}]`); the date filter is ignored, all years returned | 2022-01 – 2026-09 |
| Breznički Hum | Monthly ODS files under `/images/isplate_iz_proracuna/<year>/` | ODS | publishing lags ~6 months |

**Other open payment data in the county** (checked Nov 2026, not configured): Kipos portals of Cestica, Petrijanec, Vinica, Martijanec, Beretinec and Veliki Bukovec (all current to Sep 2026 except Martijanec, Dec 2025); Visoko on proracun.hr (`kid=24`); Breznica (XLSX) and Gornji Kneginec (CSV) via data.gov.hr. Each is one entry in `payments.toml` (the last two need a parser for their layouts).

**Not open, or open only through the city's export** (not pilots):

- **Varaždin:** `transparentni.varazdin.hr` (Infomare). The portal's search is checked with an invisible reCAPTCHA v3 and is not used. The city named `/Pretraga/GetExport/` as its access point for programmatic export (reply of Nov 2026), and the nightly run fetches one month per request from it (platform `official_csv`); see [varazdin-payments.md](varazdin-payments.md). Its older data.gov.hr datasets (2019–2021 budget extracts) link to `otvoreni.varazdin.hr`, offline since 2023, or to a private network address (`192.168.100.11`); the files were never archived.
- **Ivanec, Ludbreg (and Novi Marof):** Otvoreni grad iTransparentnost (`api.otvorenigrad.hr/itransparentnost/isplate`, CSV per month, header `LC-Tenant: grad-<name>`). It answers HTTP 403 to GitHub's servers and ordinary connections otherwise. ivanec.hr and the cities' data.gov.hr entries only link to the portal, and ludbreg.hr has its own monthly tables only up to January 2025. The block is not worked around. The connector (`otvorenigrad`) stays in the code for a publisher on that platform that does answer.

Layouts:

- **Otvoreni grad (Ludbreg, Ivanec):** `Naziv isplatitelja;Datum;Primatelj;OIB;Mjesto;Proračunski korisnik;Valuta;Iznos na poziciji;Pozicija;Organizacijska klasifikacija;Programska klasifikacija;Izvor financiranja;Ekonomska klasifikacija;Funkcijska klasifikacija;Broj računa;Opis;…`. One row per budget position, so one payment can span several rows. Natural persons appear as `Fizičke osobe` with OIB `GDPR`. Classifications are "code name" in one string; the functional one is COFOG.
- **Kipos (Jalžabet):** `DATUM, GODINA, ISPLATITELJ, NAZIV, OIB, OPCINA, IZNOS (text), IDKONTO, IDKONTO_NAZIV, PROGRAM_ID, PROGRAM_NAZIV`. No COFOG, no description.
- **Breznički Hum ODS:** 6 header lines; `Datum | Naziv isplatitelja | Naziv primatelja | OIB primatelja | Sjedište primatelja | Način objave isplaćenog iznosa` (actually the amount) `| Vrsta rashoda i izdataka`. Continuation rows have a blank date and recipient; the last row is `UKUPNO`; amounts carry float noise.

**Security note:** Jalžabet's `dbapi.php` accepts a raw SQL fragment in a `filter` parameter. The pipeline must not use it. Consider reporting it to the municipality.

## Procurement

**Correction to SPEC.md:** the data.gov.hr dataset the spec cites as the national "contract register 2018–2023" (`247c96e7-…`) is **Grad Ivanec's own register**, published by Ivanec under Otvorena dozvola. No national EOJN dataset exists on data.gov.hr.

Contracts are fetched automatically for every buyer in scope: each municipality plus its own budget users from the RKP register (67 buyers in Varaždin County; `opcina_pipeline/buyers.py`).

| Source key | System | Route | Coverage |
| --- | --- | --- | --- |
| `contracts_eojn_legacy` | Old EOJN RH (`eojn.nn.hr`) | Public contract register form, buyer by buyer, Excel export | 2018 – early 2024, all buyers |
| `contracts_eojn` | New EOJN RH (`eojn.hr`) | Official Open Data API with `X-API-Key` | 2024 onwards, all buyers, **once a key is set** |
| `contracts_municipal` | Publishers' own registers on data.gov.hr | CKAN, one dataset per publisher (`datasets` in sources.toml) | Ivanec 2015–2026, Lepoglava 2018–2026, Varaždinske Toplice 2018–2023 |
| `contracts_ted` | TED (EU Official Journal) | Anonymous search API | 2024 onwards, single-contract award notices above EU thresholds, all buyers |

**Old register (`contracts_eojn_legacy`).** `https://eojn.nn.hr/Spin/application/ipn/JavniReporti/RptRegistarUgovora.aspx` is public, and robots.txt there disallows only `/administrator`. It is an ASP.NET page with a ReportViewer:

1. GET the page for the session cookie, `__VIEWSTATE` and the partner lookup URL.
2. Look the buyer up by OIB in `Common/SearchFrm.aspx` (`__EVENTTARGET=uiFilterSearch`, `uiFilter$Txt_OIB`). Partner ids are stable and cached in `partners.json`.
3. POST the form with the partner id in `ctl04` and every date filter blanked (the page defaults to "updated in the last 3 months").
4. GET `ExportUrlBase` + `EXCELOPENXML` from the response: an xlsx with sheet `RPT_Ugovor` (CSV export returns 500).

There is no national or incremental export: a report needs a buyer, and "view all data" errors. Steady state is two requests per buyer, 3 s apart (~20 minutes for 67 buyers), so the source has `refresh_days = 7`. Files whose cell values have not changed are left untouched. First run, 22 Oct 2026: Varaždin 772 rows, Ivanec 609, Jalžabet 153, Breznički Hum 25, Ludbreg 24; the Ivanec export contains every row of Ivanec's own data.gov.hr file plus 35 later updates.

**Without permission, 2024 onwards.** The new EOJN register is open only through the keyed API below, and eojn.hr's robots.txt forbids everything else. Two open routes cover part of it:

- **TED (`contracts_ted`).** Every procurement above the EU thresholds is also published on TED. The search API (`POST https://api.ted.europa.eu/v3/notices/search`) needs no key; the query is `organisation-identifier-buyer IN (<buyer OIBs>) AND notice-type IN (can-standard can-social) AND publication-date>=20240101`, and the fields the parser needs come back with it (`notices.jsonl`). Licence: reuse with attribution, Commission Decision 2011/833/EU.
  - The notice pages and eForms XML on `ted.europa.eu` are behind an AWS WAF that answers GitHub Actions with a JavaScript challenge (HTTP 202, `x-amzn-waf-action: challenge`, empty body); a pipeline must not try to pass it, so only the API is used.
  - The API's fields are flat lists per notice: with several contracts the winners come in an order unrelated to the contracts. Only notices with one buyer and one contract are used; joint procurements and multi-contract notices are skipped.
  - Framework agreements have no tender value, only a ceiling, so their amount stays unknown rather than counting the ceiling as spending.
  - First run, 2 Nov 2026: 48 notices for the 67 buyers, 28 usable, 25 kept after matching the registers.
- **Publishers' own registers (`contracts_municipal`).** Searched data.gov.hr for every unit in the county (Nov 2026): Ivanec, Lepoglava and Varaždinske Toplice publish their registers as EOJN exports; Sveti Đurđ, Breznica and Maruševec publish other layouts or files on their own sites (not used yet). Lepoglava's grid has a title row above the header.
- **Checked and not useful:** EOJN's monthly OCDS open-data files (`eojn.nn.hr/SPIN/application/ipn/Oglasnik/PreuzimanjeUgovoraOCD.aspx`, free, no registration) hold only the old system's register and updates to it, the same data as `contracts_eojn_legacy`; some files are not valid JSON (unescaped quotes). OpenTender's Croatian data ends in 2024 and is CC BY-NC-SA.

**New register (`contracts_eojn`).** `eojn.hr` robots.txt is `Disallow: /` and its public grid needs a token scraped from the page, so the grid is not used. The official Open Data API (`/api/public/eContractRegister/contractsSearch`, `/api/public/eProcurementData/eventsForContractsByTime`, `getContractData`) needs an `X-API-Key`, requested from **eojn@nn.hr**. The fetcher walks 7-day windows from 2024-01-01 (resuming from `state.json` with a 1-day overlap), keeps contracts whose buyer OIB is in scope, and merges them by `contractId` into `contracts.jsonl`. Without `EOJN_API_KEY` it reports `skipped`. It is unit-tested against the API schema but **not yet tested live**.

**Old-register export layout** (`RPT_Ugovor`, as in Ivanec's 2018–2023 file): sheet `RPT_Ugovor`, merged cells, header on row 14 from column B: `Evidencijski broj nabave | Predmet nabave | CPV | Broj objave iz EOJN RH | Vrsta postupka | Naziv i OIB ugovaratelja | … | Datum sklapanja | Oznaka/broj ugovora | … | Iznos bez PDV-a | Iznos PDV-a | Ukupni iznos s PDV-om | …`.

- The buyer is only in the file title.
- Supplier name and OIB share one cell.
- Amounts are text like `25.000,00 HRK`. **The currency follows the record's last update, not the signing date** (28 contracts from 2022 are in EUR), so parse the suffix on every cell.
- 5 exact duplicate rows; one obvious VAT typo (row 38).

**New-system grid export layout** (Ivanec's 2024+ file on data.gov.hr): sheet `Analytics`, header row 1, 34 columns.

- Buyer name and OIB, supplier name and OIB in separate columns; amounts are numeric EUR.
- Contract URL `https://eojn.hr/contract-eo/{id}` is a unique key.
- Includes amendment columns and `Status ugovora`.
- 216 of 241 rows are purchases exempt from the procurement law.
- One supplier OIB reads `KRIVO_SE_REGISTRIRALI_87607151174`.

Pilot buyer OIBs: Varaždin 13269011531, Ivanec 84121580205, Ludbreg 84947290034, Jalžabet 59790184195, Breznički Hum 35774913576. Pilot institutions seen as buyers: Dječji vrtić Ivančice Ivanec (37103102119), Dječji vrtić Radost Ludbreg (63026242663), Knjižnica i čitaonica "Mladen Kerstner" Ludbreg (52291394442). VARKOM d.o.o. (39048902955) serves several municipalities and cannot be attributed to one.
