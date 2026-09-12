"""Xiaomi MiMo provider over its OpenAI-compatible endpoint.

MiMo's JSON mode is NOT assumed to guarantee strict JSON Schema adherence:
every completion is parsed and validated locally against the Signal schema
(config/ai_output.schema.json). Validation failures are retried with the
specific error included in the conversation; after the retry limit the
failure is raised so it is recorded — invalid data is never written.

Transport-level retry policy (request scheduling only, no semantic change):
429 / transient 5xx / connection errors are retried with exponential
backoff + jitter, honoring Retry-After when present; permanent 4xx errors
are never retried. All retry events are counted in provider stats.
"""

from __future__ import annotations

import random
import threading
import time
from typing import Any

import httpx
from openai import APIConnectionError, APIStatusError

from pipeline.ai.base import (
    AIValidationError,
    AnalysisResult,
    VALIDATION_RETRY_INSTRUCTIONS,
)
from pipeline.ai.schemas import extract_json, validate_output

DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
DEFAULT_MODEL = "mimo-v2.5-pro"


class MiMoClassificationProvider:
    name = "mimo"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        max_validation_retries: int = 2,
        timeout: float = 90.0,
        max_api_retries: int = 5,
        retry_base_delay: float = 1.0,
    ) -> None:
        from openai import OpenAI

        # SDK-internal retries are disabled: retry scheduling (429/5xx
        # counting, Retry-After, jitter) is owned by this provider.
        self._client = OpenAI(
            base_url=(base_url or DEFAULT_BASE_URL).rstrip("/"),
            api_key=api_key,
            max_retries=0,
            timeout=timeout,
        )
        self.model = model or DEFAULT_MODEL
        self.max_validation_retries = max_validation_retries
        self.max_api_retries = max_api_retries
        self.retry_base_delay = retry_base_delay
        self.stats = {
            "rate_limited_429": 0,
            "server_5xx": 0,
            "transient_errors": 0,
            "retries": 0,
        }
        self._stats_lock = threading.Lock()

    def _create(self, messages: list[dict[str, str]]):
        return self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )

    def _complete(
        self, messages: list[dict[str, str]]
    ) -> tuple[str, dict[str, int]]:
        last_error: Exception | None = None
        for attempt in range(1, self.max_api_retries + 1):
            try:
                resp = self._create(messages)
                usage = resp.usage
                return (
                    resp.choices[0].message.content or "",
                    {
                        "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                        "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
                    },
                )
            except APIStatusError as exc:
                status = getattr(exc, "status_code", 0) or 0
                if status == 429:
                    with self._stats_lock:
                        self.stats["rate_limited_429"] += 1
                elif status >= 500:
                    with self._stats_lock:
                        self.stats["server_5xx"] += 1
                else:
                    raise  # permanent 4xx — never retried blindly
                last_error = exc
            except (APIConnectionError, httpx.TransportError) as exc:
                with self._stats_lock:
                    self.stats["transient_errors"] += 1
                last_error = exc
            if attempt >= self.max_api_retries:
                break
            response = getattr(last_error, "response", None)
            retry_after = (
                response.headers.get("retry-after")
                if response is not None
                else None
            )
            try:
                delay = float(retry_after)  # Retry-After honored when sent
            except (TypeError, ValueError):
                delay = min(
                    30.0, self.retry_base_delay * (2 ** (attempt - 1))
                )
            delay *= 0.5 + random.random()  # jitter
            with self._stats_lock:
                self.stats["retries"] += 1
            time.sleep(delay)
        assert last_error is not None
        raise last_error

    def complete_json(
        self, system_prompt: str, user_payload: str
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Generic JSON-mode completion for post-membership cluster naming.

        Membership is already fixed by deterministic code when this is
        used — the model only names/summarizes (docs/ARCHITECTURE.md §5).
        Returns (parsed_object, usage); callers validate the keys.
        """
        from pipeline.ai.schemas import extract_json

        content, usage = self._complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload},
            ]
        )
        return extract_json(content), usage

    def analyze(
        self, system_prompt: str, user_payload: str, schema: dict[str, Any]
    ) -> AnalysisResult:
        system = (
            f"{system_prompt}\n\n"
            "The output object MUST validate against this JSON Schema:\n"
            f"{schema}"
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_payload},
        ]
        problems_seen: list[str] = []
        attempts = 0
        while attempts <= self.max_validation_retries:
            attempts += 1
            content, usage = self._complete(messages)
            try:
                output = extract_json(content)
            except ValueError as exc:
                problems = [str(exc)]
            else:
                problems = validate_output(output, schema)
                if not problems:
                    return AnalysisResult(
                        output=output, usage=usage, attempts=attempts
                    )
            problems_seen.append("; ".join(problems)[:500])
            messages = [
                *messages,
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": VALIDATION_RETRY_INSTRUCTIONS
                    + problems_seen[-1],
                },
            ]
        raise AIValidationError(
            f"output failed schema validation after {attempts} attempt(s); "
            f"last problem: {problems_seen[-1]}"
        )


class MiMoEmbeddingProvider:
    name = "mimo"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str = "",
        timeout: float = 90.0,
    ) -> None:
        from openai import OpenAI

        self._client = OpenAI(
            base_url=(base_url or DEFAULT_BASE_URL).rstrip("/"),
            api_key=api_key,
            max_retries=3,
            timeout=timeout,
        )
        if not model:
            raise ValueError("MIMO_EMBEDDING_MODEL is required for embeddings")
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = self._client.embeddings.create(model=self.model, input=texts)
        vectors = [item.embedding for item in resp.data]
        dims = {len(v) for v in vectors}
        if len(dims) != 1:
            raise ValueError(f"Inconsistent embedding dimensions: {dims}")
        return vectors
