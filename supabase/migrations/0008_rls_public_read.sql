-- Migration 0008 — least-privilege public portfolio access
--
-- Architecture:
--   Public Next.js portfolio UI → Supabase anon key → RLS SELECT + column grants
--   Local Python/admin pipeline → service_role key (bypasses RLS and column grants)
--
-- Column-level audit result:
--   issues:          7 of 23 columns granted (exclude body_raw, body_clean,
--                    source_payload, 6 parsed_ fields, comments/reactions,
--                    timestamps, dedup/pipeline state)
--   issue_analysis: 17 of 25 columns granted (exclude embedding, embedding_model,
--                    model_output, analysis_input_hash, model_name, analysis_error,
--                    sentiment, scope_confidence)
--   clusters:       all 19 columns (clustering_params contains algorithm config
--                    and scoring metadata — not secrets; needs_refinement and
--                    trend_state are read from it by the UI)
--   cluster_members: all 4 columns
--   opportunities:  all 13 columns (priority_reason contains the scoring
--                    breakdown displayed by the "Why this score?" UI)
--   releases:        all 7 columns
--   release_impacts: all 10 columns
--   eval_items / analysis_runs / datasets: 0 columns (locked — RLS on, zero grants)

-- ============================================================
-- Step 1: Enable RLS on every table
-- ============================================================
alter table public.issues enable row level security;
alter table public.issue_analysis enable row level security;
alter table public.clusters enable row level security;
alter table public.cluster_members enable row level security;
alter table public.opportunities enable row level security;
alter table public.releases enable row level security;
alter table public.release_impacts enable row level security;
alter table public.eval_items enable row level security;
alter table public.analysis_runs enable row level security;
alter table public.datasets enable row level security;

-- ============================================================
-- Step 2: Revoke blanket anon privileges (clean slate)
-- Supabase default grants ALL to anon — strip it before re-granting
-- ============================================================
revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;

-- ============================================================
-- Step 3: RLS SELECT policies for the 7 public tables
-- (admin tables get RLS enabled but NO policy → locked for anon)
-- ============================================================
create policy "portfolio_select" on public.issues
  for select to anon using (true);
create policy "portfolio_select" on public.issue_analysis
  for select to anon using (true);
create policy "portfolio_select" on public.clusters
  for select to anon using (true);
create policy "portfolio_select" on public.cluster_members
  for select to anon using (true);
create policy "portfolio_select" on public.opportunities
  for select to anon using (true);
create policy "portfolio_select" on public.releases
  for select to anon using (true);
create policy "portfolio_select" on public.release_impacts
  for select to anon using (true);

-- ============================================================
-- Step 4: Column-level grants for issues (7 of 23 columns)
-- Excludes: body_raw, body_clean, source_payload, github_labels,
--   comments_count, reactions_count, github_updated_at, github_closed_at,
--   parsed_version, parsed_subscription, parsed_actual, parsed_steps,
--   parsed_expected, parsed_additional_info, duplicate_group_id, ingested_at
-- ============================================================
grant select
  (id, github_issue_number, title, github_url, state,
   parsed_platform, github_created_at)
on public.issues to anon;

-- ============================================================
-- Step 5: Column-level grants for issue_analysis (17 of 25 columns)
-- Excludes: embedding, embedding_model, model_output, analysis_input_hash,
--   model_name, analysis_error, sentiment, scope_confidence
-- ============================================================
grant select
  (id, issue_id, issue_type, surface, platform, category, subtopic,
   severity, confidence, needs_review, summary, user_scenario,
   user_impact, product_scope, scope_reason, analysis_version, analyzed_at)
on public.issue_analysis to anon;

-- ============================================================
-- Step 6: Table-level grants for fully-safe tables
-- ============================================================
grant select on public.clusters to anon;
grant select on public.cluster_members to anon;
grant select on public.opportunities to anon;
grant select on public.releases to anon;
grant select on public.release_impacts to anon;

-- ============================================================
-- Notes:
-- * service_role bypasses RLS and column grants (Supabase default);
--   the local Python pipeline retains full read/write access.
-- * eval_items, analysis_runs, datasets: RLS enabled, zero grants
--   to anon → completely inaccessible without service_role.
-- * anon has zero INSERT/UPDATE/DELETE privileges on any table.
-- * clusters.clustering_params is exposed because the UI reads
--   needs_refinement and trend.trend_state from it; it contains
--   algorithm configuration and scoring metadata, not secrets or
--   personal data. If tighter control is needed, extract
--   needs_refinement + trend_state into dedicated columns in a
--   future migration and revoke clustering_params.
-- * The portfolio queries in lib/supabase/queries.ts already select
--   only granted columns — verified against every .select() call.
-- ============================================================
