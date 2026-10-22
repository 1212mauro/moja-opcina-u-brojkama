"""Paths and configuration files."""

import tomllib
from dataclasses import dataclass, field
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


@cache
def repo_root() -> Path:
    """Resolved on first use, not at import, so importing helpers works from anywhere."""
    return find_repo_root(Path.cwd().resolve())


def config_path(name: str) -> Path:
    return repo_root() / "pipeline" / "config" / name


def schema_path() -> Path:
    return repo_root() / "contract" / "schema.json"


@dataclass(frozen=True)
class Scope:
    county_name: str
    register_code: str
    nuts3: str
    postal_name: str
    census_name: str
    pilot_lau_codes: tuple[str, ...]


SOURCE_FIELDS = ("title", "publisher", "page", "url", "licence", "file")


@dataclass(frozen=True)
class Source:
    key: str
    title: str
    publisher: str
    page: str
    url: str
    licence: str
    # What parsers read, relative to data/raw/: a file, or a folder for multi-file sources.
    file: str
    options: dict = field(default_factory=dict)  # fetcher-specific settings

    @property
    def path(self) -> Path:
        return repo_root() / "data" / "raw" / self.file


def _read_toml(name: str) -> dict:
    return tomllib.loads(config_path(name).read_text(encoding="utf-8"))


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
    sources = {}
    for key, fields in _read_toml("sources.toml").items():
        known = {name: fields[name] for name in SOURCE_FIELDS}
        options = {name: value for name, value in fields.items() if name not in SOURCE_FIELDS}
        sources[key] = Source(key=key, **known, options=options)
    return sources
