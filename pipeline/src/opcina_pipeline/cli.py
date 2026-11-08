"""Command-line entry point: ``opcina <command>``."""

import argparse
import json
from pathlib import Path

import polars as pl

from opcina_pipeline import boundaries, master, postcodes
from opcina_pipeline.config import config_path, load_scope, load_sources, repo_root, schema_path
from opcina_pipeline.contract import Contract
from opcina_pipeline.export import export
from opcina_pipeline.fetch import blocking_failures, run_fetch
from opcina_pipeline.parse import PARSERS, run_parsers
from opcina_pipeline.quality import run_gate

MASTER_CSV = "municipalities.csv"
POSTCODES_CSV = "postcodes.csv"


def contract_schema() -> dict:
    """JSON Schema of the contract, without per-field titles.

    Field titles make json-schema-to-typescript emit a type alias per field;
    model titles are kept so every model becomes one named interface.
    """
    schema = Contract.model_json_schema(mode="serialization", by_alias=True)
    for model in [schema, *schema["$defs"].values()]:
        for prop in model.get("properties", {}).values():
            prop.pop("title", None)
    return schema


def write_schema(path: Path | None = None) -> None:
    path = path or schema_path()
    schema = contract_schema()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"wrote {path.relative_to(repo_root())}")


def write_csv(df: pl.DataFrame, path: Path) -> None:
    # polars writes "\n" line endings on every platform, so the file is stable in git.
    df.write_csv(path)
    print(f"wrote {path.relative_to(repo_root())} ({df.height} rows)")


def build_master() -> pl.DataFrame:
    sources = load_sources()
    df = master.build_master(
        master.read_register(sources["minfin_budget_users"].path),
        master.read_lau(sources["lau_codes"].path),
        load_scope(),
    )
    write_csv(df, config_path(MASTER_CSV))
    return df


def build_postcodes() -> None:
    sources = load_sources()
    df = postcodes.build_postcodes(
        postcodes.read_posta(sources["postcodes"].path),
        postcodes.read_census_settlements(sources["dzs_settlements"].path),
        pl.read_csv(config_path(MASTER_CSV), infer_schema_length=0),
        load_scope(),
        postcodes.read_overrides(),
    )
    write_csv(df, config_path(POSTCODES_CSV))


def build_boundaries() -> None:
    dest = repo_root() / "web" / "public" / "data" / "boundaries.geojson"
    result = boundaries.write_boundaries(
        load_sources()["dgu_boundaries"].path,
        pl.read_csv(config_path(MASTER_CSV), infer_schema_length=0),
        dest,
    )
    print(f"wrote {dest.relative_to(repo_root())} ({len(result.features)} features)")


def gate(accept: set[str] = frozenset()) -> bool:
    """Run the quality gate and print the verdicts; True when every table passed."""
    results = run_gate(accept=accept)
    for r in results:
        verdict = "published" if r.passed else "KEPT PREVIOUS: " + "; ".join(r.problems)
        print(f"{r.table:<12} {r.rows:>8} rows  {verdict}")
    return all(r.passed for r in results)


def main() -> None:
    parser = argparse.ArgumentParser(prog="opcina", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("schema", help="write the data contract to contract/schema.json")
    commands.add_parser("master", help="build config/municipalities.csv from raw files")
    commands.add_parser("postcodes", help="build config/postcodes.csv from raw files")
    commands.add_parser("boundaries", help="simplify boundaries for the website")
    fetch_cmd = commands.add_parser("fetch", help="download every source into data/raw/")
    fetch_cmd.add_argument("sources", nargs="*", help="source keys (default: all)")
    parse_cmd = commands.add_parser("parse", help="parse raw files into data/interim/staging/")
    parse_cmd.add_argument("tables", nargs="*", help=f"any of {', '.join(PARSERS)} (default: all)")
    gate_cmd = commands.add_parser("gate", help="check staged tables, publish the ones that pass")
    gate_cmd.add_argument(
        "--accept",
        nargs="+",
        default=[],
        metavar="TABLE",
        help="accept an expected jump in row count for these tables (other checks still apply)",
    )
    commands.add_parser("export", help="write the website's JSON from published tables")
    build_cmd = commands.add_parser("build", help="parse + gate + export")
    build_cmd.add_argument("--accept", nargs="+", default=[], metavar="TABLE", help="see gate")

    args = parser.parse_args()
    if args.command == "schema":
        write_schema()
    elif args.command == "master":
        build_master()
    elif args.command == "postcodes":
        build_postcodes()
    elif args.command == "boundaries":
        build_boundaries()
    elif args.command == "fetch":
        outcomes = run_fetch(args.sources or None)
        # A source that is down but has recent good files only warns (see blocking_failures).
        blocking = blocking_failures(outcomes, repo_root() / "data" / "raw" / "source_runs.jsonl")
        for key, reason in blocking.items():
            print(f"error: {key} failed and blocks the run: {reason}")
        if blocking:
            raise SystemExit(1)
    elif args.command == "parse":
        unknown = sorted(set(args.tables) - set(PARSERS))
        if unknown:
            parser.error(f"unknown tables {unknown}; choose from {', '.join(PARSERS)}")
        if any(r.startswith("failed") for r in run_parsers(args.tables or None).values()):
            raise SystemExit(1)
    elif args.command == "gate":
        if not gate(set(args.accept)):
            raise SystemExit(1)
    elif args.command == "export":
        print(export())
    elif args.command == "build":
        parsed = run_parsers()
        passed = gate(set(args.accept))  # failing tables keep their last published version...
        print(export())  # ...and every table that passed is still exported
        if not passed or any(r.startswith("failed") for r in parsed.values()):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
