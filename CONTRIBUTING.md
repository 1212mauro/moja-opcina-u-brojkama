# Contributing

## Workflow

1. Pick a task from [TASKS.md](TASKS.md) and claim it: `— 🚧 @yourname`.
2. Work on a branch per task section, named after the section or task ID:
   `feat/A-project-setup`, `feat/C2-budget-parser`, `fix/D5-chart-labels`.
3. Prefix every commit message with the task ID: `C2: parse MinFin budget XLSX`.
4. Tick the task in TASKS.md (`- [x]`) in the same PR that finishes it.
5. Open a pull request into `main`. CI must be green before merging; merge with a merge commit so each section stays visible in history.

## Versioning

- The project follows [Semantic Versioning](https://semver.org/). Before 1.0, minor versions mark datathon and v1 milestones:

  | Version | Milestone |
  | --- | --- |
  | 0.1.0 | MVP-1 Data in hand |
  | 0.2.0 | MVP-2 First complete page |
  | 0.3.0 | MVP-3 All pilots, all features |
  | 0.4.0 | MVP-4 Datathon submission |
  | 1.0.0 | Production v1 public launch |

- Patch versions (0.2.1 …) are for fixes between milestones.
- At each milestone: update [CHANGELOG.md](CHANGELOG.md), bump the version in `pipeline/pyproject.toml`, `pipeline/src/opcina_pipeline/__init__.py` and `web/package.json`, then tag the merge commit on `main`:

  ```bash
  git tag -a v0.1.0 -m "MVP-1 Data in hand"
  git push origin v0.1.0
  ```

## Definition of done

See [TASKS.md → Definition of done](TASKS.md#definition-of-done).

## Team roles

Fill in at the first check-in:

| Area | Owner |
| --- | --- |
| Data sources and pipeline (B, C) | |
| Frontend (D) | |
| Language and accessibility (E) | |
| Deployment (F) | |
| Testing and video (G) | |

Weekly check-in: (day and time to be agreed).
