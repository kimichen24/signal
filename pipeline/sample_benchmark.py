"""Efficiency benchmark — two disjoint matched arms (Prompt 05 Phase 3).

Arm A (manual):        15 fresh issues, triaged from scratch — the
                       reviewer determines all six frozen Signal labels from
                       raw evidence WITHOUT viewing Signal predictions.
Arm B (signal_review): 15 DIFFERENT fresh issues, matched to Arm A on
                       period, template availability, body-length bucket and
                       platform group — the reviewer starts from Signal's
                       existing structured output and verifies/corrects it.

Same-issue carryover (manual → review of the same issue) is explicitly
avoided: the arms share zero issues. Assignment is seed-frozen and saved in
eval/benchmark_manifest.json. Timings are never fabricated.
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import random
import sys
import time
from collections import defaultdict
from typing import Any

from pipeline.dataset_window import DatasetWindow, WindowError
from pipeline.sample_holdout import (
    interleave_by_platform,
    labels_to_names,
    length_bounds,
    length_bucket,
    load_exclusions_extended,
    platform_group,
    period_of,
)
from pipeline.supabase_client import SupabaseConfigError, SupabaseRest

GROUP_A_COLUMNS = (
    "github_issue_number",
    "title",
    "benchmark_arm",
    "start_time",
    "end_time",
    "seconds",
    "manual_product_scope",
    "manual_issue_type",
    "manual_category",
    "manual_surface",
    "manual_platform",
    "manual_severity",
    "notes",
)
GROUP_B_COLUMNS = (
    "github_issue_number",
    "title",
    "benchmark_arm",
    "start_time",
    "end_time",
    "seconds",
    "reviewed_product_scope",
    "reviewed_issue_type",
    "reviewed_category",
    "reviewed_surface",
    "reviewed_platform",
    "reviewed_severity",
    "corrections_needed",
    "corrected_fields",
    "notes",
)
SIGNAL_PREDICTION_COLUMNS = (
    "github_issue_number",
    "product_scope",
    "issue_type",
    "category",
    "surface",
    "platform",
    "severity",
)
EVIDENCE_COLUMNS = (
    "github_issue_number",
    "title",
    "github_url",
    "body_clean",
    "parsed_version",
    "parsed_subscription",
    "parsed_platform",
    "parsed_actual",
    "parsed_steps",
    "parsed_expected",
    "parsed_additional_info",
    "github_labels",
)


def build_cells(
    pool: list[dict[str, Any]], rng: random.Random
) -> dict[str, list[dict[str, Any]]]:
    """4-factor matching cells: period | template | length | platform_group,
    each in deterministic platform-diverse order."""
    bounds = length_bounds([len(r.get("body_clean") or "") for r in pool])
    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(pool, key=lambda r: int(r["github_issue_number"])):
        template = (
            "template"
            if any(
                (row.get(k) or "").strip()
                for k in ("parsed_actual", "parsed_version")
            )
            else "non_template"
        )
        key = (
            f"{period_of(row['github_created_at'])}|{template}|"
            f"{length_bucket(len(row.get('body_clean') or ''), bounds)}|"
            f"{platform_group(row.get('parsed_platform'))}"
        )
        cells[key].append(row)
    return {k: interleave_by_platform(v, rng) for k, v in cells.items()}


def select_matched_arms(
    pool: list[dict[str, Any]],
    excluded_ids: set[int],
    seed: int,
    per_arm: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Pick per_arm matched pairs: both members of a pair come from the SAME
    matching cell (period/template/length/platform), arm A takes the first,
    arm B the second. Round-robin over cells keeps factor balance."""
    rng = random.Random(seed)
    candidates = sorted(
        (r for r in pool if int(r["github_issue_number"]) not in excluded_ids),
        key=lambda r: int(r["github_issue_number"]),
    )
    cells = build_cells(candidates, rng)

    arm_a: list[dict[str, Any]] = []
    arm_b: list[dict[str, Any]] = []
    assigned: set[int] = set()
    pairs: list[dict[str, Any]] = []

    multi_cells = sorted(k for k in cells if len(cells[k]) >= 2)
    queue = list(multi_cells)
    index = 0

    def available_in(k: str) -> list[dict[str, Any]]:
        return [
            r
            for r in cells[k]
            if int(r["github_issue_number"]) not in assigned
        ]

    while len(arm_a) < per_arm or len(arm_b) < per_arm:
        remaining_cells = [k for k in queue if len(available_in(k)) > 0]
        if not remaining_cells:
            break
        key = remaining_cells[index % len(remaining_cells)]
        index += 1
        order = available_in(key)
        if len(order) < 2:
            continue
        first, second = order[0], order[1]
        arm_a.append({**first, "benchmark_arm": "manual"})
        arm_b.append({**second, "benchmark_arm": "signal_review"})
        assigned.add(int(first["github_issue_number"]))
        assigned.add(int(second["github_issue_number"]))
        pairs.append(
            {
                "cell": key,
                "issue_a": first["github_issue_number"],
                "issue_b": second["github_issue_number"],
            }
        )

    # balance arms from cells with a single remaining candidate
    singles = sorted(
        (
            k
            for k in cells
            if len(available_in(k)) == 1
            and int(cells[k][0]["github_issue_number"]) not in assigned
        ),
        reverse=True,
    )
    for k in singles:
        if len(arm_a) >= per_arm and len(arm_b) >= per_arm:
            break
        row = available_in(k)[0]
        target = arm_a if len(arm_a) <= len(arm_b) else arm_b
        arm_name = "manual" if target is arm_a else "signal_review"
        target.append({**row, "benchmark_arm": arm_name})
        assigned.add(int(row["github_issue_number"]))

    return arm_a, arm_b, pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.sample_benchmark",
        description="Two-arm efficiency benchmark assignment (no fabricated timings).",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--per-arm", type=int, default=15)
    parser.add_argument("--dataset-id", default="codex-14d-2026-09-06")
    parser.add_argument("--analysis-version", default="v0.3.4")
    parser.add_argument("--start-at", default="2026-08-23T00:00:00Z")
    parser.add_argument("--snapshot-at", default="2026-09-06T00:00:00Z")
    parser.add_argument(
        "--pilot-manifest", default="eval/workload_pilot_v0.3.4_50.json"
    )
    parser.add_argument("--audit-csv", default="eval/audit_set_v0.3.3.csv")
    parser.add_argument(
        "--holdout-manifest", default="eval/holdout_v0.3.4_manifest.json"
    )
    parser.add_argument("--group-a-out", default="eval/benchmark_group_a.csv")
    parser.add_argument("--group-b-out", default="eval/benchmark_group_b.csv")
    parser.add_argument(
        "--group-a-evidence-out",
        default="eval/benchmark_group_a_evidence.csv",
    )
    parser.add_argument(
        "--group-b-evidence-out",
        default="eval/benchmark_group_b_evidence.csv",
    )
    parser.add_argument(
        "--group-b-predictions-out",
        default="eval/benchmark_group_b_signal_predictions.csv",
    )
    parser.add_argument(
        "--manifest-out", default="eval/benchmark_manifest.json"
    )
    args = parser.parse_args(argv)
    started = time.monotonic()

    from pipeline.supabase_client import load_env

    load_env()

    try:
        window = DatasetWindow.from_args(args.start_at, args.snapshot_at)
        with SupabaseRest.from_env() as supabase:
            excluded, sources = load_exclusions_extended(
                supabase,
                args.pilot_manifest,
                args.audit_csv,
                args.holdout_manifest,
            )
            rows = supabase.select_paged(
                "issues",
                columns=(
                    "id,github_issue_number,title,github_created_at,"
                    "body_clean,github_labels,parsed_version,"
                    "parsed_subscription,parsed_platform,parsed_actual,"
                    "parsed_steps,parsed_expected,parsed_additional_info"
                ),
                filters=window.postgrest_filters("github_created_at"),
            )
            rows = [{**r, "issue_id": r["id"]} for r in rows]
            analyses = supabase.select_paged(
                "issue_analysis",
                columns=(
                    "issues(github_issue_number),product_scope,issue_type,"
                    "category,surface,platform,severity"
                ),
                filters={"analysis_version": f"eq.{args.analysis_version}"},
            )
    except (SupabaseConfigError, RuntimeError) as exc:
        print(f"Benchmark sampling failed: {exc}", file=sys.stderr)
        return 1

    pool = [r for r in rows if r["github_issue_number"] not in excluded]
    arm_a, arm_b, pairs = select_matched_arms(
        pool, excluded, args.seed, args.per_arm
    )

    predictions_by_number = {
        (r["issues"] or {}).get("github_issue_number"): {
            "product_scope": r.get("product_scope") or "",
            "issue_type": r.get("issue_type") or "",
            "category": r.get("category") or "",
            "surface": r.get("surface") or "",
            "platform": r.get("platform") or "",
            "severity": r.get("severity") or "",
        }
        for r in analyses
    }

    out_dir = pathlib.Path("eval")
    out_dir.mkdir(parents=True, exist_ok=True)

    def write_group(
        path: pathlib.Path,
        columns: tuple[str, ...],
        rows: list[dict[str, Any]],
        arm: str,
    ) -> None:
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(columns))
            writer.writeheader()
            for row in sorted(
                rows, key=lambda r: int(r["github_issue_number"])
            ):
                record = {col: "" for col in columns}
                record["github_issue_number"] = row["github_issue_number"]
                record["title"] = row.get("title") or ""
                record["benchmark_arm"] = arm
                writer.writerow(record)

    def write_evidence(
        path: pathlib.Path, rows: list[dict[str, Any]]
    ) -> None:
        """Evidence pack: identical schema for both arms, zero AI fields."""
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=list(EVIDENCE_COLUMNS), extrasaction="ignore"
            )
            writer.writeheader()
            for row in sorted(
                rows, key=lambda r: int(r["github_issue_number"])
            ):
                record = {col: row.get(col) or "" for col in EVIDENCE_COLUMNS}
                record["github_labels"] = labels_to_names(
                    row.get("github_labels")
                )
                writer.writerow(record)

    write_group(
        pathlib.Path(args.group_a_out), GROUP_A_COLUMNS, arm_a, "manual"
    )
    write_group(
        pathlib.Path(args.group_b_out), GROUP_B_COLUMNS, arm_b, "signal_review"
    )
    write_evidence(pathlib.Path(args.group_a_evidence_out), arm_a)
    write_evidence(pathlib.Path(args.group_b_evidence_out), arm_b)

    with pathlib.Path(args.group_b_predictions_out).open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(SIGNAL_PREDICTION_COLUMNS)
        )
        writer.writeheader()
        for row in sorted(arm_b, key=lambda r: int(r["github_issue_number"])):
            record = {"github_issue_number": row["github_issue_number"]}
            record.update(
                predictions_by_number.get(
                    row["github_issue_number"],
                    {col: "" for col in SIGNAL_PREDICTION_COLUMNS[1:]},
                )
            )
            writer.writerow(record)

    # Deterministic interleaved execution order: alternate which arm goes
    # first for each matched pair (pair 1: A→B, pair 2: B→A, ...).
    execution_order = []
    step = 0
    for index, pair in enumerate(pairs, start=1):
        arms = ("A", "B") if index % 2 == 1 else ("B", "A")
        for arm in arms:
            step += 1
            source = arm_a if arm == "A" else arm_b
            match = next(
                r
                for r in source
                if r["github_issue_number"] == pair["issue_a"]
                or r["github_issue_number"] == pair["issue_b"]
            )
            execution_order.append(
                {
                    "step": step,
                    "pair_index": index,
                    "arm": arm,
                    "github_issue_number": match["github_issue_number"],
                }
            )

    period_mix: dict[str, int] = {}
    for r in arm_a + arm_b:
        p = period_of(r["github_created_at"])
        period_mix[p] = period_mix.get(p, 0) + 1

    manifest = {
        "dataset_id": args.dataset_id,
        "purpose": (
            "efficiency benchmark with two disjoint matched arms — Arm A: "
            "manual triage from scratch; Arm B: review of Signal's "
            "pre-structured output. Same-issue carryover is explicitly "
            "avoided. Timings must be measured, never fabricated."
        ),
        "matching_factors": (
            "period, template availability, body-length bucket, platform "
            "group — each pair comes from the same matching cell"
        ),
        "seed": args.seed,
        "per_arm": args.per_arm,
        "pairs": pairs,
        "excluded_populations": sources,
        "pool_after_exclusions": len(pool),
        "period_mix_actual": period_mix,
        "note_fix1": (
            "period_mix is reported exactly as selected; period balance is "
            "not required for this efficiency benchmark"
        ),
        "group_a_file": args.group_a_out,
        "group_b_file": args.group_b_out,
        "group_a_evidence": args.group_a_evidence_out,
        "group_b_evidence": args.group_b_evidence_out,
        "group_b_signal_predictions": args.group_b_predictions_out,
        "execution_order": execution_order,
        "timing_rule": (
            "start_time begins immediately before opening/reading the "
            "evidence for that issue; end_time only after all six final "
            "labels are entered. Interrupted rows are marked invalid and "
            "documented — never time-estimated."
        ),
    }
    pathlib.Path(args.manifest_out).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # ---- pre-execution verification ---------------------------------------
    def read_csv_rows(csv_path: str):
        return list(
            csv.DictReader(open(csv_path, encoding="utf-8-sig", newline=""))
        )

    a_rows = read_csv_rows(args.group_a_out)
    b_rows = read_csv_rows(args.group_b_out)
    a_numbers = {int(r["github_issue_number"]) for r in a_rows}
    b_numbers = {int(r["github_issue_number"]) for r in b_rows}
    checks = {
        "group_a_15": len(a_rows) == args.per_arm,
        "group_b_15": len(b_rows) == args.per_arm,
        "zero_overlap": not (a_numbers & b_numbers),
        "arms_labeled": (
            {r["benchmark_arm"] for r in a_rows} == {"manual"}
            and {r["benchmark_arm"] for r in b_rows} == {"signal_review"}
        ),
        "manual_label_fields_blank": all(
            not r[f"manual_{f}"]
            for r in a_rows
            for f in (
                "product_scope",
                "issue_type",
                "category",
                "surface",
                "platform",
                "severity",
            )
        ),
        "reviewed_fields_blank": all(
            not r[f"reviewed_{f}"]
            for r in b_rows
            for f in (
                "product_scope",
                "issue_type",
                "category",
                "surface",
                "platform",
                "severity",
            )
        ),
        "timing_fields_blank": all(
            not r[c]
            for r in a_rows + b_rows
            for c in ("start_time", "end_time", "seconds")
        ),
        "correction_fields_blank": all(
            not r["corrections_needed"] and not r["corrected_fields"]
            for r in b_rows
        ),
        "evidence_schemas_identical": (
            list(
                csv.DictReader(
                    open(args.group_a_evidence_out, encoding="utf-8-sig", newline="")
                )
            )[0].keys()
            == list(
                csv.DictReader(
                    open(args.group_b_evidence_out, encoding="utf-8-sig", newline="")
                )
            )[0].keys()
        ),
        "prediction_issue_set_matches_b_evidence": (
            {
                int(r["github_issue_number"])
                for r in read_csv_rows(args.group_b_predictions_out)
            }
            == b_numbers
        ),
    }
    if not all(checks.values()):
        failed = [k for k, v in checks.items() if not v]
        print(
            json.dumps({"verification": checks}, indent=2),
            file=sys.stderr,
        )
        print(
            f"VERIFICATION FAILED — not execution-ready: {failed}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "group_a": args.group_a_out,
                "group_b": args.group_b_out,
                "group_a_evidence": args.group_a_evidence_out,
                "group_b_evidence": args.group_b_evidence_out,
                "group_b_predictions": args.group_b_predictions_out,
                "pairs": len(pairs),
                "arm_sizes": {"A_manual": len(arm_a), "B_signal_review": len(arm_b)},
                "zero_overlap": True,
                "period_mix_actual": period_mix,
                "exclusions": sources,
                "verification": "all checks pass",
                "runtime_seconds": round(time.monotonic() - started, 1),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
