"""Paths and configuration files."""

import tomllib
from dataclasses import dataclass
from functools import cache
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    """Nearest ancestor of ``start`` holding both ``contract/`` and ``pipeline/``.

    Works for editable installs and for a regular install run from inside a checkout.
    """
    for path in [start, *start.parents]:
        if (path / "contract").is_dir() and (path / "pipeline").is_dir():
            return path
    raise SystemExit("opcina: run this from inside the repository checkout")


REPO_ROOT = find_repo_root(Path.cwd().resolve())
CONFIG_DIR = REPO_ROOT / "pipeline" / "config"
RAW_DIR = REPO_ROOT / "data" / "raw"
SCHEMA_PATH = REPO_ROOT / "contract" / "schema.json"


@dataclass(frozen=True)
class Scope:
    county_name: str
    register_code: str
    nuts3: str
    postal_name: str
    census_name: str
    pilot_lau_codes: tuple[str, ...]


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    publisher: str
    page: str
    url: str
    licence: str
    file: str

    @property
    def path(self) -> Path:
        return RAW_DIR / self.file


def _read_toml(name: str) -> dict:
    return tomllib.loads((CONFIG_DIR / name).read_text(encoding="utf-8"))


@cache
def load_scope() -> Scope:
    raw = _read_toml("scope.toml")
    county = raw["county"]
    return Scope(
        county_name=county["name"],
        register_code=county["register_code"],
        nuts3=county["nuts3"],
        postal_name=county["postal_name"],
        census_name=county["census_name"],
        pilot_lau_codes=tuple(raw["pilots"]["lau_codes"]),
    )


@cache
def load_sources() -> dict[str, Source]:
    return {key: Source(key=key, **fields) for key, fields in _read_toml("sources.toml").items()}
