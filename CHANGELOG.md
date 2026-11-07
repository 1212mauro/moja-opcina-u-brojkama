# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/); see [CONTRIBUTING.md](CONTRIBUTING.md#versioning) for how versions map to milestones.

## [Unreleased]

### Added

- Frontend design (`docs/design.md`): the home page puts search and the list first with the map beside them; each municipality page opens with one header card (name, key figures, locator map) and a section menu (sticky sidebar on desktop, chips on phones).
- Wide tables scroll inside their card on phones, with edge fades and a keyboard-focusable region.
- Screenshot script for visual QA (`web/scripts/screenshots.mjs`).
- Varaždin payments, fetched nightly from the city's export access point (`/Pretraga/GetExport/`, named by the city in Nov 2026): 12 months, about 2,300 payments a month, cleaned with the same privacy rules (`docs/varazdin-payments.md`).
- Data spot-check script (`scripts/spot_check.py`) and report (`docs/spot-check.md`): 50 figures on the pilot pages checked against their source files.
- Spec, task tracker (`TASKS.md`) and progress script.
- Repository layout, EUPL-1.2 licence, README and contributing guide.
- Python 3.12 pipeline package (`opcina-pipeline`) with ruff and pytest.
- Next.js website configured for static export.
- JSON data contract: Pydantic models → `contract/schema.json` → generated TypeScript types.
- GitHub Actions CI for pipeline and website.
- Pilot municipalities: five Varaždin County units covering all four population bands (`docs/pilots.md`).
- Municipality master table for all 28 Varaždin County units (`opcina master` → `pipeline/config/municipalities.csv`).
- Postcode → municipality lookup (`opcina postcodes` → `pipeline/config/postcodes.csv`).
- Source registry (`pipeline/config/sources.toml`) and source documentation (`docs/sources.md`).
- Automatic fetching of every source (`opcina fetch`): MinFin budget and RKP register, DZS census and estimates, Eurostat LAU codes, Pošta postcodes, DGU boundaries, school and kindergarten registries, OpenStreetMap facilities, monthly payments for 4 of 5 pilots, and EOJN contracts (old register for all buyers; new register via the official API once a key is configured). Polite HTTP with conditional downloads, data-only change detection and a run log (`data/raw/source_runs.jsonl`).
- Nightly fetch workflow on GitHub Actions with cached raw data and a per-source status table.
- Simplified municipality boundaries for the website (`opcina boundaries`).
- Data pipeline (`opcina build`): parsers for population, budget execution, procurement contracts (with kuna conversion and deduplication), monthly payments (natural persons never named) and facilities (with geocoding); peer groups and per-resident ranks; quality gate between staged and published tables; export of one JSON page per municipality, search index, source status and boundaries. Documented in `docs/pipeline.md`.
- Known publisher refusals are reported as "pending access" instead of failing the nightly job.
- Website: home page with municipality list and search (name without diacritics, or postcode); a page for each of the 28 municipalities with key figures, budget by revenue type and function, peer comparison, procurement, monthly payments, facilities and sources; methodology and source-status pages. Charts are server-rendered with a summary sentence and a data table, work without JavaScript, and meet WCAG AA contrast in light and dark mode.
- County map on the home page (every municipality a link, keyboard-navigable, no JavaScript needed) and a locator map on each municipality page.
- Deployment to GitHub Pages (https://1212mauro.github.io/moja-opcina-u-brojkama/) after every successful nightly data build and every website change, with a Croatian 404 page.
- English edition (`/en/`) and a simple-language Croatian edition (`/jednostavno/`), with a language link on every page to the same page in the other editions. Budget categories are translated by code; other names from the data stay in Croatian and are marked `lang="hr"` for screen readers.
- Automated accessibility checks (axe-core, WCAG 2.1 A and AA) on every page of every edition, in light and dark mode, in CI.
- Screen-reader test script (`docs/screen-reader-test.md`) and a draft accessibility statement (not yet published).
- Procurement since 2024 without an API key: contract award notices from TED (EU Official Journal) for every buyer in scope, and the contract registers that towns publish on data.gov.hr (Ivanec, now also Lepoglava and Varaždinske Toplice; source `contracts_municipal` replaces `contracts_ivanec`).


### Changed

- Payments a municipality lists with itself as recipient (Kipos: everything it does not itemise) still count in totals but are no longer shown among the largest recipients.
- Pilots are now Lepoglava, Maruševec, Sveti Ilija, Jalžabet and Breznički Hum: every source of each, payments included, is open. Varaždin, Ivanec and Ludbreg publish payments only behind a CAPTCHA or on a platform that refuses GitHub's servers; their pages keep budget, procurement and facilities. Payments from proracun.hr are a new platform.
- Procurement: the data.gov.hr file the spec cites as national is Grad Ivanec's own register; national access goes through eojn.hr (see `docs/sources.md`).
