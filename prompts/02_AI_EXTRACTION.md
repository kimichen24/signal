# Codex Prompt 02 — AI Structured Extraction

Read:
- `AGENTS.md`
- `config/taxonomy.json`
- `config/ai_output.schema.json`
- `docs/EVAL_PLAN.md`

Implement AI analysis for the ingested 100 issues.

Requirements:
- OpenAI Responses API
- Structured Outputs / JSON Schema
- model selected from `OPENAI_CLASSIFICATION_MODEL`
- embedding model selected from env
- use parsed metadata + cleaned text, not giant raw logs
- validate output
- save to `issue_analysis`
- save `analysis_version`
- set `needs_review=true` when confidence < threshold
- failures are logged and retryable
- generate embeddings from concise semantic representation
- do not silently pad/truncate vectors
- show AI fields and confidence in Feedback detail
- label severity as `AI-estimated`

Add a dry-run mode that prints estimated work count before sending API calls.

At the end:
- run against a very small batch first (e.g. 5)
- validate
- then run 100 only if the small batch succeeds
- summarize failures and token/cost metadata if the API exposes it
- stop before clustering.
