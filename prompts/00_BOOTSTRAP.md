# Codex Prompt 00 — Bootstrap

You are implementing the Signal project in this repository.

Before writing code:
1. Read `AGENTS.md`.
2. Read `docs/PRD.md`.
3. Read `docs/ARCHITECTURE.md`.
4. Read `docs/DECISIONS.md`.
5. Read `supabase/schema.sql`.
6. Write a short implementation plan in your response.

Task:
Bootstrap the repository for the Signal MVP.

Requirements:
- Next.js + TypeScript app
- Tailwind CSS
- shadcn/ui-compatible structure
- Python pipeline environment
- Supabase server-side client
- typed env validation
- lint, typecheck and test scripts
- directories described in `docs/ARCHITECTURE.md`
- basic navigation for Overview / Feedback / Insights / Releases / Opportunities
- minimal professional shell UI; do not build fake dashboard metrics
- add a `/health` or equivalent server-side health check
- add README setup instructions

Do NOT:
- create synthetic feedback
- hardcode demo metrics
- add authentication
- add chatbot
- add extra data sources

At the end:
- run lint/typecheck/tests
- list created files
- explain any assumptions
- stop before implementing GitHub ingestion.
