# Clustering Calibration Record (Prompt 03, 2026-09)

## Frozen production configuration

| Parameter | Value |
| --- | --- |
| analysis_version | v0.3.4 |
| embedding model | `local:intfloat/multilingual-e5-small` (384-dim, L2-normalized, `passage:` prefix) |
| representation | A: Title + Summary + User scenario + User impact + **Category** + Subtopic |
| partition | category-only (category + issue_type evaluated and rejected) |
| distance_threshold | **0.15** (cosine, average linkage, scikit-learn AgglomerativeClustering) |
| min_cluster_size / min_category_size | **3** |
| needs_refinement threshold | cluster size ≥ 15 → flagged broad, not presented as one precise pain point |

Membership is deterministic and reproducible: same embeddings + same params → same clusters. The LLM (MiMo) only names/summarizes clusters **after** membership is fixed.

## Why 0.15 / 3

- **e5 similarity band**: dataset-wide pairwise cosine sits in 0.756–0.962 (median ≈ 0.83–0.84). The initially assumed threshold range 0.20–0.45 collapses to identical results at every step (the old 6-cluster/29-member run) — it does not discriminate.
- **Sweep** (thresholds 0.05–0.45 × min sizes 3–5): ≤0.10 yields nothing; 0.12 over-fragments (28.6% coverage); **0.15/3 gives 10 interpretable clusters at 69.2% coverage with zero weak clusters**; ≥0.18 re-merges Reliability into a 29-member mega-cluster.
- **Partition experiment**: category+issue_type produces the same 10 clusters at 60.4% coverage (vs 69.2%) with equal coherence — no benefit, rejected.

## Representation A/B ablation

- B removed the `Category:` line from the semantic text.
- Hypothesis (Category inflates within-category similarity / causes oversized clusters) was **rejected**: global pairwise distribution essentially unchanged (median 0.827 → 0.841); Reliability produced the identical 18/5/3 cluster structure under both representations.
- B was a side-grade: slightly better App/UI/UX granularity (3 clusters vs 2, +5pp coverage), slightly coarser Usage & Credits (2 → 1).
- **Decision: keep A** — deciding weight (Reliability) unchanged, B's marginal App/UI/UX gain does not justify a full re-embedding for this MVP. Re-evaluate at the 30-day dataset scale. Tooling kept: `pipeline/embedding_ablation.py`, `pipeline/cluster_sweep.py`.

## Known limitation (explicit quality flag)

Reliability contains an n=18 cluster spanning several failure modes (app startup, crashes, WS/SSH connectivity, git diff fan-out). It passes internal-coherence checks but is too broad to be presented as one precise product pain point, so it is flagged `needs_refinement = true` (stored in `clusters.clustering_params`). It should be split via subtopic-level refinement as data grows — not silently presented as a single finding.

## Sweep results snapshot (eligible = 91 in-scope issues with embeddings)

| thr | mcs | clusters | clustered | noise | coverage% | largest | median |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ≤0.10 | 3/4/5 | 0 | 0 | 91 | 0 | — | — |
| 0.12 | 3 | 8 | 26 | 65 | 28.6 | 4 | 3.0 |
| **0.15** | **3** | **10** | **63** | **28** | **69.2** | **18** | **4.5** |
| 0.15 | 4 | 8 | 57 | 34 | 62.6 | 18 | 5.5 |
| 0.15 | 5 | 5 | 45 | 46 | 49.5 | 18 | 6.0 |
| 0.18+ | 3 | 8 | 81 | 10 | 89.0 | 29 | 6.0 |

## At-scale recalibration (2,096 in-scope issues, codex-14d-2026-09-06)

The 0.15/3 configuration calibrated on the 100-issue dev sample does NOT
hold at full scale: average-linkage chaining produced an n=495 mega-cluster
(93.6% coverage concentrated in taxonomy-sized blobs). Deterministic grid
re-run (membership-count diagnostics) on 2,096 rows:

| thr | mcs | clusters | clustered | coverage% | largest |
| --- | --- | --- | --- | --- | --- |
| 0.08 | 3 | 81 | 360 | 17.2 | 21 |
| 0.10 | 3 | 146 | 790 | 37.7 | 28 |
| **0.12** | **3** | **197** | **1,395** | **66.6** | **75** |
| 0.15 | 3 | 88 | 1,962 | 93.6 | **495** (rejected) |

**New frozen config: 0.12 / min_cluster_size 3 / category-only.** Largest
cluster (n=75, Usage & Credits quota-mechanics family) is flagged
`needs_refinement`; all clusters pass the coherence bar (mean pairwise
cosine ≥ dataset median 0.843).

## Cross-process determinism fix

Cluster membership was stable within a process but varied between processes.
Root cause: PostgREST returned issue rows in arbitrary order without an
ORDER BY, and agglomerative tie-breaking is input-order sensitive near
equal merge distances. Fix: `load_analysis_rows` now orders by
`issue_id` (stable), and the clustering module pins BLAS/OpenMP to one
thread before numpy/sklearn import as belt-and-braces against threaded-BLAS
reduction-order variance. Membership is now verified identical across
processes (fingerprint check).
