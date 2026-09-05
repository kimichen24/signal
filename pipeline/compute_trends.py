"""Compute deterministic trends and emerging signals.

Implemented in prompts/03_INTELLIGENCE.md. Uses the growth formula
(current - previous) / max(previous, 1) with the SIGNAL_EMERGING_* volume and
growth thresholds from env. All math is deterministic and testable.
"""


def main() -> None:
    raise NotImplementedError(
        "compute_trends is delivered with prompts/03_INTELLIGENCE.md"
    )


if __name__ == "__main__":
    main()
