"""Command-line entry point: ``opcina <command>``."""

import argparse
import json
from pathlib import Path

from opcina_pipeline.contract import Contract

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = REPO_ROOT / "contract" / "schema.json"


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


def write_schema(path: Path = SCHEMA_PATH) -> None:
    schema = contract_schema()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"wrote {path.relative_to(REPO_ROOT)}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="opcina", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("schema", help="write the data contract to contract/schema.json")

    args = parser.parse_args()
    if args.command == "schema":
        write_schema()


if __name__ == "__main__":
    main()
