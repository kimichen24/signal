"""Generate embeddings for analyzed issues and store them in pgvector.

Implemented in prompts/02_AI_EXTRACTION.md. Embedding model comes from
OPENAI_EMBEDDING_MODEL. The semantic representation is
title + summary + user_scenario + user_impact (docs/ARCHITECTURE.md §5).
"""


def main() -> None:
    raise NotImplementedError(
        "embed_issues is delivered with prompts/02_AI_EXTRACTION.md"
    )


if __name__ == "__main__":
    main()
