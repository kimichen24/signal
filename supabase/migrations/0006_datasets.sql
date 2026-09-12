-- Migration 0006 — dataset registry (Historical Expansion Phase 1)
-- A dataset definition pins a reproducible GitHub creation-time window;
-- the same dataset_id always resolves to the same [start_at, snapshot_at)
-- window over issue created_at.
create table if not exists public.datasets (
  id uuid primary key default gen_random_uuid(),
  dataset_id text not null unique,
  repository text not null,
  start_at timestamptz not null,
  snapshot_at timestamptz not null,
  created_at timestamptz not null default now(),
  raw_issue_count integer not null default 0,
  analysis_version text
);

comment on table public.datasets is
  'Reproducible dataset definitions: membership is always derived from start_at <= github_created_at < snapshot_at';
