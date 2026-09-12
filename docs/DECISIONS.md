# Locked Product Decisions

1. Product name: Signal
2. Product category: AI Product Ops Intelligence System
3. Codex is a Case Study, not the product identity.
4. First source: GitHub Issues only.
5. Dev sample: 100 issues.
6. Full demo target: recent 30-day dataset.
7. Stable top-level taxonomy + dynamic subtopics.
8. Emerging Signals are deterministic analytics.
9. Release Impact reports correlation, not causation.
10. Priority means Investigation Priority.
11. AI severity is always labeled estimated.
12. Every insight requires evidence.
13. First MVP has no login, no chatbot, no Reddit.
14. Models are configurable via env.
15. Raw data is preserved.
16. Product scope: every analysis labels `product_scope` = codex_core / codex_adjacent / out_of_scope with `scope_confidence` + `scope_reason`. Out-of-scope rows are always preserved in the database, but product analytics, clustering, trends and priority exclude them by default.
17. Reproducible datasets: production analysis operates on a fixed window `start_date <= github_created_at < snapshot_at`. The `snapshot_at` used by every run is recorded in `analysis_runs` (run ledger) instead of relying on an ever-moving live window.
18. Deterministic metadata precedence for classification: parsed GitHub metadata > strong GitHub labels > LLM inference > Unknown (minimum: platform, and surface where strongly indicated). The raw LLM result is preserved in `issue_analysis.model_output` for audit; typed columns hold the normalized final value.
19. Codex Remote scope: issues explicitly involving Codex Remote, remote Codex tasks, or a ChatGPT/OpenAI surface used specifically to access/control a Codex workflow are `codex_adjacent` — unless the issue directly concerns the Codex execution system itself, in which case `codex_core` may apply.
20. Locked severity rubric (v0.3.4, calibrated against the 20-item human audit): critical is exceptional (data/state integrity, security/safety, uncontrollable paid-resource loss, or core system unusable with no workaround); high = core workflow blocked/repeatedly failing with bounded impact or workaround; medium = meaningful degradation with workaround; low = cosmetic/localized/withdrawn/non-core. User frustration does not determine severity; "app crashes" alone is not critical; critical must be rare with explicit evidence. Prompt-level calibration only — no deterministic severity-shifting rule.
21. Frozen clustering configuration (v0.3.4, user-approved): representation A (semantic text includes the Category line), category-only partition, cosine distance_threshold=0.15, min_cluster_size=3, min_category_size=3. Representation B (Category removed) was ablated and rejected: it did not change the oversized Reliability cluster and only marginally restructured App/UI/UX. Clusters with ≥15 members are flagged `needs_refinement` (stored in clustering_params with coherence metadata) and must not be presented as single precise pain points. Full record: docs/CLUSTERING_CALIBRATION.md.
22. At-scale clustering config (codex-14d-2026-09-06, 2,096 in-scope): distance_threshold=0.12 recalibrated by deterministic grid — 0.15 produced an n=495 mega-cluster at full scale. Cross-process determinism fixed (deterministic ORDER BY + BLAS single-thread pinning). Same 0.15/3 config remains valid only for the 100-issue dev sample.
23. Frozen Emerging scoring (Prompt 04): state-specific formulas with P95 clipping over emerging-eligible clusters, params persisted per run. normal_growth = 0.35·share_lift + 0.30·|Δ| + 0.20·growth(capped +200%) + 0.15·severity; low_base_acceleration = 0.40·share_lift + 0.35·|Δ| + 0.25·severity (growth excluded); new_signal = 0.45·current_share + 0.35·current_count + 0.20·severity (growth never computed). Negative share lift never contributes positively.
24. Opportunity evidence gate (Prompt 04): size ≥ 5 AND current ≥ 5; narrow exception 3 ≤ size < 5 with ≥ 2 AI-critical members is capped at Validate. Tiny clusters never reach high priority from percentage growth alone.
25. Investigation Priority weights (frozen): 30% frequency (real DB counts) + 25% AI-estimated severity + 25% growth/signal strength (frozen Emerging score) + 20% engagement (real GitHub comments+reactions only). Engagement sparse/unavailable → renormalize available components transparently; never fake neutral values. Status mapping deterministic BEFORE LLM prose: ≥0.60 Investigate Now (size≥5), ≥0.45 Validate, ≥0.30 Monitor, else Low Priority.
