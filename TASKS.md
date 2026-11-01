# Moja općina u brojkama — Development Tasks

Task breakdown derived from [SPEC.md](SPEC.md). This file is the single place where development progress is tracked.

## How to use this file

- Tick a task when it is done: `- [ ]` → `- [x]`. Commit the change together with the work, or in the PR that delivers it.
- Claim a task by adding your name after it: `— @ana`. Mark work in progress with `🚧`, e.g. `— 🚧 @ana`.
- Each task has an ID (`B2`), an estimate (`~6h`) and, where relevant, dependencies (`needs B1`). Refer to the ID in branch names and commit messages: `feat/C2-budget-parser`, `C2: parse MinFin budget XLSX`.
- A task is done only when it meets the [Definition of done](#definition-of-done).
- Print progress per section:

  ```bash
  python scripts/progress.py
  ```

## Milestones

| Milestone | Target | Done when | Status |
| --- | --- | --- | --- |
| MVP-1 Data in hand | End of week 1 | Pilots chosen, master table built, all raw files downloaded and documented (A, B) | 🟨 |
| MVP-2 First complete page | End of week 2 | One pilot municipality has a full page from real data (C, D1–D5) | ✅ |
| MVP-3 All pilots, all features | End of week 3 | 5 pilots live with every MVP feature (C, D, F1–F2) | ✅ |
| MVP-4 Submission | End of week 4 | Accessible, bilingual, deployed, tested with residents, video recorded (E, F, G) | ⬜ |
| v1-M3 Pilot data live | M3 | Production pipeline publishing pilot data | ⬜ |
| v1-M5 Beta | M5 | All 556 units on the beta site | ⬜ |
| v1-M6 Public launch | M6 | Production live, WCAG 2.1 AA audit passed | ⬜ |

Status: ⬜ not started · 🟨 in progress · ✅ done

---

## Datathon MVP (4 weeks, ~320 h, 5 pilot municipalities)

MVP architecture (SPEC → Deployment): a Python pipeline run on a laptop or in GitHub Actions writes pre-computed JSON files; a Next.js static site reads them and is hosted on GitHub Pages. No server, no database.

### A. Project setup — week 1 (~16 h)

- [x] A1 Agree on repo layout: `pipeline/` (Python), `web/` (Next.js), `data/raw/` (git-ignored downloads), `web/public/data/` (generated JSON) (~1h)
- [x] A2 Add `LICENSE` (EUPL-1.2) and a `README.md` with the goal and how to run the pipeline and the site (~1h)
- [x] A3 Set up the Python 3.12 project in `pipeline/`: polars, openpyxl, httpx, pytest, ruff (~2h)
- [x] A4 Set up the Next.js + TypeScript app in `web/` with static export (`output: 'export'`) and ESLint (~3h)
- [x] A5 GitHub Actions CI on every PR: ruff + pytest for `pipeline/`, lint + build for `web/` (~3h, needs A3, A4)
- [x] A6 Define the JSON data contract between pipeline and frontend (per-municipality file, search index, boundaries) as TypeScript types + an example file (~4h)
- [ ] A7 Agree on team roles, a weekly check-in, and the branch/PR convention (~2h) — conventions in CONTRIBUTING.md; roles and check-in time still to fill in

### B. Pilot selection and raw data — week 1 (~41 h)

- [x] B1 Pick 5 pilot municipalities of different sizes, ideally in one county so peer comparison works; include at least one city and cover several population bands; write down why (~3h)
- [x] B2 Build the master table for the pilots (and their county peers): OIB, RKP, DZS code, LAU code, name, county, type → `pipeline/config/municipalities.csv` (~6h, needs B1)
- [x] B3 Download the latest Ministry of Finance budget execution XLSX (plus the previous year for context) (~2h)
- [x] B4 Download the EOJN contract register 2018–2023 XLSX; find out how to export 2024+ contracts from the new EOJN (~5h) — automatic: old register (eojn.nn.hr) for all 67 buyers; new EOJN via the official API once `EOJN_API_KEY` is set (request from eojn@nn.hr)
- [x] B5 Download DZS Census 2021 and the latest population estimates; check settlement → municipality roll-up (~5h)
- [x] B6 Get DGU administrative boundaries (WFS/GeoJSON) for the pilot county and simplify the polygons for the browser (~5h) — DGU ATOM feed, pyproj, coverage simplification (`opcina boundaries`)
- [x] B7 Collect school, kindergarten and health facility lists for the pilots from data.gov.hr; use OpenStreetMap (Overpass) where none exist (~6h)
- [x] B8 Find 1–2 pilots that publish monthly payment disclosures as CSV/XLSX and download the last 12 months (~4h, needs B1) — 4 of 5 pilots (Varaždin is behind reCAPTCHA)
- [x] B9 Build a postcode → municipality lookup for the pilots (~2h, needs B2)
- [x] B10 Document every source in `docs/sources.md`: URL, publisher, licence, date fetched, known quirks (~3h)

### C. Data pipeline — weeks 1–2 (~82 h)

- [x] C1 Fetch step: download each source into `data/raw/`, store file hash, row count and timestamp as a `source_run` record (~6h) — `opcina fetch`, every source automatic; see docs/sources.md
- [x] C2 Budget parser: MinFin XLSX → `budget_line` (year, period, account code, COFOG function, amount_eur); keep the column mapping in a config file, not in code (~12h, needs B3) — `parse/budget.py`; all 3 reconciliations hold for 28 units × 7 years
- [x] C3 Kuna → euro conversion at the fixed rate 7.53450 HRK/EUR for pre-2023 figures, keeping the original value in its own column; unit tests (~3h, needs C2) — contract amounts per cell; budget file already in EUR
- [x] C4 Population loader and per-resident figures (~4h, needs B5) — `parse/population.py`
- [x] C5 Procurement parser: EOJN XLSX → `contract`; match buyers by OIB, and attribute contracts of the municipality's own budget users (kindergartens, utilities) via the MinFin budget-user register (~12h, needs B2, B4) — `parse/contracts.py`; 5,379 contracts, budget users attributed via the RKP register
- [x] C6 Deduplicate contracts across old and new EOJN on contract number + OIB; record the data's start and end dates (~3h, needs C5) — number + supplier (numbers are reused), priority eojn > legacy > municipal
- [x] C7 Payments parser for the pilots' file format(s) → `payment`; payments to private individuals only as the aggregated categories the Naputak prescribes, never by name (~10h, needs B8) — `parse/payments.py`; 4 pilots, natural persons never named (docs/pipeline.md)
- [x] C8 Facilities: normalise columns across publishers, geocode addresses that lack coordinates (cached, rate-limited), assign to municipalities by point-in-polygon (~10h, needs B6, B7) — `parse/facilities.py`; 199 facilities, Nominatim cached
- [x] C9 Peer groups: same county, same type, population band (<3,000; 3,000–10,000; 10,000–35,000; >35,000); compute basic ranks (~5h, needs C2, C4) — `peers.py`
- [x] C10 Quality gate: schema unchanged, row counts within ±20% of the last run, totals reconcile; on failure keep the last good output (~6h) — `quality.py`; staging → published
- [x] C11 Export: one JSON file per municipality, a search index, simplified boundaries; every figure references its `source_run` (~6h, needs A6) — `export.py`; all 28 units get a page
- [x] C12 Parser tests with small fixture files for budget, procurement and payments (~5h) — 173 tests

### D. Frontend — weeks 2–3 (~90 h)

- [x] D1 Base layout, design tokens, header and footer with source attribution and licences (~6h, needs A4) — tokens checked for AA in light and dark
- [x] D2 Search by municipality name (diacritic-insensitive: "cakovec" finds "Čakovec") and by postcode (~6h, needs C11, B9) — static list + search box with JavaScript
- [x] D3 County map with municipality polygons; clicking one opens its page (MapLibre GL JS) (~8h, needs B6) — server-rendered SVG with linked municipalities instead of MapLibre: works without JavaScript and by keyboard; locator map on every page
- [x] D4 Municipality page route, statically generated for every pilot (~4h, needs C11) — all 28 units, not only the pilots
- [x] D5 Budget card: revenue, spending by function, per-resident figures; Observable Plot chart + HTML data table + one-sentence plain summary (~14h, needs D4) — server-rendered HTML/SVG instead of Observable Plot, so charts need no JavaScript
- [x] D6 Basic peer comparison: per-resident figures and rank against same-county, same-band peers (~10h, needs C9)
- [x] D7 Procurement section: recent awards and top suppliers (~8h, needs C5)
- [x] D8 Monthly payments explorer for the 1–2 units with data: month filter, categories, top recipients (~10h, needs C7) — 4 pilots
- [x] D9 Services map plus a text list of facilities grouped by type (the map is optional, the list is not) (~10h, needs C8) — list with OpenStreetMap links; the map comes with D3
- [x] D10 "Where does this number come from?" link on every figure: source file and date (~4h)
- [x] D11 Methodology page: sources, matching rules, peer groups, context notes, no judgement of whether spending is "good" (~4h)
- [x] D12 Missing-data states, e.g. "this municipality does not publish machine-readable payment files" (~3h)
- [x] D13 Mobile and responsive pass (~3h) — checked at 375 px

### E. Language and accessibility — weeks 3–4 (~40 h)

- [ ] E1 next-intl with Croatian (default) and English message files (~6h)
- [ ] E2 Simple-language mode as a third message set, at roughly primary-school reading level (~8h, needs E1)
- [ ] E3 Keyboard navigation, visible focus, skip link, 4.5:1 text contrast (~6h)
- [ ] E4 axe-core accessibility checks in CI (~5h, needs A5)
- [ ] E5 Screen-reader test with NVDA and VoiceOver on a full municipality page; fix findings (~8h)
- [x] E6 Core content works without JavaScript (~3h) — everything but the search box is static HTML
- [ ] E7 Draft the accessibility statement using the EU template (~4h)

### F. Deployment — weeks 3–4 (~16 h)

- [x] F1 GitHub Actions workflow that runs the pipeline and publishes the generated JSON (~6h, needs C11) — nightly `fetch.yml`, then `deploy.yml` exports and publishes
- [x] F2 Deploy the static site to GitHub Pages (base path, 404 page) (~5h, needs A4) — https://1212mauro.github.io/moja-opcina-u-brojkama/
- [x] F3 Source-status section showing when each source was last refreshed (~3h, needs C1) — /izvori/
- [ ] F4 Smoke-test the deployed site: every pilot page, both languages, all links (~2h) — 🚧 Croatian done (31 pages, 12 assets, no broken links); English after E1

### G. Testing and demo — week 4 (~38 h)

- [ ] G1 Test with 3–5 residents: "find how much your municipality spends on kindergartens", timed against the 60-second target (~8h)
- [ ] G2 Fix the findings from G1 (~8h)
- [ ] G3 Data spot-check: compare 10 figures per pilot with the source files (~6h)
- [ ] G4 Write the video script around one resident's question and how the app answers it (~4h)
- [ ] G5 Record and edit the video (~8h)
- [ ] G6 Submission: README, live demo link, screenshots (~4h)

---

## Production v1 (~6 months, ~1,100 person-hours, all 556 units)

Starts after the funding or adoption decision (M0); the Ministry conference on 23 November 2026 is the natural moment to seek it. Production architecture: nightly pipeline → PostgreSQL 16 + PostGIS (staging and published schemas) → FastAPI + statically generated Next.js site, packaged with Docker Compose.

### P0. Funding and adoption — before M0

- [ ] P0.1 Present the MVP and the cost plan at the Ministry conference (23 Nov 2026)
- [ ] P0.2 Get real quotes to replace the assumed hourly rates
- [ ] P0.3 Find a long-term owner (Ministry or civil-society partner) to cover the maintainer risk

### P1. Discovery and UX — M0–M1 (100 h)

- [ ] P1.1 Interviews with residents and journalists
- [ ] P1.2 Wireframes for the municipality page, comparison view, services map and search
- [ ] P1.3 Design system (tokens, components, chart styles) built for WCAG 2.1 AA

### P2. Data model and entity matching — M0.5–M2 (90 h)

- [ ] P2.1 PostgreSQL schema: `municipality`, `population`, `budget_line`, `payment`, `contract`, `facility`, `source_run`
- [ ] P2.2 Master table for all 556 units: OIB, RKP, DZS code, LAU code, boundary geometry
- [ ] P2.3 Budget-user attribution from the MinFin register (institutions → parent unit)
- [ ] P2.4 Yearly peer groups and full ranks
- [ ] P2.5 Provenance: every row links to its `source_run`

### P3. Data ingestion and validation — M0.5–M3.5 (260 h)

- [ ] P3.1 Connector: MinFin budget execution, all years, column mapping per year in config
- [ ] P3.2 Connector: EOJN 2018–2023 XLSX and the new EOJN register (2024+), deduplicated
- [ ] P3.3 Connector: DZS census and yearly population estimates
- [ ] P3.4 Connector: DGU boundaries, simplified for the browser
- [ ] P3.5 Connector: facility lists from data.gov.hr + OpenStreetMap fallback, with geocoding
- [ ] P3.6 Payment-file parsers for the 3–4 most common formats
- [ ] P3.7 Payments coverage map: which units are included
- [ ] P3.8 Staging → published load with the quality gate; failed checks keep the old data and alert the maintainer
- [ ] P3.9 Nightly scheduling with systemd timers
- [ ] P3.10 Pilot data live (milestone v1-M3)

### P4. DevOps and security — M1–M2 (60 h)

- [ ] P4.1 Production (4 vCPU / 8 GB) and staging (2 vCPU / 4 GB) EU servers, SSH keys only, automatic security updates
- [ ] P4.2 Docker Compose setup, Caddy with automatic HTTPS
- [ ] P4.3 CI/CD: lint, tests, axe-core, build on every PR; `main` deploys to staging; one-click production promotion; previous image kept for rollback
- [ ] P4.4 Nightly database dumps to object storage, 30-day retention, monthly restore test
- [ ] P4.5 Monitoring: Uptime Kuma, GlitchTip, public source-status page
- [ ] P4.6 Cookieless self-hosted analytics (Plausible or Umami)

### P5. Backend and public API — M2–M4 (120 h)

- [ ] P5.1 FastAPI service with a read-only database user and rate limiting
- [ ] P5.2 Endpoints for municipality, budget, peers, contracts, payments, facilities
- [ ] P5.3 CSV exports of the joined data
- [ ] P5.4 OpenAPI documentation with licence and attribution

### P6. Frontend — M2–M5 (240 h)

- [ ] P6.1 Static generation of all 556 municipality pages, HR/EN
- [ ] P6.2 Search with pg_trgm/unaccent-equivalent matching, postcode and map click
- [ ] P6.3 Full comparison view with ranks
- [ ] P6.4 Services map on self-hosted PMTiles
- [ ] P6.5 Payments explorer for all covered units
- [ ] P6.6 Simple-language mode across the whole site
- [ ] P6.7 Downloads and API links on every page
- [ ] P6.8 Beta with all 556 units (milestone v1-M5)

### P7. Accessibility and content — M3.5–M5 (70 h)

- [ ] P7.1 WCAG 2.1 AA fixes from the audit
- [ ] P7.2 Plain-language texts and context notes (e.g. tourist towns with small populations)
- [ ] P7.3 Methodology page and right-of-reply contact for municipalities
- [ ] P7.4 Published accessibility statement (EU template, Information Commissioner as complaints body)

### P8. QA and user testing — M4.5–M6 (80 h)

- [ ] P8.1 Automated test suite for pipeline, API and frontend
- [ ] P8.2 User testing round 1 with residents, including screen-reader users
- [ ] P8.3 User testing round 2 after fixes
- [ ] P8.4 External WCAG 2.1 AA audit with no open critical issues

### P9. Project management — M0–M6 (80 h)

- [ ] P9.1 Planning and progress reporting
- [ ] P9.2 Contact with data publishers (MinFin, EOJN, DZS, DGU, municipalities)
- [ ] P9.3 Public launch (milestone v1-M6)

---

## Phase 2 backlog (not scheduled)

- [ ] X1 Trends over 5+ years in peer comparison
- [ ] X2 Supplier profiles linked to the court register API
- [ ] X3 EU TED notices for above-threshold tenders
- [ ] X4 Automated scraping of payment disclosures that are not machine-readable
- [ ] X5 Travel-time coverage gaps on the services map
- [ ] X6 Email alerts for new contracts in my municipality
- [ ] X7 More languages

---

## Definition of done

A task is done when:

- The code is merged to `main` through a reviewed PR and CI is green.
- Parsers and data transforms have tests with fixture files.
- Every new figure on screen has a data table, a plain summary, and a link to its source.
- New UI works by keyboard, has visible focus, meets 4.5:1 contrast and passes axe-core.
- New UI text exists in Croatian, English and simple-language versions.
- No personal data about private individuals is shown.

## Success metrics (6 months after launch)

| Metric | Target | Current |
| --- | --- | --- |
| Municipalities with a complete budget card | 556 of 556 | – |
| Municipalities in the payments explorer | ≥ 150 | – |
| Pages with data refreshed on schedule | ≥ 95% | – |
| Task success: "find how much your municipality spends on kindergartens" | 80% within 60 s | – |
| WCAG 2.1 AA audit | No open critical issues | – |
| Monthly maintenance time | ≤ 15 h | – |
