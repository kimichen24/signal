"""Tests for MiMo transport retry policy: 429/5xx backoff with jitter,
Retry-After, permanent-4xx no-retry, and stats counting. No network."""

import json

import httpx
import pytest
from openai import APIConnectionError, APIStatusError

from pipeline.ai.base import AIValidationError
from pipeline.ai.mimo import MiMoClassificationProvider
from pipeline.ai.schemas import load_analysis_schema
from tests.test_ai_schemas import VALID_OUTPUT


class FakeResp:
    def __init__(self, content):
        message = type("M", (), {"content": content})()
        self.choices = [type("C", (), {"message": message})()]
        self.usage = type("U", (), {"prompt_tokens": 3, "completion_tokens": 4})()


class RetryStub(MiMoClassificationProvider):
    """No HTTP client; replays scripted create() outcomes."""

    def __init__(self, outcomes, max_api_retries=5, max_validation_retries=2):
        import threading

        self.max_validation_retries = max_validation_retries

        self.model = "mimo-v2.5-pro"
        self.max_validation_retries = 2
        self.max_api_retries = max_api_retries
        self.retry_base_delay = 0.0
        self.stats = {
            "rate_limited_429": 0,
            "server_5xx": 0,
            "transient_errors": 0,
            "retries": 0,
        }
        self._stats_lock = threading.Lock()
        self.outcomes = list(outcomes)
        self.calls = 0
        self.last_messages = None

    def _create(self, messages):
        self.calls += 1
        self.last_messages = messages
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        # Strings are already JSON content — never double-encode.
        content = outcome if isinstance(outcome, str) else json.dumps(outcome)
        return FakeResp(content)


def _status_error(code: int, retry_after: str | None = None):
    request = httpx.Request("POST", "https://api.test/v1/chat/completions")
    headers = {"retry-after": retry_after} if retry_after else {}
    response = httpx.Response(code, headers=headers, request=request)
    return APIStatusError("boom", response=response, body=None)


class TestTransportRetryPolicy:
    def test_success_first_try(self):
        import json

        stub = RetryStub([json.dumps(VALID_OUTPUT)])
        result = stub.analyze("sys", "user", load_analysis_schema())
        assert result.output == VALID_OUTPUT
        assert stub.calls == 1
        assert stub.stats["retries"] == 0

    def test_429_retried_then_succeeds(self, monkeypatch):
        import json

        slept = []
        monkeypatch.setattr(
            "pipeline.ai.mimo.time.sleep", lambda s: slept.append(s)
        )
        stub = RetryStub(
            [_status_error(429, retry_after="0"), json.dumps(VALID_OUTPUT)]
        )
        result = stub.analyze("sys", "user", load_analysis_schema())
        assert result.attempts == 1  # attempts = validation attempts
        assert stub.calls == 2
        assert stub.stats["rate_limited_429"] == 1
        assert stub.stats["retries"] == 1
        assert slept  # backoff was applied

    def test_5xx_counted_and_retryable(self, monkeypatch):
        import json

        slept = []
        monkeypatch.setattr(
            "pipeline.ai.mimo.time.sleep", lambda s: slept.append(s)
        )
        stub = RetryStub(
            [_status_error(503), _status_error(500), json.dumps(VALID_OUTPUT)]
        )
        result = stub.analyze("sys", "user", load_analysis_schema())
        assert stub.stats["server_5xx"] == 2
        assert stub.calls == 3
        assert result.output == VALID_OUTPUT

    def test_permanent_4xx_never_retried(self):
        stub = RetryStub([_status_error(401)])
        with pytest.raises(APIStatusError):
            stub.analyze("sys", "user", load_analysis_schema())
        assert stub.calls == 1
        assert stub.stats["retries"] == 0

    def test_connection_error_retried(self, monkeypatch):
        request = httpx.Request("POST", "https://api.test/v1/chat/completions")
        slept = []
        monkeypatch.setattr(
            "pipeline.ai.mimo.time.sleep", lambda s: slept.append(s)
        )
        stub = RetryStub(
            [
                APIConnectionError(request=request),
                json.dumps(VALID_OUTPUT),
            ]
        )
        result = stub.analyze("sys", "user", load_analysis_schema())
        assert stub.stats["transient_errors"] == 1
        assert stub.stats["retries"] == 1
        assert result.output == VALID_OUTPUT

    def test_retry_cap_raises(self, monkeypatch):
        slept = []
        monkeypatch.setattr(
            "pipeline.ai.mimo.time.sleep", lambda s: slept.append(s)
        )
        stub = RetryStub(
            [_status_error(429)] * 6, max_api_retries=5
        )
        with pytest.raises(APIStatusError):
            stub.analyze("sys", "user", load_analysis_schema())
        assert stub.calls == 5  # capped

    def test_validation_failure_is_not_a_transport_retry(self):
        # Schema-invalid JSON never triggers transport retries; the
        # validation retry loop is separate and also capped.
        stub = RetryStub(["not json", "still bad", "nope"], max_validation_retries=2)
        with pytest.raises(AIValidationError):
            stub.analyze("sys", "user", load_analysis_schema())
        assert stub.calls == 3
        assert stub.stats["retries"] == 0
