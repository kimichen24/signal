# How to Use This Pack with Codex

## Recommended workflow
Do not paste the full PRD into every prompt. Keep these files in the repository so Codex can read them.

1. Put this pack at the root of a fresh project folder.
2. Start Codex in that folder.
3. Send `prompts/00_BOOTSTRAP.md`.
4. Review the diff and run the app.
5. Commit.
6. Send `prompts/01_DATA_INGESTION.md`.
7. Commit.
8. Continue through Prompt 05.

## At every stage
Ask Codex to:
- read AGENTS.md first
- show a plan before editing
- run tests
- stop at the requested boundary
- avoid unrelated refactors

## If Codex drifts
Use:
> Re-read AGENTS.md and docs/DECISIONS.md. Do not expand the MVP. Revert any feature that violates the locked scope.

## Before full API batch
Use:
> Run the pipeline on 5 issues first. Show me the validated outputs and any failures before running 100.

## Before full dataset
Use:
> Do not run the full 30-day dataset until the 100-item Eval and cost/runtime checks are complete.
