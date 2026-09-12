-- Migration 0007 — analysis input traceability
-- dataset membership is reproducible via [start_at, snapshot_at); the
-- exact semantic input of every analysis is auditable via this hash
-- (sha256 of the normalized payload sent to the classifier). A later
-- GitHub edit cannot silently change what an old analysis used.
alter table public.issue_analysis
  add column if not exists analysis_input_hash text;

comment on column public.issue_analysis.analysis_input_hash is
  'sha256 of the exact normalized classification payload (title/parsed fields/labels/body_clean + min_confidence); recomputable and auditable';
