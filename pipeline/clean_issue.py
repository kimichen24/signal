"""Deterministic Stage 2 (parse) + Stage 3 (clean) for Codex issue bodies.

- parse_issue_body(): extract heading-based fields into the parsed_* columns
  using keyword rules over `###`/`##` headings. No LLM involved.
- build_body_clean(): collapse oversized fenced code blocks and repeated log
  lines for LLM input. body_raw is never modified — cleaning only produces
  body_clean.
"""

from __future__ import annotations

import re

NO_RESPONSE_MARKERS = {
    "_no response_",
    "no response",
    "n/a",
    "na",
    "none",
    "unknown",
}

# Ordered keyword rules: the first rule whose any-keyword matches a
# normalized heading wins. Wording drift across template edits is tolerated.
_FIELD_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("parsed_additional_info", ("additional information", "additional context")),
    ("parsed_expected", ("expected behavior", "expected result")),
    ("parsed_steps", ("steps", "reproduce", "reproduction")),
    ("parsed_subscription", ("subscription",)),
    ("parsed_platform", ("platform", "operating system")),
    ("parsed_version", ("version", "variant", "build")),
    (
        "parsed_actual",
        (
            "issue are you seeing",
            "feature would you like",
            "what happened",
            "describe the bug",
        ),
    ),
]

# Template field headings are h3/h4 (`### What platform ...?`); h1/h2 lines
# are body content sections (e.g. "## Problem" inside feature requests) and
# must not terminate a field.
_HEADING_RE = re.compile(r"^#{3,4}\s+(.*?)\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_WS_RE = re.compile(r"\s+")


def _normalize_heading(heading: str) -> str:
    lowered = heading.lower()
    for curly in ("\u201c", "\u201d", "\u2018", "\u2019"):
        lowered = lowered.replace(curly, "'")
    return _WS_RE.sub(" ", lowered).strip(" \t-—:?")


def _match_field(heading: str) -> str | None:
    normalized = _normalize_heading(heading)
    for field, keywords in _FIELD_RULES:
        if any(keyword in normalized for keyword in keywords):
            return field
    return None


def _normalize_value(text: str) -> str | None:
    value = text.strip()
    if not value:
        return None
    if value.lower() in NO_RESPONSE_MARKERS:
        return None
    return value


def parse_issue_body(body: str | None) -> dict[str, str | None]:
    """Extract parsed_* fields from heading sections. Never raises on text."""
    fields: dict[str, str | None] = {
        "parsed_version": None,
        "parsed_subscription": None,
        "parsed_platform": None,
        "parsed_actual": None,
        "parsed_steps": None,
        "parsed_expected": None,
        "parsed_additional_info": None,
    }
    if not body:
        return fields

    current_field: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if current_field is not None and fields[current_field] is None:
            fields[current_field] = _normalize_value("\n".join(buffer))
        buffer = []

    for line in body.splitlines():
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            flush()
            current_field = _match_field(heading_match.group(1))
            continue
        if current_field is not None:
            buffer.append(line)
    flush()
    return fields


def build_body_clean(
    body: str | None,
    *,
    max_code_lines: int = 40,
    max_repeat: int = 3,
    max_total_chars: int = 8000,
) -> str | None:
    """Cleaned text for semantic analysis: collapse huge code blocks and
    repeated lines, then cap total length. Raw text stays in body_raw."""
    if body is None:
        return None

    out_lines: list[str] = []
    fence_marker: str | None = None
    fence_lines: list[str] = []

    def flush_fence() -> None:
        nonlocal fence_marker, fence_lines
        if fence_marker is None:
            return
        if len(fence_lines) > max_code_lines:
            out_lines.append(f"[code block removed: {len(fence_lines)} lines]")
        else:
            out_lines.append(fence_marker)
            out_lines.extend(fence_lines)
            out_lines.append(fence_marker)
        fence_marker = None
        fence_lines = []

    for line in body.splitlines():
        fence_match = _FENCE_RE.match(line)
        if fence_marker is None:
            if fence_match:
                flush_fence()
                fence_marker = fence_match.group(1)
            else:
                out_lines.append(line)
        else:
            if fence_match and fence_match.group(1)[0] == fence_marker[0]:
                flush_fence()
            else:
                fence_lines.append(line)
    flush_fence()

    # Collapse runs of identical non-empty lines (repeated logs/headers).
    collapsed: list[str] = []
    run_value: str | None = None
    run_count = 0

    def flush_run() -> None:
        nonlocal run_value, run_count
        if run_value is None:
            return
        collapsed.append(run_value)
        if run_count > max_repeat:
            collapsed.append(f"[repeated {run_count} times]")
        run_value = None
        run_count = 0

    for line in out_lines:
        stripped = line.strip()
        if stripped and stripped == run_value:
            run_count += 1
            continue
        flush_run()
        run_value = stripped
        run_count = 1
    flush_run()

    clean = "\n".join(collapsed).strip()
    if len(clean) > max_total_chars:
        clean = clean[:max_total_chars].rstrip() + "\n[truncated]"
    return clean or None
