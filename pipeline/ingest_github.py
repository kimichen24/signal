"""Ingest real issues from the GitHub REST API into Supabase.

Implemented in prompts/01_DATA_INGESTION.md. Issues only — PRs are filtered
out. Raw bodies are preserved; never mutate or delete raw data.
"""


def main() -> None:
    raise NotImplementedError(
        "ingest_github is delivered with prompts/01_DATA_INGESTION.md"
    )


if __name__ == "__main__":
    main()
