# Data pipeline

How raw open data becomes the website's JSON. Sources and their quirks are in [sources.md](sources.md).

```bash
cd pipeline
opcina fetch      # download every source into data/raw/            (C1)
opcina master     # rebuild config/municipalities.csv               (B2)
opcina postcodes  # rebuild config/postcodes.csv                    (B9)
opcina build      # parse -> quality gate -> export                 (C2–C11)
```

`opcina build` is `opcina parse`, `opcina gate` and `opcina export` in one go. The nightly workflow (`.github/workflows/fetch.yml`) runs all of it.

## Stages

| Stage | Reads | Writes |
| --- | --- | --- |
| Fetch | publishers' sites and APIs | `data/raw/<source>/`, `data/raw/source_runs.jsonl` |
| Parse | `data/raw/` | `data/interim/staging/<table>.parquet` |
| Gate | staging + last published | `data/interim/published/<table>.parquet`, `data/interim/quality_report.json` |
| Export | published tables | `web/public/data/` (one page per municipality, search index, source status, boundaries) |

## Tables

Schemas are in `pipeline/src/opcina_pipeline/tables.py`. Every row carries `dzs_code` (the municipality) and `source_run_id` (the fetch it came from).

| Table | Parser | Rows (Varaždin County, Oct 2026) | Notes |
| --- | --- | --- | --- |
| `population` | `parse/population.py` | 448 | census 2021 + DZS estimates 2011–2025 |
| `budget_line` | `parse/budget.py` | 224,560 | 28 units × 2019–2025; economic, COFOG and derived positions; layout in `config/budget_layout.toml` |
| `contract` | `parse/contracts.py` | 5,379 | old EOJN register (61 buyers), Ivanec's own register, new EOJN API when a key is set |
| `payment` | `parse/payments.py` | 15,540 | Ivanec, Ludbreg, Jalžabet, Breznički Hum |
| `facility` | `parse/facilities.py` | 199 | ministry school and kindergarten registries + OpenStreetMap |

## Rules that matter

- **Matching.** Everything is tied to a municipality by code: the master table joins the RKP register to the DZS/LAU code. Contracts of a municipality's own budget users (kindergartens, libraries) count for that municipality (SPEC rule 1).
- **Kuna.** Contract amounts published in HRK are converted at 7.53450 per euro when parsed, cell by cell, because the old register's currency follows the record's last update rather than the signing date. The original text is kept. The MinFin budget file is already in euro for every year.
- **Budget reconciliation.** For every unit and year: the sum of COFOG functions equals R1, R1 equals total expenditure minus transfers to own budget users (account 367), and total revenue equals classes 6 + 7. The parser stops if any of these fails.
- **Budget hierarchy.** Parent and child accounts both appear (6 → 61 → 611), so only one level may be summed. Some derived positions are not euros (Z006–Z009 are employee counts).
- **Peer groups (SPEC rule 3).** Same county, same type and same population band in that year (under 3,000; 3,000–10,000; 10,000–35,000; over 35,000). Rank 1 is the highest per-resident figure.
- **Payments window.** Pages show 12 calendar months up to the newest complete month. The month in progress is left out, and a month a publisher skipped stays a visible gap.

## Personal data

The app republishes only what municipalities must publish, and never names private individuals (SPEC, GDPR).

- A payment is to a natural person when any of these applies:
  - the publisher marks it (OIB "GDPR");
  - its label stands for people (salaries, "ugovor o djelu", meeting fees);
  - the municipality pays itself on a personal-expense account;
  - the recipient name looks like a person's, **even if an OIB is published**. Some portals print people with their personal OIB;
  - the name carries no organisation marker (legal form, "obrt", "udruga", …) **and** its OIB is not a known business or public body, meaning neither a supplier or buyer in the procurement registers nor an entity in the MinFin register. This is the safety net for people the name rules miss. It also hides some small associations and firms (in October 2026, 75 recipients, 0.5 % of named spending).

  Such rows keep only the amount and the expense category; name and OIB are cleared.
- Free-text payment descriptions are dropped entirely, because they name employees and welfare recipients.
- Health facility names that contain a doctor's name are replaced with a generic label ("Ordinacija opće medicine").
- The quality gate refuses to publish a payment table in which any natural-person row still has a name or OIB.

Two choices currently keep a name because it is a business name. **Both are open policy decisions:**

1. **Sole traders** (obrt "vl. …", OPG, notaries, lawyers) keep their name and OIB as payment recipients and suppliers, but an obrt's OIB is its owner's personal OIB. Where a publisher marks them GDPR (Ivanec does), they stay hidden.
2. **Pharmacies** named after their owner (e.g. "Ljekarna <ime prezime>") keep that trade name.

## Every source and table stands alone

One source or table never holds back another:

- **A source that fails to download** keeps the files of its last successful download. The build uses them, and the website marks the source as "zadnje preuzimanje nije uspjelo; prikazujemo prethodne podatke", with the date of those files. Every other source updates as usual.
- **A table the quality gate rejects** keeps its last published version. Every table that passed is published.
- **The website deploys after every nightly run**, whether it succeeded or failed (`deploy.yml`), so everything that did update goes live. Only a cancelled run does not deploy.

A red nightly job is therefore only an alert to the maintainer (GitHub emails on a failed scheduled run). It happens when a table fails the quality gate, or when a source is overdue: it failed and has no successful download in the last 7 days (`STALE_LIMIT_DAYS` in `fetch/__init__.py`). A shorter outage shows as a "Source down" warning on the run page. Example: on 8 Nov 2026, data.gov.hr reset every connection from GitHub's runners while it answered normally elsewhere; eight sources kept their files from the day before, and the rest updated.

## Quality gate

A staged table is published only if all of these hold:

- its schema matches exactly;
- its row count is within ±20 % of the last published version;
- its own checks pass: no duplicate keys, no missing required values, every municipality present, natural persons anonymous, facilities inside Croatia.

Otherwise the last published version stays live. Every table that passed is still exported. `opcina gate` / `opcina build` then exit with an error, which makes the nightly job email the maintainer; the other tables still go live. Contract amounts may legitimately be empty (not published) or negative (annexes that lower a contract).

When a jump in row count is expected, accept it once and let every other check still run. Examples: a municipality added to `payments.toml`, a new county, or the EOJN API backfill once a key is set.

```bash
opcina build --accept contract
```

On GitHub, run the "Fetch and build data" workflow by hand and enter the table name in the `accept` field.

On the website, procurement counts and recent awards leave out annexes ("Dodatak ugovoru", "Aneks"); their value still counts in the totals.
