# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/); see [CONTRIBUTING.md](CONTRIBUTING.md#versioning) for how versions map to milestones.

## [Unreleased]

### Added

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

### Changed

- Procurement: the data.gov.hr file the spec cites as national is Grad Ivanec's own register; national access goes through eojn.hr (see `docs/sources.md`).
