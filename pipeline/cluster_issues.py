"""Cluster analyzed issues within top-level categories.

Implemented in prompts/03_INTELLIGENCE.md. Cluster membership is computed
algorithmically (HDBSCAN or agglomerative), never decided freely by an LLM.
Cluster names are generated only after membership is fixed.
"""


def main() -> None:
    raise NotImplementedError(
        "cluster_issues is delivered with prompts/03_INTELLIGENCE.md"
    )


if __name__ == "__main__":
    main()
