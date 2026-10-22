import json

from opcina_pipeline.cli import contract_schema
from opcina_pipeline.config import REPO_ROOT, SCHEMA_PATH
from opcina_pipeline.contract import MunicipalityPage

EXAMPLE = REPO_ROOT / "contract" / "examples" / "municipality-page.json"


def test_example_page_matches_contract():
    raw = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    page = MunicipalityPage.model_validate(raw)
    assert page.population.total == 4250
    # Round-trips to the same camelCase JSON the website reads.
    assert page.model_dump(mode="json")["budget"]["revenueTotalEur"] == 5100000


def test_committed_schema_is_up_to_date():
    expected = contract_schema()
    committed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert committed == expected, "run `opcina schema` and commit contract/schema.json"
