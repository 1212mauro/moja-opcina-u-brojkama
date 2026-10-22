# Pilot municipalities (task B1)

The datathon MVP covers five pilots, all in **Varaždin County** (Varaždinska županija), so that peer comparison works: peers are units of the same county, same type and same population band (SPEC → Data model). The pipeline loads all 28 units of the county so every pilot has its full peer group.

| Pilot | Type | DZS/LAU code | Census 2021 | Estimate 2025 | Population band | OIB | RKP |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Varaždin | grad | 04723 | 43,782 | 44,283 | over 35,000 | 13269011531 | 31350 |
| Ivanec | grad | 01562 | 12,723 | 12,974 | 10,000–35,000 | 84121580205 | 31681 |
| Ludbreg | grad | 02445 | 8,477 | 8,558 | 3,000–10,000 | 84947290034 | 31585 |
| Jalžabet | općina | 01651 | 3,183 | 3,206 | 3,000–10,000 | 59790184195 | 31632 |
| Breznički Hum | općina | 01511 | 1,132 | 1,102 | under 3,000 | 35774913576 | 31761 |

## Why these five

- **All four population bands are covered**, from the county seat to one of the smallest municipalities in Croatia, so the page design is tested against very different budget sizes (EUR 1.2M to EUR 80M of yearly spending in 2025).
- **Both unit types** (grad and općina) are included.
- **Ludbreg and Jalžabet share a band** but differ in type, which shows why the peer rule also groups by type.
- **One county** keeps the data work small: one MinFin budget file (`05 Varaždinska.xlsx`), one boundary set, one set of facility lists.
- **Ivanec publishes its contract register as open data** on data.gov.hr (2010–2026), so at least one pilot has complete procurement data.

## Data available per pilot (as of 22 Oct 2026)

| Pilot | Budget 2019–2025 | Contracts | Payments (12 months) | Budget users in RKP register |
| --- | --- | --- | --- | --- |
| Varaždin | yes | not yet: eojn.hr access pending | no: portal behind reCAPTCHA | 19 |
| Ivanec | yes | 2018–2026, data.gov.hr | yes, CSV API | 3 |
| Ludbreg | yes | not yet: eojn.hr access pending | yes, CSV API | 4 |
| Jalžabet | yes | not yet: eojn.hr access pending | yes, JSON (from 2022) | 1 |
| Breznički Hum | yes | not yet: eojn.hr access pending | yes, ODS (lags ~6 months) | 0 |

Details and quirks for each source: [sources.md](sources.md).

The pilot list lives in `pipeline/config/scope.toml`; `opcina master` checks that every pilot exists in the county.
