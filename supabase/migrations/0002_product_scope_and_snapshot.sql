-- Migration 0002 — product scope classification + reproducible snapshot runs
-- Applied after supabase/schema.sql.

-- 1. Product scope on every analysis row.
--    codex_core      : issue directly concerns Codex App/CLI/IDE extension,
--                      agent behavior, coding workflows, tools, execution,
--                      models, workspace, context, usage or other Codex
--                      functionality.
--    codex_adjacent  : issue concerns a ChatGPT/OpenAI surface that materially
--                      interacts with a Codex workflow (Remote, Work,
--                      cross-surface task behavior).
--    out_of_scope    : posted in the repository but does not materially
--                      concern the Codex product or Codex workflow.
--    out_of_scope rows are ALWAYS preserved in the database; product
--    analytics, clustering, trends and priority exclude them by default.
alter table public.issue_analysis
  add column if not exists product_scope text
    check (product_scope in ('codex_core', 'codex_adjacent', 'out_of_scope')),
  add column if not exists scope_confidence numeric
    check (scope_confidence >= 0 and scope_confidence <= 1),
  add column if not exists scope_reason text;

create index if not exists idx_analysis_product_scope
  on public.issue_analysis (product_scope);

comment on column public.issue_analysis.product_scope is
  'codex_core | codex_adjacent | out_of_scope; out_of_scope rows are kept but excluded from analytics/clustering/trends/priority by default';

-- 2. Reproducible dataset snapshots.
--    Every pipeline run records the exact window it operated on:
--      start_date <= github_created_at < snapshot_at
--    so any metric can be recomputed against the same slice of data.
create table if not exists public.analysis_runs (
  id uuid primary key default gen_random_uuid(),
  run_type text not null check (run_type in (
    'ingestion', 'analysis', 'embedding', 'clustering',
    'trends', 'release_impact', 'opportunities', 'eval'
  )),
  analysis_version text,
  repo text,
  model_name text,
  start_date timestamptz,
  snapshot_at timestamptz not null,
  item_count integer not null default 0,
  params jsonb not null default '{}'::jsonb,
  error_summary text,
  created_at timestamptz not null default now()
);

create index if not exists idx_analysis_runs_type
  on public.analysis_runs (run_type, created_at desc);

comment on table public.analysis_runs is
  'Run ledger: documents the dataset window (start_date <= github_created_at < snapshot_at) and parameters used for each pipeline run';
