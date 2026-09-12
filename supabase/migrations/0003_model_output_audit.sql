-- Migration 0003 — audit trail for raw model output
-- The persisted platform/surface/etc. hold the NORMALIZED final value
-- (deterministic metadata > strong labels > LLM > Unknown); the untouched
-- LLM result is kept here for auditing and eval.
alter table public.issue_analysis
  add column if not exists model_output jsonb;

comment on column public.issue_analysis.model_output is
  'Raw LLM output before deterministic normalization; final values live in the typed columns';
