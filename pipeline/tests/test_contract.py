import json

from opcina_pipeline.cli import contract_schema
from opcina_pipeline.config import repo_root, schema_path
from opcina_pipeline.contract import MunicipalityPage


def test_example_page_matches_contract():
    example = repo_root() / "contract" / "examples" / "municipality-page.json"
    raw = json.loads(example.read_text(encoding="utf-8"))
    page = MunicipalityPage.model_validate(raw)
    assert page.population.total == 4250
    # Round-trips to the same camelCase JSON the website reads.
    assert page.model_dump(mode="json")["budget"]["revenueTotalEur"] == 5100000


def test_committed_schema_is_up_to_date():
    expected = contract_schema()
    committed = json.loads(schema_path().read_text(encoding="utf-8"))
    assert committed == expected, "run `opcina schema` and commit contract/schema.json"
