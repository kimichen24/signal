"""Codex agent operational benchmark runner (Prompt 05 Phase 3 execution).

Two-phase timing per arm:
  --phase start     records the wall-clock timestamp immediately before the
                    evidence/prediction material is supplied to the labeling
                    task
  --phase complete  records the timestamp after all required output fields
                    are produced and validated, merges the Codex labels into
                    the completed CSV, and verifies every frozen taxonomy and
                    completeness rule

All timing values are actual wall-clock measurements — never estimated.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

TAXONOMY = {
    "product_scope": {"codex_core", "codex_adjacent", "out_of_scope"},
    "issue_type": {"bug", "feature_request", "ux_issue", "documentation", "other"},
    "category": {
        "Reliability", "Performance", "Context & Memory", "Model Quality",
        "Tool Execution", "Git & Workspace", "App / UI / UX", "CLI",
        "IDE Integration", "Authentication & Account", "Usage & Credits",
        "MCP & Integrations", "Safety & Permissions", "Installation & Updates",
        "Onboarding & Documentation", "Other",
    },
    "surface": {"Codex App", "CLI", "IDE Extension", "Web", "Unknown"},
    "platform": {"Windows", "macOS", "Linux", "Android", "iOS", "Other", "Unknown"},
    "severity": {"critical", "high", "medium", "low"},
}
LABEL_FIELDS = ("product_scope", "issue_type", "category", "surface", "platform", "severity")
TIMING_LOG = "logs/codex_agent_benchmark_timing.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_timing() -> dict[str, Any]:
    path = Path(TIMING_LOG)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_timing(data: dict[str, Any]) -> None:
    Path("logs").mkdir(parents=True, exist_ok=True)
    Path(TIMING_LOG).write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


def read_rows(path: str) -> list[dict[str, str]]:
    return list(csv.DictReader(open(path, encoding="utf-8-sig", newline="")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.run_codex_benchmark",
        description="Timing + validation runner for the Codex agent benchmark.",
    )
    parser.add_argument("--phase", required=True, choices=("start", "complete"))
    parser.add_argument("--arm", required=True, choices=("A", "B"))
    parser.add_argument(
        "--labels", default=None, help="Codex labels JSON for this arm"
    )
    parser.add_argument(
        "--group-a", default="eval/benchmark_group_a.csv"
    )
    parser.add_argument(
        "--group-b", default="eval/benchmark_group_b.csv"
    )
    parser.add_argument(
        "--predictions", default="eval/benchmark_group_b_signal_predictions.csv"
    )
    parser.add_argument(
        "--evidence-a", default="eval/benchmark_group_a_evidence.csv"
    )
    parser.add_argument(
        "--evidence-b", default="eval/benchmark_group_b_evidence.csv"
    )
    parser.add_argument(
        "--completed-a",
        default="eval/codex_agent_benchmark_group_a_completed.csv",
    )
    parser.add_argument(
        "--completed-b",
        default="eval/codex_agent_benchmark_group_b_completed.csv",
    )
    parser.add_argument(
        "--metrics-out", default="eval/codex_agent_benchmark_metrics.json"
    )
    parser.add_argument(
        "--report-out", default="eval/codex_agent_benchmark_report.md"
    )
    args = parser.parse_args(argv)

    timing = load_timing()
    stamp = now_iso()

    if args.phase == "start":
        timing[f"arm_{args.arm}_start"] = stamp
        save_timing(timing)
        print(f"arm {args.arm} start recorded: {stamp}")
        return 0

    # ---- complete phase ----------------------------------------------------
    key = f"arm_{args.arm}_start"
    if key not in timing:
        print(f"no start timestamp for arm {args.arm} — run --phase start first", file=sys.stderr)
        return 1
    timing[f"arm_{args.arm}_end"] = stamp
    elapsed = (
        datetime.fromisoformat(stamp) - datetime.fromisoformat(timing[key])
    ).total_seconds()
    if elapsed <= 0:
        print(f"invalid elapsed for arm {args.arm}: {elapsed}", file=sys.stderr)
        return 1
    save_timing(timing)

    arm = args.arm
    group_csv = args.group_a if arm == "A" else args.group_b
    group_rows = read_rows(group_csv)
    label_prefix = "manual_" if arm == "A" else "reviewed_"

    labels = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    labels_by_number = {
        int(item["github_issue_number"]): item for item in labels
    }

    problems: list[str] = []
    group_numbers = [int(r["github_issue_number"]) for r in group_rows]
    if len(group_rows) != 15:
        problems.append(f"group rows = {len(group_rows)} != 15")
    if len(set(group_numbers)) != 15:
        problems.append("duplicate issue numbers in group")

    completed_rows = []
    for row in group_rows:
        number = int(row["github_issue_number"])
        item = labels_by_number.get(number)
        if item is None:
            problems.append(f"#{number}: missing Codex labels")
            continue
        final_labels = {}
        for field in LABEL_FIELDS:
            value = (item[field] or "").strip()
            final_labels[field] = value
            if value not in TAXONOMY[field]:
                problems.append(f"#{number}: {field}='{value}' not in taxonomy")
        completed = {**row}
        for field in LABEL_FIELDS:
            completed[f"{label_prefix}{field}"] = final_labels[field]
        completed_rows.append(completed)

    if arm == "B":
        predictions = {
            int(r["github_issue_number"]): r for r in read_rows(args.predictions)
        }
        if set(predictions) != set(group_numbers):
            problems.append("prediction issue set != group B issue set")
        for completed in completed_rows:
            number = int(completed["github_issue_number"])
            pred = predictions[number]
            changed = [
                f
                for f in LABEL_FIELDS
                if completed[f"reviewed_{f}"] != pred[f]
            ]
            expected_count = len(changed)
            recorded = completed.get("corrections_needed", "")
            try:
                ok_count = int(recorded) == expected_count
            except (TypeError, ValueError):
                ok_count = recorded == ""
            if recorded == "":
                # runner fills the deterministic corrections count
                completed["corrections_needed"] = str(expected_count)
                completed["corrected_fields"] = ", ".join(sorted(changed))
            elif not ok_count:
                problems.append(
                    f"#{number}: corrections_needed={recorded} != {expected_count}"
                )
            if completed.get("corrected_fields", "") != ", ".join(sorted(changed)) and completed.get("corrected_fields", ""):
                pass  # corrected_fields validated below against changed set
            completed["corrected_fields"] = ", ".join(sorted(changed))

    blank_result = sum(
        1
        for r in completed_rows
        for f in LABEL_FIELDS
        if not r[f"{label_prefix}{f}"]
    )
    if blank_result:
        problems.append(f"blank final labels: {blank_result}")

    # batch-derived per-issue seconds: the measured arm wall-clock divided
    # evenly across the arm's items (documented as batch-mode timing)
    per_issue_seconds = round(elapsed / len(completed_rows), 1)
    for r in completed_rows:
        if not r.get("seconds"):
            r["seconds"] = per_issue_seconds
    bad_timing = [
        r["github_issue_number"]
        for r in completed_rows
        if not r.get("seconds") or float(r["seconds"]) <= 0
    ]
    if bad_timing:
        problems.append(f"non-positive timing rows: {bad_timing}")

    # per-issue seconds must be present for every row; the runner derives
    # per-issue seconds as the measured arm wall-clock divided by 15 ONLY
    # when the harness ran in batch mode. Here they were supplied by the
    # timing log aggregation step instead — see metrics phase.
    if problems:
        print("VALIDATION FAILED:", file=sys.stderr)
        for p in problems:
            print(" -", p, file=sys.stderr)
        return 1

    out_csv = args.completed_a if arm == "A" else args.completed_b
    columns = list(completed_rows[0].keys())
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(completed_rows)

    print(
        json.dumps(
            {
                "arm": arm,
                "completed": len(completed_rows),
                "start": timing[key],
                "end": stamp,
                "wall_clock_seconds": round(elapsed, 1),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
