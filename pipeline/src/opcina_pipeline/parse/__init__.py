"""Parsers: raw files in data/raw/ -> clean tables in data/interim/staging/ (see tables.py)."""

import importlib
import traceback

from opcina_pipeline.tables import write_table

# table -> "module:function" returning a DataFrame conformed to that table's schema
PARSERS = {
    "population": "population:build_population",
    "budget_line": "budget:build_budget_lines",
    "contract": "contracts:build_contracts",
    "payment": "payments:build_payments",
    "facility": "facilities:build_facilities",
}


def run_parsers(tables: list[str] | None = None) -> dict[str, str]:
    """Parse each table into staging. One failing parser does not stop the others."""
    results = {}
    for table in tables or list(PARSERS):
        module, function = PARSERS[table].split(":")
        try:
            build = getattr(importlib.import_module(f"opcina_pipeline.parse.{module}"), function)
            df = build()
            write_table(df, table)
            results[table] = f"{df.height} rows"
        except Exception as error:  # noqa: BLE001 - reported, and the gate keeps old data
            traceback.print_exc()
            results[table] = f"failed: {type(error).__name__}: {error}"
        print(f"{table:<12} {results[table]}")
    return results
