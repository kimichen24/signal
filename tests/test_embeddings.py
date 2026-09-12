"""Tests for the independent embedding provider factory (no model loads)."""

import pytest

from pipeline.ai import embeddings as embeddings_module
from pipeline.ai.base import build_providers
from pipeline.ai.embeddings import EmbeddingConfigError, build_embedding_provider
from pipeline.ai.mimo import MiMoEmbeddingProvider


class TestBuildProvidersClassificationOnly:
    def test_mimo_classification_without_embedding(self):
        provider = build_providers(
            {"AI_PROVIDER": "mimo", "MIMO_API_KEY": "mk-test"}
        )
        assert provider.name == "mimo"
        assert provider.model == "mimo-v2.5-pro"

    def test_mimo_requires_api_key(self):
        with pytest.raises(Exception):
            build_providers({"AI_PROVIDER": "mimo", "MIMO_API_KEY": ""})


class TestBuildEmbeddingProvider:
    def test_none_returns_none(self):
        assert build_embedding_provider({"EMBEDDING_PROVIDER": "none"}) is None
        assert build_embedding_provider({}) is None

    def test_unknown_provider_rejected(self):
        with pytest.raises(EmbeddingConfigError):
            build_embedding_provider({"EMBEDDING_PROVIDER": "openai"})

    def test_mimo_branch_requires_key_and_model(self):
        with pytest.raises(EmbeddingConfigError):
            build_embedding_provider(
                {"EMBEDDING_PROVIDER": "mimo", "MIMO_API_KEY": "k"}
            )

    def test_mimo_branch_builds(self):
        provider = build_embedding_provider(
            {
                "EMBEDDING_PROVIDER": "mimo",
                "MIMO_API_KEY": "k",
                "MIMO_EMBEDDING_MODEL": "mimo-embed",
            }
        )
        assert isinstance(provider, MiMoEmbeddingProvider)
        assert provider.model == "mimo-embed"

    def test_local_branch_dispatches_with_env_config(self, monkeypatch):
        calls = {}

        class StubLocal:
            def __init__(self, model_name, dimension, prefix=""):
                calls["model_name"] = model_name
                calls["dimension"] = dimension
                calls["prefix"] = prefix

        monkeypatch.setattr(
            embeddings_module, "LocalEmbeddingProvider", StubLocal
        )
        provider = build_embedding_provider(
            {
                "EMBEDDING_PROVIDER": "local",
                "LOCAL_EMBEDDING_MODEL": "intfloat/multilingual-e5-small",
                "EMBEDDING_DIMENSION": "384",
                "LOCAL_EMBEDDING_PREFIX": "passage:",
            }
        )
        assert isinstance(provider, StubLocal)
        assert calls == {
            "model_name": "intfloat/multilingual-e5-small",
            "dimension": 384,
            "prefix": "passage:",
        }

    def test_local_defaults(self, monkeypatch):
        calls = {}

        class StubLocal:
            def __init__(self, model_name, dimension, prefix=""):
                calls.update(
                    model_name=model_name, dimension=dimension, prefix=prefix
                )

        monkeypatch.setattr(
            embeddings_module, "LocalEmbeddingProvider", StubLocal
        )
        build_embedding_provider({"EMBEDDING_PROVIDER": "local"})
        assert calls == {
            "model_name": "intfloat/multilingual-e5-small",
            "dimension": 384,
            "prefix": "",
        }
