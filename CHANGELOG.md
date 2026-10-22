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

### Changed

- Procurement: the data.gov.hr file the spec cites as national is Grad Ivanec's own register; national access goes through eojn.hr (see `docs/sources.md`).
