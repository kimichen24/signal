"""Embedding provider layer — independent from the classification provider.

Classification (MiMo) and embeddings are wired through separate factories:
embedding text NEVER goes to the classification provider. The local
provider runs sentence-transformers in-process.

Providers are registered in build_embedding_provider(); adding one later
(e.g. openai) means implementing embed() and adding a branch — nothing else
changes.
"""

from __future__ import annotations

from typing import Any


class EmbeddingConfigError(RuntimeError):
    pass


class LocalEmbeddingProvider:
    """sentence-transformers in-process embeddings."""

    name = "local"

    def __init__(
        self,
        model_name: str,
        dimension: int,
        prefix: str = "",
    ) -> None:
        if not model_name:
            raise EmbeddingConfigError(
                "LOCAL_EMBEDDING_MODEL is not set in .env.local"
            )
        from sentence_transformers import SentenceTransformer

        self._st_model = SentenceTransformer(model_name)
        self.model = model_name
        self.dimension = int(dimension)
        self.prefix = prefix or ""
        # Fail fast on a dimension mismatch instead of ever padding or
        # truncating vectors (docs/ARCHITECTURE.md §8).
        probe = self.embed(["dimension probe"])
        if probe and len(probe[0]) != self.dimension:
            raise EmbeddingConfigError(
                f"model {model_name!r} produces {len(probe[0])}-dim vectors "
                f"but EMBEDDING_DIMENSION={self.dimension}; fix the env or "
                f"create a migration for the new dimension"
            )

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        prefixed = [f"{self.prefix} {t}".strip() for t in texts]
        vectors = self._st_model.encode(
            prefixed,
            batch_size=32,
            normalize_embeddings=True,  # cosine space (HNSW cosine ops)
            show_progress_bar=False,
        )
        dims = {len(v) for v in vectors}
        if dims != {self.dimension}:
            raise ValueError(
                f"embedding dimension mismatch: got {dims}, expected "
                f"{self.dimension}; refusing to pad or truncate"
            )
        return [[float(x) for x in v] for v in vectors]


def build_embedding_provider(
    env: Any,
) -> Any:
    """Build the embedding provider from EMBEDDING_PROVIDER + its settings.

    Returns None only for EMBEDDING_PROVIDER=none (rows stay without
    vectors; --embed-only can backfill later).
    """
    provider_name = (env.get("EMBEDDING_PROVIDER") or "").strip().lower()

    if not provider_name or provider_name == "none":
        return None

    if provider_name == "local":
        from pipeline.ai.embeddings import LocalEmbeddingProvider

        return LocalEmbeddingProvider(
            model_name=(env.get("LOCAL_EMBEDDING_MODEL") or "").strip()
            or "intfloat/multilingual-e5-small",
            dimension=int(env.get("EMBEDDING_DIMENSION") or 384),
            prefix=(env.get("LOCAL_EMBEDDING_PREFIX") or "").strip(),
        )

    if provider_name == "mimo":
        from pipeline.ai.mimo import MiMoEmbeddingProvider

        api_key = (env.get("MIMO_API_KEY") or "").strip()
        model = (env.get("MIMO_EMBEDDING_MODEL") or "").strip()
        if not api_key or not model:
            raise EmbeddingConfigError(
                "EMBEDDING_PROVIDER=mimo requires MIMO_API_KEY and "
                "MIMO_EMBEDDING_MODEL in .env.local"
            )
        return MiMoEmbeddingProvider(
            api_key=api_key,
            base_url=(env.get("MIMO_BASE_URL") or "").strip() or None,
            model=model,
        )

    raise EmbeddingConfigError(
        f"Unknown EMBEDDING_PROVIDER {provider_name!r} "
        f"(expected 'local', 'mimo', or 'none')"
    )
