# Codex Prompt 01 — Real GitHub Data

Read `AGENTS.md` and `docs/DATA_PIPELINE.md`.

Implement Phase 1.

Goal:
Import the first 100 real Issues from `openai/codex`, parse them, store them in Supabase, and display them on the Feedback page.

Requirements:
- GitHub REST API
- authenticated request if `GITHUB_TOKEN` exists
- filter Pull Requests
- configurable repo/date/limit
- idempotent upsert
- deterministic parser for Codex issue-form headings
- preserve `body_raw`
- generate `body_clean`
- add parser tests using realistic fixture text
- Feedback table uses DB data only
- Feedback detail links to original GitHub Issue
- no LLM yet

CLI should be documented and easy to run.

At the end:
- report imported row count
- show parser test results
- verify no PR rows were imported
- stop before AI analysis.
