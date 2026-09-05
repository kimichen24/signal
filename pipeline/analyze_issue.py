"""Run OpenAI structured extraction over cleaned issues.

Implemented in prompts/02_AI_EXTRACTION.md. Uses the Responses API with the
JSON Schema in config/ai_output.schema.json. Model names come from env
(OPENAI_CLASSIFICATION_MODEL). Outputs are versioned with
SIGNAL_ANALYSIS_VERSION; failures are recorded, never swallowed.
"""


def main() -> None:
    raise NotImplementedError(
        "analyze_issue is delivered with prompts/02_AI_EXTRACTION.md"
    )


if __name__ == "__main__":
    main()
