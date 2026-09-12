-- Migration 0005 — clustering reproducibility metadata (Prompt 03)
alter table public.clusters
  add column if not exists clustering_params jsonb
    not null default '{}'::jsonb,
  add column if not exists problem_statement text;

comment on column public.clusters.clustering_params is
  'Exact clustering parameters/version used (algorithm, distance threshold, min sizes) for reproducibility';
comment on column public.clusters.problem_statement is
  'LLM-written product-problem statement, generated only after membership was fixed; based strictly on cluster members';
