# Sources / Implementation References

These are implementation references, not marketing copy.

## GitHub
GitHub REST API — Issues:
https://docs.github.com/en/rest/issues/issues

Important:
- GitHub issue endpoints can include pull requests; filter any item with a `pull_request` field.
- Use pagination.
- Use versioned GitHub REST headers.

## Codex repository
https://github.com/openai/codex

The Codex App Issue template includes structured fields for:
- version
- subscription
- platform
- issue
- reproduction steps
- expected behavior
- additional information

## OpenAI
Structured Outputs:
https://openai.com/index/introducing-structured-outputs-in-the-api/

Responses API:
https://developers.openai.com/api/reference/

Implementation rule:
Use JSON Schema Structured Outputs for issue extraction.

## Supabase
pgvector:
https://supabase.com/docs/guides/database/extensions/pgvector

Vector columns:
https://supabase.com/docs/guides/ai/vector-columns

The starter schema uses a 1536-dimensional vector column. If the selected embedding model uses another dimension, migrate the schema.
