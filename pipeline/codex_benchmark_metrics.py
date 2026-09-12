"""Final metrics + report for the Codex agent operational benchmark."""
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

FIELDS = ("product_scope", "issue_type", "category", "surface", "platform", "severity")
SEV_ORDER = ["low", "medium", "high", "critical"]

a = list(csv.DictReader(open("eval/codex_agent_benchmark_group_a_completed.csv", encoding="utf-8-sig", newline="")))
b = list(csv.DictReader(open("eval/codex_agent_benchmark_group_b_completed.csv", encoding="utf-8-sig", newline="")))

def seconds(rows):
    return [float(r["seconds"]) for r in rows]

a_s, b_s = seconds(a), seconds(b)
def dist(values):
    s = sorted(values)
    n = len(s)
    p25 = s[int(0.25 * n)] if n else 0
    p75 = s[min(int(0.75 * n), n - 1)] if n else 0
    return {"mean": round(statistics.mean(s), 1), "median": round(statistics.median(s), 1),
            "p25": p25, "p75": p75}

a_total, b_total = sum(a_s), sum(b_s)
a_rate = round(len(a) / a_total * 60, 1)
b_rate = round(len(b) / b_total * 60, 1)
reduction = round(100 * (1 - b_total / a_total), 1)
multiplier = round(a_total / b_total, 2)

corrections = [int(r["corrections_needed"]) for r in b]
zero_corr = sum(1 for c in corrections if c == 0)
per_field = {f: sum(1 for r in b if f in [x.strip() for x in (r["corrected_fields"] or "").split(",")]) for f in FIELDS}

metrics = {
    "benchmark_type": "independent Codex agent operational benchmark — unaided triage vs Signal-assisted review",
    "not_human_timing": "This benchmark measures an independent Codex agent performing unaided triage versus reviewing Signal's pre-structured output. It does not measure human operator productivity.",
    "arms": {
        "A_manual": {"n": len(a), "wall_clock_seconds": round(a_total, 1),
                      "seconds_per_issue": dist(a_s), "issues_per_hour": round(len(a) / a_total * 60, 1)},
        "B_signal_review": {"n": len(b), "wall_clock_seconds": round(b_total, 1),
                             "seconds_per_issue": dist(b_s), "issues_per_hour": round(len(b) / b_total * 60, 1),
                             "total_corrected_fields": sum(corrections),
                             "mean_corrected_fields_per_issue": round(sum(corrections) / len(b), 2),
                             "zero_correction_issues": zero_corr,
                             "zero_correction_pct": round(100 * zero_corr / len(b), 1),
                             "at_least_one_correction_issues": len(b) - zero_corr,
                             "at_least_one_correction_pct": round(100 * (len(b) - zero_corr) / len(b), 1)},
    },
    "comparison": {
        "relative_wall_clock_reduction_pct": reduction,
        "throughput_multiplier": multiplier,
    },
    "timing_granularity_limitation": (
        "Timing measured per-arm batch wall-clock (start of evidence supply to "
        "end of validated labels), not per-item; per-item percentiles are not "
        "measurable in agent batch mode and are reported as the batch-derived mean."
    ),
}

Path("eval/codex_agent_benchmark_metrics.json").write_text(
    json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
)

md = []
md.append("# Independent Codex Agent Benchmark — Report")
md.append("")
md.append("**Independent Codex agent benchmark: unaided triage vs Signal-assisted review.**")
md.append("")
md.append("This benchmark measures an independent Codex agent performing unaided triage "
          "versus reviewing Signal's pre-structured output. It does **not** measure human "
          "operator productivity.")
md.append("")
md.append("## Arm metrics")
md.append("")
md.append("| metric | Arm A (unaided triage) | Arm B (Signal-assisted review) |")
md.append("| --- | --- | --- |")
md.append(f"| n | {len(a)} | {len(b)} |")
md.append(f"| wall-clock seconds | {round(a_total, 1)} | {round(b_total, 1)} |")
md.append(f"| mean seconds/issue | {dist(a_s)['mean']} | {dist(b_s)['mean']} |")
md.append(f"| median seconds/issue | {dist(a_s)['median']} | {dist(b_s)['median']} |")
md.append(f"| p25 / p75 (batch-derived) | {dist(a_s)['p25']} / {dist(a_s)['p75']} | {dist(b_s)['p25']} / {dist(b_s)['p75']} |")
md.append(f"| issues/hour | {round(len(a) / a_total * 60, 1)} | {round(len(b) / b_total * 60, 1)} |")
md.append("")
md.append("## Comparison")
md.append("")
md.append(f"- relative wall-clock reduction: **{reduction}%**")
md.append(f"- throughput multiplier: **{multiplier}x**")
md.append(f"- total corrected fields in Arm B: {sum(corrections)}")
md.append(f"- mean corrected fields/issue: {round(sum(corrections) / len(b), 2)}")
md.append(f"- Arm B issues with zero corrections: {zero_corr} ({round(100 * zero_corr / len(b), 1)}%)")
md.append(f"- Arm B issues with ≥1 correction: {len(b) - zero_corr} ({round(100 * (len(b) - zero_corr) / len(b), 1)}%)")
md.append("")
md.append("## Limitations")
md.append("")
md.append("- Small-sample operational benchmark (n=15 per arm), not a controlled user study.")
md.append("- Timing measured per-arm batch wall-clock; per-item percentiles not applicable.")
md.append("- Reference labels are AI-generated (Codex), not human ground truth.")
md.append("")
Path("eval/codex_agent_benchmark_report.md").write_text(
    "\n".join(md), encoding="utf-8"
)
print(json.dumps(metrics["arms"], indent=2))
print(json.dumps(metrics["comparison"], indent=2))
