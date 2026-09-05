-- Signal MVP schema
-- Supabase / PostgreSQL

create extension if not exists vector with schema extensions;

create table if not exists public.issues (
  id uuid primary key default gen_random_uuid(),
  github_issue_number bigint not null unique,
  title text not null,
  body_raw text,
  body_clean text,
  github_url text not null,
  state text,
  github_labels jsonb not null default '[]'::jsonb,
  comments_count integer not null default 0,
  reactions_count integer not null default 0,
  github_created_at timestamptz not null,
  github_updated_at timestamptz,
  github_closed_at timestamptz,
  source_payload jsonb,
  parsed_version text,
  parsed_subscription text,
  parsed_platform text,
  parsed_actual text,
  parsed_steps text,
  parsed_expected text,
  parsed_additional_info text,
  duplicate_group_id uuid,
  ingested_at timestamptz not null default now()
);

create index if not exists idx_issues_created_at on public.issues (github_created_at desc);
create index if not exists idx_issues_state on public.issues (state);

create table if not exists public.issue_analysis (
  id uuid primary key default gen_random_uuid(),
  issue_id uuid not null references public.issues(id) on delete cascade,
  issue_type text not null check (issue_type in ('bug','feature_request','ux_issue','documentation','other')),
  surface text not null check (surface in ('Codex App','CLI','IDE Extension','Web','Unknown')),
  platform text not null check (platform in ('Windows','macOS','Linux','Android','iOS','Other','Unknown')),
  category text not null,
  subtopic text not null,
  user_scenario text,
  user_impact text,
  severity text not null check (severity in ('critical','high','medium','low')),
  sentiment text not null check (sentiment in ('negative','neutral','positive','mixed')),
  summary text not null,
  confidence numeric(4,3) not null check (confidence >= 0 and confidence <= 1),
  needs_review boolean not null default false,
  analysis_version text not null,
  model_name text,
  embedding extensions.vector(1536),
  analysis_error text,
  analyzed_at timestamptz not null default now(),
  unique(issue_id, analysis_version)
);

create index if not exists idx_analysis_category on public.issue_analysis(category);
create index if not exists idx_analysis_surface on public.issue_analysis(surface);
create index if not exists idx_analysis_platform on public.issue_analysis(platform);
create index if not exists idx_analysis_severity on public.issue_analysis(severity);
create index if not exists idx_analysis_needs_review on public.issue_analysis(needs_review);

create index if not exists idx_analysis_embedding_hnsw
on public.issue_analysis
using hnsw (embedding extensions.vector_cosine_ops);

create table if not exists public.clusters (
  id uuid primary key default gen_random_uuid(),
  analysis_version text not null,
  cluster_key text not null,
  cluster_name text not null,
  category text not null,
  summary text,
  issue_count integer not null default 0,
  current_period_count integer not null default 0,
  previous_period_count integer not null default 0,
  growth_rate numeric,
  avg_severity_score numeric,
  primary_platform text,
  primary_surface text,
  emerging_score numeric,
  is_emerging boolean not null default false,
  representative_issue_ids uuid[] not null default '{}',
  generated_at timestamptz not null default now(),
  unique(analysis_version, cluster_key)
);

create table if not exists public.cluster_members (
  cluster_id uuid not null references public.clusters(id) on delete cascade,
  issue_id uuid not null references public.issues(id) on delete cascade,
  similarity_score numeric,
  is_representative boolean not null default false,
  primary key(cluster_id, issue_id)
);

create table if not exists public.releases (
  id uuid primary key default gen_random_uuid(),
  product text not null default 'Codex',
  name text not null,
  release_date timestamptz not null,
  source_url text not null,
  description text,
  created_at timestamptz not null default now()
);

create table if not exists public.release_impacts (
  id uuid primary key default gen_random_uuid(),
  release_id uuid not null references public.releases(id) on delete cascade,
  cluster_id uuid not null references public.clusters(id) on delete cascade,
  window_days integer not null default 7,
  before_count integer not null default 0,
  after_count integer not null default 0,
  change_rate numeric,
  signal_type text not null check (signal_type in ('new','increased','decreased','stable')),
  confidence numeric,
  computed_at timestamptz not null default now(),
  unique(release_id, cluster_id, window_days)
);

create table if not exists public.opportunities (
  id uuid primary key default gen_random_uuid(),
  cluster_id uuid not null references public.clusters(id) on delete cascade,
  frequency_score numeric not null,
  severity_score numeric not null,
  growth_score numeric not null,
  engagement_score numeric not null,
  priority_score numeric not null,
  action_type text not null check (action_type in ('investigate_now','validate','monitor','low_priority')),
  priority_reason text,
  product_hypothesis text,
  suggested_metrics jsonb not null default '[]'::jsonb,
  action_brief jsonb not null default '{}'::jsonb,
  generated_at timestamptz not null default now(),
  unique(cluster_id)
);

create table if not exists public.eval_items (
  id uuid primary key default gen_random_uuid(),
  issue_id uuid not null references public.issues(id) on delete cascade,
  split text check (split in ('dev','holdout')),
  human_issue_type text,
  human_category text,
  human_surface text,
  human_platform text,
  human_severity text,
  reviewer_note text,
  reviewed_at timestamptz,
  unique(issue_id)
);

-- Portfolio MVP should access Supabase from server-side code.
-- Do not expose service-role keys in the browser.
