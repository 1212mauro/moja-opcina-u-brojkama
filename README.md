# Moja općina u brojkama

One plain-language page for each of Croatia's 556 cities and municipalities: how the local government spends money, what it buys, and which public services are nearby — compared with similar municipalities in the same county.

- What and why: [SPEC.md](SPEC.md)
- Task breakdown and progress: [TASKS.md](TASKS.md)
- How we work: [CONTRIBUTING.md](CONTRIBUTING.md)
- Release history: [CHANGELOG.md](CHANGELOG.md)

## Repository layout

| Path | What it is |
| --- | --- |
| `pipeline/` | Python 3.12 pipeline: fetches open data, parses and joins it, writes JSON for the site |
| `web/` | Next.js website, exported as static files |
| `contract/` | The JSON data contract between pipeline and website (`schema.json`, examples) |
| `data/raw/` | Downloaded source files (git-ignored) |
| `docs/` | Source documentation and methodology |
| `scripts/` | Small helpers, e.g. `progress.py` |

## Running locally

Pipeline:

```bash
cd pipeline
python -m venv .venv
.venv/Scripts/activate        # Windows; on macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

Website:

```bash
cd web
npm install
npm run dev
```

`npm run build` writes the static site to `web/out/`.

## Changing the data contract

The pipeline's Pydantic models in `pipeline/src/opcina_pipeline/contract.py` are the single source of truth for the JSON the site reads. After changing them:

```bash
cd pipeline && opcina schema           # writes contract/schema.json
cd ../web && npm run gen:types         # writes src/lib/contract.ts
```

CI fails if either generated file is out of date.

## Licence

Code: [EUPL-1.2](LICENSE). Data comes from Croatian public bodies under the Croatian Open Licence or CC BY; each page credits its sources.
