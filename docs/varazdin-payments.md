# Varaždin payments: the monthly routine

Grad Varaždin publishes its payments only on [transparentni.varazdin.hr](https://transparentni.varazdin.hr/), whose search runs an invisible reCAPTCHA v3 check before every query. The pipeline therefore never requests anything from it. A person saves the month's export by hand, and everything after that is automatic.

## Once a month (after the 20th, when the previous month is complete)

1. **Get the links.**

   ```
   cd pipeline
   .venv/Scripts/opcina varazdin-link 2026-10 --pages 15
   ```

   These are the same links the portal's "CSV" button gives after a search: one per page of 80 payments, all payers (the city and its institutions). A month is about 12 pages; a page past the end is simply empty.

2. **Save each CSV** into `data/inbox/varazdin/`, under any name (the browser may call it `GetExport`; that is fine). Saving a page twice is harmless.

3. **Import.**

   ```
   .venv/Scripts/opcina import-varazdin
   ```

   This also runs on its own whenever you run `opcina fetch` or `opcina fetch payments` locally. It:

   - reads every CSV in the inbox together with the ones saved before (`done/`), and groups the payments by month;
   - drops exact duplicate rows (a page saved twice);
   - warns if a month looks incomplete: gaps in the row numbers, or a first payment later than the 5th;
   - applies the site's privacy rules, so individuals' names and OIBs and every "Svrha isplate" description are removed, and writes `pipeline/manual/payments/04723/<YYYY-MM>.csv`;
   - moves the inbox files to `data/inbox/varazdin/done/`.

   **If it warns that pages are missing,** save those pages and run it again: the month is rebuilt from all its saved pages.

4. **Commit and push** `pipeline/manual/payments/04723/`. The nightly run copies the files into the data and publishes them; Varaždin's page shows payments up to the newest imported month.

## Where it is wired in

| What | Where |
| --- | --- |
| Link generator, export reader, importer | `pipeline/src/opcina_pipeline/varazdin.py` |
| Commands `varazdin-link`, `import-varazdin` | `pipeline/src/opcina_pipeline/cli.py` |
| Inbox, never committed (it may hold personal data) | `data/inbox/varazdin/` (in `.gitignore`) |
| Cleaned monthly files, committed | `pipeline/manual/payments/04723/` |
| Varaždin's entry, platform `manual` | `pipeline/config/payments.toml` (`["04723"]`) |
| Copy into the data on every run, import first if the inbox has files | `fetch_manual` in `pipeline/src/opcina_pipeline/fetch/payments.py` |
| Reading the cleaned files; the privacy rules run again | `parse_manual` in `pipeline/src/opcina_pipeline/parse/payments.py` |
| Nightly run that publishes it | `.github/workflows/fetch.yml` → `deploy.yml` |

## The export

The CSV is `;`-separated UTF-8 with a BOM. Its columns are:

```
Rbr;Datum isplate;Isplatitelj;Primatelj;PTT broj;Sjedište primatelja;OIB;Iznos isplate;Valuta;Svrha isplate;Vrsta rashoda/izdatka
```

- **Dates** are `yyyymmdd`.
- **Amounts** use a decimal comma (`1.201,29`).
- **The expense type** is "code label" (`3222 Materijal i sirovine`).
- **Payers** include the city's institutions: the kindergarten, the primary schools, the theatre, the library and others.

An export holds only the 80 rows of one page. The importer refuses a file whose header differs, so a changed layout is noticed at once.
