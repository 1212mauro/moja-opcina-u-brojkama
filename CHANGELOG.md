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

### Changed

- Procurement: the data.gov.hr file the spec cites as national is Grad Ivanec's own register; national access goes through eojn.hr (see `docs/sources.md`).
