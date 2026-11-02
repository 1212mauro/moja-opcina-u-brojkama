# Pilot municipalities (task B1)

The datathon MVP covers five pilots, all in **Varaždin County** (Varaždinska županija), so that peer comparison works: peers are units of the same county, same type and same population band (SPEC → Data model). The pipeline loads all 28 units of the county so every pilot has its full peer group, and every unit gets a page.

| Pilot | Type | DZS/LAU code | Census 2021 | Estimate 2025 | Population band | OIB | RKP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Lepoglava | grad | 02291 | 6,945 | 6,653 | 3,000–10,000 | 79368224789 | 31544 |
| Maruševec | općina | 02607 | 5,682 | 5,539 | 3,000–10,000 | 26670454549 | 31497 |
| Sveti Ilija | općina | 04383 | 3,242 | 3,181 | 3,000–10,000 | 10443118219 | 31421 |
| Jalžabet | općina | 01651 | 3,183 | 3,206 | 3,000–10,000 | 59790184195 | 31632 |
| Breznički Hum | općina | 01511 | 1,132 | 1,102 | under 3,000 | 35774913576 | 31761 |

## Why these five

- **Every source is open for each of them**, payments included: no API key, no access request, nothing behind a CAPTCHA or a block on GitHub's servers. A pilot is a unit whose page can be complete from the nightly job alone.
- **Both unit types** (grad and općina) are included, and **Lepoglava and the općine share a band**, which shows why the peer rule also groups by type.
- **Three payment platforms** are covered: proracun.hr (Lepoglava), Kipos (Maruševec, Sveti Ilija, Jalžabet) and monthly ODS files (Breznički Hum).
- **One county** keeps the data work small: one MinFin budget file (`05 Varaždinska.xlsx`), one boundary set, one set of facility lists.

## Changed on 2 Nov 2026

The first pilots were Varaždin, Ivanec and Ludbreg (one per band over 3,000) with Jalžabet and Breznički Hum. Their payments turned out not to be openly available: Varaždin publishes them only behind a reCAPTCHA, and Ivanec and Ludbreg on Otvoreni grad, whose API refuses GitHub Actions (HTTP 403). No other copy exists (docs/sources.md). They were replaced by units with open payments.

**Cost:** no pilot is over 10,000 residents. Varaždin is the county's only unit over 35,000, and both units between 10,000 and 35,000 (Ivanec, Novi Marof) are on Otvoreni grad. Varaždin and Ivanec keep their pages with budget, procurement and facilities, only without payments.

## Data available per pilot (as of 2 Nov 2026)

| Pilot | Budget 2019–2025 | Contracts | Payments (12 months) |
| --- | --- | --- | --- |
| Lepoglava | yes | 418, 2018 – Jan 2026 (old EOJN register + own register on data.gov.hr) | yes, proracun.hr JSON (no expense categories) |
| Maruševec | yes | 190, 2018 – Jan 2024 (old EOJN register) | yes, Kipos JSON (from 2022) |
| Sveti Ilija | yes | 77, 2019 – Dec 2023 (old EOJN register) | yes, Kipos JSON (from 2022) |
| Jalžabet | yes | 168, 2017 – Apr 2025 (old EOJN register + TED) | yes, Kipos JSON (from 2022) |
| Breznički Hum | yes | 25, 2014 – Sep 2023 (old EOJN register) | yes, ODS (lags ~6 months) |

Contracts signed in the new EOJN system since 2024 appear only where the unit publishes its own register or the contract is on TED; the rest would need the keyed EOJN API.

Details and quirks for each source: [sources.md](sources.md).

The pilot list lives in `pipeline/config/scope.toml`; `opcina master` checks that every pilot exists in the county.
