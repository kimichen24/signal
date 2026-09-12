"""Scope regression fixtures + locked scope principle (workflow-based)."""

import json
from pathlib import Path

from pipeline.ai.base import SYSTEM_PROMPT

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "scope_regression.json"

EXPECTED_SCOPES = {
    43065: "codex_core",
    43067: "codex_adjacent",
    43066: "codex_adjacent",
    43064: "codex_core",
    43063: "out_of_scope",
}


def _cases() -> dict[int, dict]:
    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return {case["issue_number"]: case for case in cases}


def test_fixture_matches_locked_regression_expectations():
    cases = _cases()
    for number, expected in EXPECTED_SCOPES.items():
        assert cases[number]["expected_scope"] == expected, (
            f"fixture for #{number} must expect {expected}"
        )


def test_fixture_has_remote_widget_regression_case():
    case = _cases()[43066]
    assert "remote" in case["title"].lower()


def test_system_prompt_encodes_remote_rule():
    lowered = SYSTEM_PROMPT.lower()
    assert "codex remote" in lowered
    assert "widget" in lowered
    assert "codex_adjacent, not out_of_scope" in lowered


def test_system_prompt_encodes_locked_scope_principle():
    lowered = SYSTEM_PROMPT.lower()
    assert "workflow/capability" in lowered
    assert "bundle id" in lowered
    assert "must not by themselves promote" in lowered
    # The bundle-ID regression example is spelled out.
    assert "text-rendering bug in chat conversations" in lowered
    assert "out_of_scope" in lowered
