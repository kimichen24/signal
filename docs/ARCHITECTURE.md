# Technical Architecture

## 1. High-level

```text
GitHub REST API
      |
      v
Python Ingestion
      |
      v
Postgres / Supabase (raw issues)
      |
      v
Pre-processing
      |
      v
OpenAI Structured Extraction
      |
      v
issue_analysis
      |
      +--> Embeddings --> pgvector
      |                    |
      |                    v
      |                 Clustering
      |                    |
      v                    v
Deterministic Analytics -> clusters
      |                    |
      +---- Trends --------+
      +---- Release Impact
      +---- Priority Score
      |
      v
Action Brief (LLM grounded in computed stats)
      |
      v
Next.js Product UI
```

## 2. Recommended monorepo structure

```text
signal/
├─ app/
│  ├─ overview/
│  ├─ feedback/
│  ├─ insights/
│  ├─ releases/
│  ├─ opportunities/
│  └─ api/
├─ components/
├─ lib/
│  ├─ supabase/
│  ├─ analytics/
│  └─ types/
├─ pipeline/
│  ├─ ingest_github.py
│  ├─ clean_issue.py
│  ├─ analyze_issue.py
│  ├─ embed_issues.py
│  ├─ cluster_issues.py
│  ├─ compute_trends.py
│  ├─ compute_release_impact.py
│  └─ evaluate.py
├─ supabase/
│  ├─ migrations/
│  └─ seed/
├─ tests/
├─ docs/
├─ AGENTS.md
└─ .env.local
```

## 3. Responsibilities

### Python
- GitHub ingestion
- text cleaning
- LLM structured extraction
- embeddings
- clustering
- batch analytics
- eval

### TypeScript / Next.js
- dashboard
- filtering
- detail pages
- API/server actions
- typed data presentation
- no heavy ML logic

### Postgres
- source of truth
- deterministic aggregations
- traceability
- vector storage

## 4. Data flow invariants
- Raw data is immutable except source updates.
- AI analysis is versioned (`analysis_version`).
- Analytics output can always be recomputed.
- No computed metric is stored without enough source IDs to trace it.
- Frontend never fabricates fallback data.

## 5. Clustering approach (MVP)
Do not overengineer.

Recommended sequence:
1. Stable top-level category via Structured Output.
2. Generate embedding from a concise semantic representation:
   `title + summary + user_scenario + user_impact`.
3. Cluster within each top-level category.
4. Start with HDBSCAN or agglomerative clustering offline.
5. Generate human-readable cluster names using an LLM only after cluster membership is fixed.
6. Save representative issue IDs.

Do not let the LLM freely decide cluster membership for thousands of items.

## 6. Release data
MVP can seed release/product-event dates manually from official public release notes.
Each event must store a `source_url`.

## 7. OpenAI integration
Use Responses API Structured Outputs / JSON Schema for extraction.
Keep:
- `OPENAI_CLASSIFICATION_MODEL`
- `OPENAI_EMBEDDING_MODEL`
as environment variables.

Do not hard-code model IDs in core logic.

## 8. Embedding
Starter schema uses `vector(1536)`, compatible with the common 1536-dimension embedding setup.
If a different embedding model/dimension is selected, create a DB migration rather than silently truncating/padding vectors.

## 9. Frontend data access
Portfolio MVP:
- Prefer Server Components / server-side Supabase access.
- Keep service-role credentials server-only.
- Never expose OpenAI or GitHub secrets to browser code.

## 10. Testing
Minimum:
- parser unit tests
- taxonomy schema validation
- priority formula tests
- growth calculation tests
- release-window tests
- route/component smoke tests
