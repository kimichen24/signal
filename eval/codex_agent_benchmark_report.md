# Independent Codex Agent Benchmark — Report

**Independent Codex agent benchmark: unaided triage vs Signal-assisted review.**

This benchmark measures an independent Codex agent performing unaided triage versus reviewing Signal's pre-structured output. It does **not** measure human operator productivity.

## Arm metrics

| metric | Arm A (unaided triage) | Arm B (Signal-assisted review) |
| --- | --- | --- |
| n | 15 | 15 |
| batch wall-clock seconds | 348.0 | 28.5 |
| issues/min | 2.59 | 31.58 |
| issues/hour | 155.2 | 1894.7 |
| batch-derived avg seconds/issue | 23.2 | 1.9 |
| per-item median/p25/p75 | not_applicable | not_applicable |

## Comparison

- relative wall-clock reduction: **91.8%**
- throughput multiplier: **12.21x**
- total corrected fields in Arm B: 6
- mean corrected fields/issue: 0.4
- Arm B issues with zero corrections: 10 (66.7%)
- Arm B issues with ≥1 correction: 5 (33.3%)

## Limitations

- Small-sample operational benchmark (n=15 per arm), not a controlled user study.
- Timing measured per-arm batch wall-clock; per-item percentiles not applicable.
- Reference labels are AI-generated (Codex), not human ground truth.
