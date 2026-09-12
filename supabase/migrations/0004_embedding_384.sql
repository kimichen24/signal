-- Migration 0004 — embedding storage: 1536 placeholder -> 384 (local e5-small)
-- No embedding values exist yet (no provider was configured before this
-- migration), so rebuilding the column loses nothing.
-- EMBEDDING_DIMENSION=384 must match this column; a different model
-- requires another migration (docs/ARCHITECTURE.md §8: never truncate/pad).

drop index if exists idx_analysis_embedding_hnsw;

alter table public.issue_analysis drop column if exists embedding;
alter table public.issue_analysis
  add column embedding extensions.vector(384);

-- Bind every vector to the model/version that produced it so embeddings
-- can be regenerated (or swapped) later without guessing.
alter table public.issue_analysis
  add column if not exists embedding_model text;

comment on column public.issue_analysis.embedding_model is
  'Embedding model/version used for this row''s vector; vectors are regenerable per model';

create index if not exists idx_analysis_embedding_hnsw
  on public.issue_analysis
  using hnsw (embedding extensions.vector_cosine_ops);
