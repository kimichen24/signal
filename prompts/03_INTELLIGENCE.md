# Codex Prompt 03 — Insights, Trends, Evidence

Implement:
- category-level analytics
- semantic clustering within top-level categories
- cluster membership persistence
- representative evidence
- current vs previous 7-day trends
- Emerging Signals
- deterministic Investigation Priority inputs
- Insights page
- Overview / What Changed

Rules:
- cluster membership must be reproducible enough to rerun
- LLM may name/summarize a cluster only after membership is fixed
- all counts/growth values come from data
- minimum volume threshold for emerging signals
- every Insight links to real issues
- no hardcoded findings
- no unsupported causal claims

Add tests for:
- growth calculation
- zero baseline
- min-volume threshold
- priority normalization
- evidence presence

At the end, produce a short audit:
for 3 displayed insights, show the exact underlying issue IDs.
