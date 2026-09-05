# Implementation Plan

## Phase 0 — Bootstrap
Deliverables:
- Next.js app boots
- Python env boots
- Supabase connected
- schema migrated
- basic health page
- lint/typecheck/test scripts

Exit criteria:
- no real feature yet
- all secrets via env

## Phase 1 — 100 real issues
Deliverables:
- ingest 100 Codex Issues
- filter PRs
- parse issue sections
- save raw + clean text
- Feedback page with real rows

Exit criteria:
- click row → original GitHub URL
- no mock feedback in production path

## Phase 2 — AI structuring
Deliverables:
- Structured Output schema
- batch analysis
- taxonomy
- confidence
- Needs Review
- embeddings

Exit criteria:
- 100 issues analyzed
- failures visible/retryable
- AI values stored with analysis_version

## Phase 3 — Intelligence
Deliverables:
- clustering
- trends
- Emerging Signals
- Traceability
- deterministic priority scoring

Exit criteria:
- every insight links to evidence
- all numbers DB-derived

## Phase 4 — Release + Action
Deliverables:
- releases table/data
- before/after comparison
- correlation-safe copy
- Opportunities
- Action Brief

Exit criteria:
- at least one real public release/event analyzed
- no causal language

## Phase 5 — Eval + Portfolio polish
Deliverables:
- 100-item eval workflow
- efficiency baseline
- polished dashboard
- limitations page/section
- README case study
- deployment

Exit criteria:
- demo path works
- no fake metrics
- docs match implementation

## Backlog (do not build in MVP)
- Reddit
- Discord
- App Store
- multi-product workspace
- auth
- multi-tenant
- alerts
- daily/weekly email brief
