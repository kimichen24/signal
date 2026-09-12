"""Tests for the MiMo provider retry loop and the provider factory.

No network: the OpenAI client is never called because _complete is stubbed.
"""

import pytest

from pipeline.ai.base import (
    AIConfigError,
    AIValidationError,
    build_providers,
)
from pipeline.ai.mimo import MiMoClassificationProvider
from pipeline.ai.schemas import load_analysis_schema
from tests.test_ai_schemas import VALID_OUTPUT


class StubMiMoProvider(MiMoClassificationProvider):
    """Stub that skips the OpenAI client and replays canned completions."""

    def __init__(self, responses: list[str], max_validation_retries: int = 2):
        self.model = "mimo-v2.5-pro"
        self.max_validation_retries = max_validation_retries
        self.responses = list(responses)
        self.call_messages: list[list[dict[str, str]]] = []

    def _complete(self, messages):
        self.call_messages.append(messages)
        return self.responses.pop(0), {"input_tokens": 1, "output_tokens": 2}


class TestAnalyzeRetryLoop:
    def test_valid_output_first_try(self):
        import json

        provider = StubMiMoProvider([json.dumps(VALID_OUTPUT)])
        result = provider.analyze("sys", "user", load_analysis_schema())
        assert result.output == VALID_OUTPUT
        assert result.attempts == 1
        assert result.usage["input_tokens"] == 1

    def test_retries_with_validation_error_included(self):
        import json

        broken = {k: v for k, v in VALID_OUTPUT.items() if k != "severity"}
        provider = StubMiMoProvider(
            [json.dumps(broken), json.dumps(VALID_OUTPUT)]
        )
        result = provider.analyze("sys", "user", load_analysis_schema())
        assert result.attempts == 2
        assert result.output == VALID_OUTPUT
        # The retry conversation includes the assistant output + the error.
        retry_messages = provider.call_messages[1]
        assert any(m["role"] == "assistant" for m in retry_messages)
        assert any("did not conform" in m["content"] for m in retry_messages)

    def test_raises_after_retry_limit_instead_of_accepting_invalid(self):
        import json

        broken = {k: v for k, v in VALID_OUTPUT.items() if k != "severity"}
        provider = StubMiMoProvider(
            [json.dumps(broken)] * 3, max_validation_retries=2
        )
        with pytest.raises(AIValidationError):
            provider.analyze("sys", "user", load_analysis_schema())
        assert len(provider.call_messages) == 3  # 1 initial + 2 retries

    def test_retries_when_output_is_not_json(self):
        provider = StubMiMoProvider(
            ["I cannot answer that", '{"also": "bad"}', "zzz"],
            max_validation_retries=2,
        )
        with pytest.raises(AIValidationError):
            provider.analyze("sys", "user", load_analysis_schema())


class TestBuildProviders:
    def test_unknown_provider_rejected(self):
        with pytest.raises(AIConfigError):
            build_providers({"AI_PROVIDER": "anthropic"})

    def test_mimo_requires_api_key(self):
        with pytest.raises(AIConfigError):
            build_providers({"AI_PROVIDER": "mimo", "MIMO_API_KEY": ""})

    def test_mimo_classification_builds_without_embedding(self):
        # Embeddings are wired separately (pipeline.ai.embeddings) —
        # build_providers returns the classification provider only.
        provider = build_providers(
            {"AI_PROVIDER": "mimo", "MIMO_API_KEY": "mk-test"}
        )
        assert provider.name == "mimo"
        assert provider.model == "mimo-v2.5-pro"
