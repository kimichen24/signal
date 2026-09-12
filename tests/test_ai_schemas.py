"""Tests for the provider-agnostic AI schema helpers (pipeline/ai/schemas)."""

import pytest

from pipeline.ai.schemas import extract_json, load_analysis_schema, validate_output

VALID_OUTPUT = {
    "issue_type": "bug",
    "surface": "CLI",
    "platform": "Windows",
    "category": "CLI",
    "subtopic": "startup crash",
    "user_scenario": "Tried to run codex in a repo",
    "user_impact": "Could not start a session",
    "severity": "high",
    "sentiment": "negative",
    "summary": "Codex CLI crashes on startup on Windows.",
    "confidence": 0.8,
    "needs_review": False,
    "product_scope": "codex_core",
    "scope_confidence": 0.9,
    "scope_reason": "Directly concerns the Codex CLI.",
}


class TestExtractJson:
    def test_plain_object(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_markdown_fenced(self):
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_prose_around_object(self):
        assert extract_json('Here you go:\n{"a": 1}\nDone.') == {"a": 1}

    def test_rejects_empty_and_non_object(self):
        with pytest.raises(ValueError):
            extract_json("")
        with pytest.raises(ValueError):
            extract_json("[1, 2, 3]")
        with pytest.raises(ValueError):
            extract_json("no json here at all")


class TestValidateOutput:
    def test_valid_output_passes(self):
        problems = validate_output(VALID_OUTPUT, load_analysis_schema())
        assert problems == []

    def test_missing_required_field_flagged(self):
        broken = {k: v for k, v in VALID_OUTPUT.items() if k != "product_scope"}
        problems = validate_output(broken, load_analysis_schema())
        assert any("product_scope" in p for p in problems)

    def test_invalid_enum_flagged(self):
        problems = validate_output(
            {**VALID_OUTPUT, "severity": "catastrophic"},
            load_analysis_schema(),
        )
        assert any("severity" in p for p in problems)

    def test_out_of_range_confidence_flagged(self):
        problems = validate_output(
            {**VALID_OUTPUT, "confidence": 1.5}, load_analysis_schema()
        )
        assert any("confidence" in p for p in problems)

    def test_scope_fields_are_validated(self):
        problems = validate_output(
            {
                **VALID_OUTPUT,
                "product_scope": "everything",
                "scope_confidence": "high",
            },
            load_analysis_schema(),
        )
        assert any("product_scope" in p for p in problems)
        assert any("scope_confidence" in p for p in problems)
