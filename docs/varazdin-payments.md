# Varaždin payments

Grad Varaždin publishes its payments on [transparentni.varazdin.hr](https://transparentni.varazdin.hr/). The portal's search is checked with an invisible reCAPTCHA v3, and the pipeline never uses it.

In November 2026 the city named a separate access point for programmatic export:

> `https://transparentni.varazdin.hr/Pretraga/GetExport/` accepts the search criteria as URL parameters (year, month, transaction type, currency, number of records and the other filters); `exportType` sets the format.

The nightly run fetches it once per month for the last 13 months.

## Where it is wired in

| What | Where |
| --- | --- |
| The address and its parameters | `url` (and `max_rows`) in Varaždin's entry `["04723"]`, `pipeline/config/payments.toml` |
| Fetching, once per month on every run | `fetch_official_csv` in `pipeline/src/opcina_pipeline/fetch/payments.py` (platform `official_csv`) |
| Reading the CSV, cleaning it for publication | `read_export`, `write_cleaned`, `fetch_official` in `pipeline/src/opcina_pipeline/varazdin.py` |
| Raw answers, outside git | `data/raw/payments/04723/raw/<YYYY-MM>.csv` |
| Cleaned months | `data/raw/payments/04723/<YYYY-MM>.csv` |
| Parsing the cleaned months; the privacy rules run again | `parse_official_csv` in `pipeline/src/opcina_pipeline/parse/payments.py` |
| Nightly run that publishes it | `.github/workflows/fetch.yml` → `deploy.yml` |

## The request

`{year}` and `{month_int}` in `url` are filled in for each month. The other parameters, taken from the portal's own export link:

| Parameter | Value | Meaning |
| --- | --- | --- |
| `Uprave` | `0` | all payers: the city and its institutions (kindergarten, schools, theatre, library…) |
| `Valuta` | `191` | euro |
| `IsplataUplata` | `10` | payments |
| `preskoci` / `uzmi` | `0` / `10000` | skip none, take up to 10,000 records |
| `exportType` | `1` | CSV |

A full month is about 2,300 rows (September 2026: 2,255, numbered 1–2,255 with no gaps, 6,476,383.18 €). If a month ever reaches `max_rows`, the run says so: the answer may then be cut short, and `uzmi` and `max_rows` should be raised together.

## The CSV

The CSV is `;`-separated UTF-8 with a BOM. Its columns are:

```
Rbr;Datum isplate;Isplatitelj;Primatelj;PTT broj;Sjedište primatelja;OIB;Iznos isplate;Valuta;Svrha isplate;Vrsta rashoda/izdatka
```

Quirks the reader handles:

- **Dates** are `yyyymmdd`, and **amounts** use a decimal comma.
- **Names arrive HTML-escaped and unquoted** (`ŠMEK&amp;SNACK`). The `;` of an entity would split the field, so entities are decoded before splitting.
- **Some rows end with a stray `;`**, an empty 12th field. Real extra data is refused.
- **Payroll rows list several accounts in one field** ("3111 Plaće za redovan rad, 3121 …"). The first account stands for the row.

What is published follows the same privacy rules as every other source: no names or OIBs of individuals, and never the "Svrha isplate" description.

**Failure modes:**

- An answer that is not this layout is noted in the run log, not failed.
- An endpoint that is down keeps the last good months.
