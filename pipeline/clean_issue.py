"""Clean issue bodies for LLM input without touching raw data.

Implemented in prompts/01_DATA_INGESTION.md. Writes `body_clean`; large logs,
doctor reports and code blocks may be trimmed from LLM input but are never
removed from `body_raw`.
"""


def main() -> None:
    raise NotImplementedError(
        "clean_issue is delivered with prompts/01_DATA_INGESTION.md"
    )


if __name__ == "__main__":
    main()
