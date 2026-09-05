# Codex Prompt 05 — Eval + Portfolio Polish

Read `docs/EVAL_PLAN.md`.

Implement the evaluation workflow and finish the portfolio demo.

Requirements:
- create a way to select/export 100 random issues for human labeling
- store human labels in `eval_items`
- support dev/holdout split
- compute category/surface/platform accuracy
- compute severity agreement
- show confusion matrix or clear table
- document limitations
- add efficiency baseline template; do not fabricate baseline results
- polish UI around real data
- README should tell the product story, not just setup steps
- add screenshots placeholders only if actual screenshots are produced
- no fake user testimonials
- no fake performance claims

Final quality pass:
- lint
- typecheck
- tests
- accessibility basics
- mobile reasonable
- secrets not exposed
- no mock data in production code paths

Finally produce:
1. a 3-minute demo script
2. a resume-ready project description
3. 4 resume bullets that use only measured facts from the project.
