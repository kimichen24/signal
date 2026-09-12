# Data Pipeline Specification

## Dataset windows (reproducible snapshots)
All production analysis operates on a fixed slice:

```text
start_date <= github_created_at < snapshot_at
```

- `snapshot_at` defaults to the run time but is always pinned per run and recorded in the `analysis_runs` table together with `start_date`, version and parameters.
- Ingestion and analysis CLIs accept `--start-date` / `--snapshot-at` to reproduce a past dataset exactly.
- Default exclusion: rows with `product_scope = 'out_of_scope'` are preserved in the database but excluded from product analytics, clustering, trends and priority.
- Classification precedence: deterministic parsed metadata > strong GitHub labels > LLM inference > Unknown (minimum: `platform`, and `surface` where strongly indicated — see `pipeline/normalize.py`). Raw LLM output is kept in `issue_analysis.model_output`.


## Stage 1 — GitHub ingestion
Repository: `openai/codex`

Requirements:
- use authenticated GitHub REST API if token exists
- filter pull requests
- paginate
- store raw JSON fields needed for audit
- idempotent upsert by `github_issue_number`
- keep timestamps in UTC
- initial dev limit: 100 issues
- production mode: configurable date range

Recommended CLI:
```bash
python -m pipeline.ingest_github --repo openai/codex --since 2026-08-07 --limit 100
```

## Stage 2 — Parse issue form
Try deterministic extraction first:
- version
- subscription
- platform
- actual issue
- reproduction steps
- expected behavior
- additional info

Do not use LLM to parse fields that can be parsed reliably from headings.

## Stage 3 — Clean text
Create `body_clean` for semantic analysis.

Remove/collapse:
- very large fenced code blocks
- long JSON dumps
- doctor reports
- repeated logs
- stack traces after a configurable threshold

Preserve:
- title
- actual issue
- expected behavior
- short reproduction summary
- user-described impact
- platform/version metadata

Raw body must remain intact in DB.

## Stage 4 — Structured extraction
Input:
- title
- parsed metadata
- body_clean
- GitHub labels

Output must validate against `config/ai_output.schema.json`.

Never parse model prose manually.

## Stage 5 — Embedding
Semantic text:
```text
Title: ...
Summary: ...
Scenario: ...
Impact: ...
Category: ...
Subtopic: ...
```

Save embedding only after successful structured analysis.

## Stage 6 — Clustering
Run within top-level categories.
Persist:
- cluster ID
- members
- centroid/summary metadata
- representative issues

Minimum cluster size should be configurable.

## Stage 7 — Trend analytics
Default:
- current = last 7 complete days
- previous = preceding 7 complete days

Calculate in deterministic code:
- counts
- growth
- share of feedback
- platform/surface distribution

## Stage 8 — Emerging signals
Apply configurable thresholds:
- current_count >= min_volume
- growth >= min_growth
- severity-weighted score

Do not display “Emerging” based only on LLM opinion.

## Stage 9 — Release impact
For each release:
- before window
- after window
- cluster/category counts
- deltas
- new / increased / decreased / stable

Do not infer causation.

## Stage 10 — Opportunity score
Compute deterministic score.
Then pass computed facts + evidence to LLM only for:
- concise explanation
- product hypothesis
- action brief

## Stage 11 — Evidence validation
Before publishing insight/opportunity:
- has >= configured evidence count
- representative IDs exist
- URLs exist
- computed stats match DB
- confidence threshold satisfied or marked Needs Review
