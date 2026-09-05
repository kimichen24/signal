"""Config consistency tests: taxonomy ↔ structured-output schema.

These tests keep config/taxonomy.json and config/ai_output.schema.json in
agreement so the AI extraction step can never emit values outside the locked
taxonomy (docs/DECISIONS.md #7).
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def test_taxonomy_file_has_expected_structure():
    taxonomy = _load("config/taxonomy.json")
    assert isinstance(taxonomy["version"], str) and taxonomy["version"], (
        "taxonomy.json 'version' must be a non-empty string"
    )
    for key in (
        "issue_types",
        "categories",
        "surfaces",
        "platforms",
        "severities",
        "action_types",
    ):
        assert key in taxonomy, f"taxonomy.json is missing '{key}'"
        assert isinstance(taxonomy[key], list) and taxonomy[key], (
            f"taxonomy.json '{key}' must be a non-empty list"
        )


def test_schema_enums_match_taxonomy():
    taxonomy = _load("config/taxonomy.json")
    schema = _load("config/ai_output.schema.json")
    props = schema["properties"]

    assert props["issue_type"]["enum"] == taxonomy["issue_types"]
    assert props["category"]["enum"] == taxonomy["categories"]
    assert props["surface"]["enum"] == taxonomy["surfaces"]
    assert props["platform"]["enum"] == taxonomy["platforms"]
    assert props["severity"]["enum"] == taxonomy["severities"]


def test_schema_required_fields_are_all_defined():
    schema = _load("config/ai_output.schema.json")
    missing = set(schema["required"]) - set(schema["properties"])
    assert not missing, f"required fields missing from properties: {missing}"


def test_schema_disallows_extra_properties():
    schema = _load("config/ai_output.schema.json")
    assert schema.get("additionalProperties") is False
