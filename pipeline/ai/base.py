"""Provider-agnostic AI analysis layer (Prompt 02).

The analysis pipeline depends only on this module (and the small interface
below), so adding a provider later — e.g. OpenAI proper — means dropping in
a new implementation of `analyze()`/`embed()` and registering it in
`build_providers`; nothing else changes.

Shared pieces live here: the system prompt, retry instruction, payload
builders and the provider factory.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol

SYSTEM_PROMPT = """You are a precise product-operations analyst labelling GitHub issues filed against the openai/codex repository.

Return exactly one JSON object matching the required schema. Semantics:

product_scope (read carefully):
- LOCKED PRINCIPLE: product_scope is determined by the affected user workflow/capability — never by the host application, bundle ID, repository location, or GitHub labels alone. Host metadata and labels may determine surface or platform, but they must not by themselves promote an issue to codex_core.
- "codex_core": the affected workflow directly concerns Codex App, Codex CLI, the IDE extension, Codex agent behavior, coding workflows, tools, execution, models, workspace, context, usage, or other Codex functionality.
- "codex_adjacent": the affected workflow explicitly involves Codex Remote, remote Codex tasks, or a ChatGPT/OpenAI surface used specifically to access or control a Codex workflow — including widgets/shortcuts to start a new remote Codex chat, remote task queues, cross-surface task behavior, and Codex mode selectors. Only if the issue is directly about the Codex execution system itself does codex_core apply instead.
- "out_of_scope": the affected workflow does not materially concern the Codex product or a Codex workflow (e.g. chatting in Chat conversations, pure ChatGPT features with no Codex connection) — even when the host app's bundle ID is com.openai.codex.
Example: an Android home-screen widget shortcut for starting a new remote Codex chat is codex_adjacent, not out_of_scope.
Example: a text-rendering bug in Chat conversations inside the unified desktop app is out_of_scope — the affected workflow is chatting, not a Codex workflow, regardless of the bundle ID.
Give scope_confidence (0-1) and a one-sentence scope_reason citing the affected workflow and what the issue actually mentions.

issue_type:
- "bug": something is broken or behaves incorrectly.
- "feature_request": requested new capability or enhancement.
- "ux_issue": works as designed but the experience is confusing or painful.
- "documentation": missing/unclear docs caused the problem.
- "other": none of the above fit.

surface: which Codex surface the issue is about (Codex App, CLI, IDE Extension, Web, Unknown).
platform: the reporter's operating system/device when stated; otherwise Unknown.

category: choose the single best fit from the enum (fixed top-level taxonomy).
subtopic: a short, specific noun phrase (<= 80 chars), e.g. "context window truncation" or "git staging area sync".

severity (AI-estimated) — calibrated rubric, follow it exactly:
- "critical": exceptional. Use only when there is strong evidence of severe data/state integrity risk, security/safety risk, uncontrollable material paid-resource loss, or the core system is effectively unusable with no practical workaround.
- "high": a core user task/workflow is blocked or repeatedly fails, but the impact is bounded and/or another workflow/workaround remains.
- "medium": meaningful degradation, friction, performance loss, or feature failure with a practical workaround or without complete task blockage.
- "low": cosmetic/localized UX issue, minor inconvenience, withdrawn/non-actionable report, or non-core impact.

Severity rules:
- User frustration does not determine severity.
- "App crashes" is not automatically critical.
- "Core workflow blocked" is normally high unless there is additional evidence satisfying the critical definition.
- Critical should be rare and require explicit evidence.

Calibration examples (from human audit — match the pattern, not the topic):
- Feature blocked but bounded (sandbox ACL failure #42958, extension sidebar regression #42969, compaction hang with later resume #43062) → high, NOT critical.
- Single-workflow failure with a workaround (fresh-thread resume fails #43053, browser download stops #42960, composer disappears after response #42963) → medium, NOT high.
- Cosmetic/localized glitch (reorder inserts stray reference #42972) or withdrawn/non-actionable report (#43050) → low, NOT medium.
- Silent state/data loss or uncontrollable paid-resource consumption (#42971 account switch silently discards completed turns; #43021 stuck task keeps consuming allowance and cannot be stopped) → critical.

sentiment: overall tone of the report (negative/neutral/positive/mixed).
summary: neutral 1-3 sentence restatement of the concrete problem/request.
user_scenario: what the user was trying to do (short, concrete).
user_impact: the consequence for the user (short, concrete).

confidence: your self-assessed confidence (0-1) in the whole labelling.
needs_review: set true when your confidence is below the min_confidence given in the input, or when the issue is ambiguous, mixed-topic, or lacks enough context.

Rules:
- Base everything only on the provided title, parsed metadata, labels and cleaned body.
- Interpret meaning only. Never invent counts, statistics, or reproduce long logs.
- Write all text fields in English."""

VALIDATION_RETRY_INSTRUCTIONS = (
    "Your previous output did not conform to the required JSON schema. "
    "Return the complete corrected JSON object, fixing exactly these "
    "problems:\n"
)


class AIConfigError(RuntimeError):
    """Raised when the configured AI provider is missing settings."""


class AIValidationError(RuntimeError):
    """Raised when model output never validates within the retry limit."""


@dataclass
class AnalysisResult:
    output: dict[str, Any]
    usage: dict[str, int] = field(default_factory=dict)
    attempts: int = 1


class ClassificationProvider(Protocol):
    name: str
    model: str

    def analyze(
        self, system_prompt: str, user_payload: str, schema: dict[str, Any]
    ) -> AnalysisResult: ...


class EmbeddingProvider(Protocol):
    model: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


def build_providers(env: Mapping[str, str | None]) -> ClassificationProvider:
    """Build the classification provider from AI_PROVIDER + its settings.

    Embeddings are deliberately wired separately — see
    pipeline.ai.embeddings.build_embedding_provider (embedding text never
    goes to the classification provider).
    """
    provider_name = (env.get("AI_PROVIDER") or "mimo").strip().lower()
    if provider_name == "mimo":
        from pipeline.ai.mimo import MiMoClassificationProvider

        api_key = (env.get("MIMO_API_KEY") or "").strip()
        if not api_key:
            raise AIConfigError(
                "AI_PROVIDER=mimo but MIMO_API_KEY is not set in .env.local"
            )
        base_url = (env.get("MIMO_BASE_URL") or "").strip() or None
        model = (
            env.get("MIMO_CLASSIFICATION_MODEL") or ""
        ).strip() or "mimo-v2.5-pro"
        return MiMoClassificationProvider(
            api_key=api_key, base_url=base_url, model=model
        )
    if provider_name == "openai":
        raise AIConfigError(
            "AI_PROVIDER=openai is not implemented yet: add "
            "pipeline/ai/openai.py with the same analyze()/embed() "
            "interface and register it in build_providers()."
        )
    raise AIConfigError(
        f"Unknown AI_PROVIDER {provider_name!r} (expected 'mimo'; "
        f"'openai' once implemented)"
    )


def build_user_payload(issue: Mapping[str, Any], min_confidence: float) -> str:
    """Title + parsed metadata + labels + cleaned body. Raw logs excluded."""
    labels = ", ".join(
        label.get("name", "") for label in issue.get("github_labels") or []
    ).strip()

    def field(name: str) -> str:
        return (issue.get(name) or "(not provided)").strip() or "(not provided)"

    return (
        f"min_confidence: {min_confidence}\n"
        f"title: {field('title')}\n"
        f"parsed_version: {field('parsed_version')}\n"
        f"parsed_subscription: {field('parsed_subscription')}\n"
        f"parsed_platform: {field('parsed_platform')}\n"
        f"parsed_actual: {field('parsed_actual')}\n"
        f"parsed_steps: {field('parsed_steps')}\n"
        f"parsed_expected: {field('parsed_expected')}\n"
        f"parsed_additional_info: {field('parsed_additional_info')}\n"
        f"github_labels: {labels or '(none)'}\n"
        f"body_clean:\n{field('body_clean')}"
    )


def semantic_text(row: Mapping[str, Any]) -> str:
    """Concise embedding input (docs/ARCHITECTURE.md §5)."""
    return (
        f"Title: {row.get('title', '')}\n"
        f"Summary: {row.get('summary', '')}\n"
        f"Scenario: {row.get('user_scenario') or ''}\n"
        f"Impact: {row.get('user_impact') or ''}\n"
        f"Category: {row.get('category', '')}\n"
        f"Subtopic: {row.get('subtopic', '')}"
    )


def vector_to_postgrest(vector: list[float]) -> str:
    """pgvector textual form for PostgREST; dimension must already match."""
    return "[" + ",".join(repr(float(x)) for x in vector) + "]"
