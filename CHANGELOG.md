# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/); see [README → Versioning](README.md#versioning) for how versions map to milestones.

## [Unreleased]

### Changed

- Video: the narration is a full script (`docs/video/naracija.md`): for each scene the time, what is on screen, the caption and the spoken text in full sentences, plus the whole text to read in one piece. The video is now 2:18.

## [0.4.0] - 2026-11-08

Datathon submission (MVP-4). Live site: https://1212mauro.github.io/moja-opcina-u-brojkama/

### Fixed

- One source or table no longer holds back the others. A source that fails to download keeps its last good files (the sources page says so), a table the quality gate rejects keeps its last published version, and the website now deploys after every nightly run, failed or not. A red nightly run is only an alert: a rejected table, or a source with no successful download in 7 days.
- Bar charts: all tracks in one chart now have the same length, so bars are comparable (each row used to size its own value column).
- Home list fits a 360 px phone; source cards have inner padding; dates no longer wrap.

### Added

- Video presentation (G4/G5): a 2:18 walkthrough in Croatian, recorded from the built site with on-screen captions (`web/scripts/video.mjs`), with subtitles and a timed narration to read over it (`docs/video/`). It covers what the datathon rules ask for: problem, users, data sources, features, technical architecture, value and further development.
- Solution documentation in Croatian for the datathon submission (`docs/prijava.md`): every dataset with publisher, link and licence, how they are linked, architecture, standards, prerequisites, limits, further development and the tools used (including AI). README links the live site, video and screenshots.
- Frontend design (`docs/design.md`): the home page puts search and the list first with the map beside them; each municipality page opens with one header card (name, key figures, locator map) and a section menu (sticky sidebar on desktop, chips on phones).
- Wide tables scroll inside their card on phones, with edge fades and a keyboard-focusable region.
- Screenshot script for visual QA (`web/scripts/screenshots.mjs`).
- Key figures in context: the revenue and expenditure tiles say how much more or less per resident the unit has than similar units on average (or than the one other similar unit), linked to the comparison section, in all three editions.
- County map: a municipality's name appears on the map when it is hovered or focused (CSS only, no JavaScript), and a legend explains the marked unit and units without data.
- Sources tables (on each municipality page and on the sources page) become a stacked list on phones, one card per source with each value under its column name; screen readers still get a table.
- Layout check (`npm run layout`, in CI): every page of every edition at 360, 768 and 1280 px, failing on sideways scrolling. Submission screenshots in `docs/screenshots/`.
- Varaždin payments, fetched nightly from the city's export access point (`/Pretraga/GetExport/`, named by the city in Nov 2026): 12 months, about 2,300 payments a month, cleaned with the same privacy rules (`docs/varazdin-payments.md`).
- Data spot-check script (`scripts/spot_check.py`) and report (`docs/spot-check.md`): 50 figures on the pilot pages checked against their source files.
- Spec, task tracker (`TASKS.md`) and progress script.
- Repository layout, EUPL-1.2 licence and README (workflow and versioning, formerly in CONTRIBUTING.md, which is removed).
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

[Unreleased]: https://github.com/1212mauro/moja-opcina-u-brojkama/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/1212mauro/moja-opcina-u-brojkama/releases/tag/v0.4.0
