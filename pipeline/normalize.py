"""Deterministic normalization of AI classification results (Prompt 02).

Precedence for fields determinable from GitHub metadata:

    parsed metadata > strong GitHub labels > LLM inference > Unknown

At minimum this applies to `platform` and (where strongly indicated)
`surface`. The LLM result is preserved untouched in `model_output` (see
migration 0003); the typed columns hold the normalized final values.

Pure functions only — the LLM never overrides deterministic facts.
"""

from __future__ import annotations

import re
from typing import Any

_PLATFORM_TEXT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"windows|winnt|win32|win64|win10|win11", re.IGNORECASE), "Windows"),
    (re.compile(r"macos|mac os|os x|darwin|\bmac\b", re.IGNORECASE), "macOS"),
    (re.compile(r"linux|ubuntu|debian|fedora|arch|centos|rhel|mint", re.IGNORECASE), "Linux"),
    (re.compile(r"android", re.IGNORECASE), "Android"),
    (re.compile(r"\bios\b|iphone|ipados|ipad", re.IGNORECASE), "iOS"),
)

# Strong labels: substring tokens inside label names like "windows-os".
_PLATFORM_LABEL_TOKENS: tuple[tuple[str, str], ...] = (
    ("windows", "Windows"),
    ("macos", "macOS"),
    ("mac-os", "macOS"),
    ("linux", "Linux"),
    ("android", "Android"),
    ("ios", "iOS"),
)

# Strong labels that identify the Codex surface directly.
_SURFACE_LABELS: dict[str, str] = {
    "app": "Codex App",
    "desktop": "Codex App",
    "cli": "CLI",
    "ide-extension": "IDE Extension",
    "ide_extension": "IDE Extension",
    "vscode": "IDE Extension",
    "web": "Web",
}


def platform_from_parsed(parsed_platform: str | None) -> str | None:
    if not parsed_platform:
        return None
    for pattern, platform in _PLATFORM_TEXT_PATTERNS:
        if pattern.search(parsed_platform):
            return platform
    return None


def _label_names(labels: Any) -> list[str]:
    names: list[str] = []
    for label in labels or []:
        if isinstance(label, dict) and label.get("name"):
            names.append(str(label["name"]).strip().lower())
        elif isinstance(label, str):
            names.append(label.strip().lower())
    return names


def platform_from_labels(labels: Any) -> str | None:
    for name in _label_names(labels):
        for token, platform in _PLATFORM_LABEL_TOKENS:
            if token in name:
                return platform
    return None


def surface_from_labels(labels: Any) -> str | None:
    for name in _label_names(labels):
        if name in _SURFACE_LABELS:
            return _SURFACE_LABELS[name]
    return None


def apply_deterministic_overrides(
    output: dict[str, Any], issue: dict[str, Any]
) -> dict[str, Any]:
    """Return a copy of the model output with deterministic fields enforced.

    Deterministic sources win whenever they resolve to a value; the LLM
    result only stands when nothing deterministic is available.
    """
    final = dict(output)
    labels = issue.get("github_labels")
    deterministic_platform = platform_from_parsed(
        issue.get("parsed_platform")
    ) or platform_from_labels(labels)
    deterministic_surface = surface_from_labels(labels)
    if deterministic_platform:
        final["platform"] = deterministic_platform
    if deterministic_surface:
        final["surface"] = deterministic_surface
    return final
