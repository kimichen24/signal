"""Schema loading and local validation for AI outputs (provider-independent).

Providers must never be trusted to emit schema-valid JSON on their own:
every output is parsed here and validated against
config/ai_output.schema.json before it can be written to the database.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

# pipeline/ai/schemas.py → parents[2] is the repository root.
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
SCHEMA_PATH = CONFIG_DIR / "ai_output.schema.json"
TAXONOMY_PATH = CONFIG_DIR / "taxonomy.json"


@lru_cache(maxsize=1)
def load_analysis_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_taxonomy() -> dict[str, Any]:
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def validate_output(output: Any, schema: dict[str, Any]) -> list[str]:
    """Return human-readable validation problems (empty list = valid)."""
    errors = sorted(
        Draft202012Validator(schema).iter_errors(output),
        key=lambda e: list(e.path),
    )
    return [
        f"{'/'.join(map(str, error.path)) or '(root)'}: {error.message}"
        for error in errors[:5]
    ]


def extract_json(text: str) -> dict[str, Any]:
    """Parse a JSON object out of a model message.

    Tolerates markdown code fences and stray prose around the object, which
    OpenAI-compatible providers emit even in JSON mode.
    """
    if not text or not text.strip():
        raise ValueError("model returned an empty message")
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.lower().startswith("json"):
            candidate = candidate[4:]
        candidate = candidate.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(
                f"no JSON object found in model output: {text[:200]!r}"
            ) from None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"model output is not valid JSON: {exc}; got {text[:200]!r}"
            ) from exc
    if not isinstance(parsed, dict):
        raise ValueError(
            f"expected a JSON object, got {type(parsed).__name__}"
        )
    return parsed
