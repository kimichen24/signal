"""Build a lightweight human audit set from a completed analysis version.

Selection (deduplicated, fixed seed for reproducibility):
  A. all needs_review=true issues
  B. random 5 of severity=critical with confidence >= 0.9
  C. random 5 of product_scope=out_of_scope with confidence >= 0.8
  D. random 5 of the remaining issues

AI columns are copied verbatim — this script never modifies analysis
outputs. Human label columns start empty; after labelling, run
pipeline.eval_agreement to compute per-field agreement.

Usage:
  python -m pipeline.audit_set --analysis-version v0.3.3 --seed 42 \
      --out eval/audit_set_v0.3.3.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

from pipeline.supabase_client import SupabaseConfigError, SupabaseRest

AUDIT_FIELDS = (
    "product_scope",
    "issue_type",
    "category",
    "surface",
    "platform",
    "severity",
)

CSV_COLUMNS = (
    ["github_issue_number", "audit_group", "title", "github_url", "state",
     "github_created_at"]
    + ["parsed_version", "parsed_subscription", "parsed_platform",
       "parsed_actual", "parsed_steps", "parsed_expected",
       "parsed_additional_info", "github_labels", "body_clean"]
    + [f"ai_{f}" for f in AUDIT_FIELDS]
    + ["ai_confidence", "ai_scope_confidence", "ai_summary"]
    + [f"human_{f}" for f in AUDIT_FIELDS]
    + ["reviewer_note"]
)


def select_audit_items(
    analyses: list[dict[str, Any]], seed: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Deterministically pick the audit groups. Returns (rows, stats).

    Candidate pools are sorted before sampling so a fixed seed always
    yields the same issues. Pools smaller than the group size are taken
    in full and reported as shortfalls — the script never invents data.
    """
    rng = random.Random(seed)
    rows = sorted(
        analyses,
        key=lambda r: (int(r["github_issue_number"]), r["issue_id"]),
    )
    taken: dict[str, str] = {}

    def sample(
        pool: list[dict[str, Any]], size: int, group: str
    ) -> list[dict[str, Any]]:
        eligible = [r for r in pool if r["issue_id"] not in taken]
        picked = [
            {**r, "audit_group": group}
            for r in rng.sample(eligible, min(size, len(eligible)))
        ]
        for r in picked:
            taken[r["issue_id"]] = group
        return picked

    group_a = [
        {**r, "audit_group": "needs_review"}
        for r in rows
        if r["needs_review"]
    ]
    for r in group_a:
        taken[r["issue_id"]] = "needs_review"

    b_pool = [
        r
        for r in rows
        if r["severity"] == "critical" and float(r["confidence"]) >= 0.9
    ]
    group_b = sample(b_pool, 5, "critical_high_confidence")

    c_pool = [
        r
        for r in rows
        if r["product_scope"] == "out_of_scope"
        and float(r["confidence"]) >= 0.8
    ]
    group_c = sample(c_pool, 5, "out_of_scope_high_confidence")

    d_pool = rows
    group_d = sample(d_pool, 5, "remaining")

    stats = {
        "seed": seed,
        "pools": {
            "needs_review": len(group_a),
            "critical_conf_ge_0_9": len(b_pool),
            "out_of_scope_conf_ge_0_8": len(c_pool),
            "remaining": len(rows) - len(taken) + len(group_d),
        },
        "taken": {
            "needs_review": len(group_a),
            "critical_high_confidence": len(group_b),
            "out_of_scope_high_confidence": len(group_c),
            "remaining": len(group_d),
        },
        "unique_total": len(taken),
    }
    ordered = sorted(
        (group_a + group_b + group_c + group_d),
        key=lambda r: (
            ["needs_review", "critical_high_confidence",
             "out_of_scope_high_confidence", "remaining"].index(
                 taken[r["issue_id"]]
             ),
            int(r["github_issue_number"]),
        ),
    )
    return ordered, stats


def select_flatten(row: dict[str, Any]) -> dict[str, Any]:
    """Merge the nested issues(...) join fields to the top level so
    selection sees github_issue_number directly."""
    out = dict(row)
    issue = row.get("issues") or {}
    for key in (
        "github_issue_number",
        "title",
        "github_url",
        "state",
        "github_created_at",
        "body_clean",
        "github_labels",
        "parsed_version",
        "parsed_subscription",
        "parsed_platform",
        "parsed_actual",
        "parsed_steps",
        "parsed_expected",
        "parsed_additional_info",
    ):
        out[key] = issue.get(key)
    return out


def flatten(row: dict[str, Any]) -> dict[str, Any]:
    issue = row.get("issues") or {}
    labels = ", ".join(
        label.get("name", "")
        for label in (issue.get("github_labels") or [])
        if isinstance(label, dict) and label.get("name")
    )
    flat = {
        "github_issue_number": issue.get("github_issue_number"),
        "audit_group": row.get("audit_group"),
        "title": issue.get("title"),
        "github_url": issue.get("github_url"),
        "state": issue.get("state"),
        "github_created_at": issue.get("github_created_at"),
        "body_clean": issue.get("body_clean"),
        "github_labels": labels,
        "ai_summary": row.get("summary"),
        "ai_confidence": row.get("confidence"),
        "ai_scope_confidence": row.get("scope_confidence"),
    }
    for parsed in (
        "parsed_version",
        "parsed_subscription",
        "parsed_platform",
        "parsed_actual",
        "parsed_steps",
        "parsed_expected",
        "parsed_additional_info",
    ):
        flat[parsed] = issue.get(parsed)
    for field in AUDIT_FIELDS:
        flat[f"ai_{field}"] = row.get(field)
        flat[f"human_{field}"] = None
    flat["reviewer_note"] = None
    return flat


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so Excel opens non-ASCII titles correctly.
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def make_blind(reference_path: Path, blind_path: Path) -> int:
    """Derive a blind-review CSV: drop every ai_* column so labellers see
    only the issue material. The reference file is never modified."""
    with reference_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    kept = [c for c in columns if not c.startswith("ai_")]
    blind_path.parent.mkdir(parents=True, exist_ok=True)
    with blind_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=kept, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def make_blind_final(
    reference_path: Path, blind_path: Path, seed: int = 42
) -> int:
    """Final human-labelling file: no ai_* columns AND no audit_group
    (group names like needs_review / out_of_scope_high_confidence leak AI
    information). Rows are shuffled with a fixed seed so the stratified
    grouping is not visually apparent; github_issue_number is preserved as
    the join key. The reference file is never modified."""
    with reference_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        rows = list(reader)
    kept = [
        c
        for c in columns
        if not c.startswith("ai_") and c != "audit_group"
    ]
    shuffled = list(rows)
    random.Random(seed).shuffle(shuffled)
    blind_path.parent.mkdir(parents=True, exist_ok=True)
    with blind_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=kept, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(shuffled)
    return len(shuffled)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.audit_set",
        description="Build the 20-item human audit set CSV.",
    )
    parser.add_argument(
        "--blind-from",
        default=None,
        help="derive a blind review CSV (ai_* columns stripped) from an "
        "existing audit CSV instead of building a new set",
    )
    parser.add_argument(
        "--blind-final-from",
        default=None,
        help="derive the final human-labelling CSV from an existing audit "
        "CSV: ai_* columns and audit_group removed, rows shuffled with "
        "--seed",
    )
    parser.add_argument(
        "--analysis-version",
        default=os.environ.get("SIGNAL_ANALYSIS_VERSION", "v0.3.3"),
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default=None, help="output CSV path")
    args = parser.parse_args(argv)

    if args.blind_final_from:
        source = Path(args.blind_final_from)
        target = (
            Path(args.out)
            if args.out
            else source.with_name(source.stem + "_blind_final.csv")
        )
        if not source.exists():
            print(f"file not found: {source}", file=sys.stderr)
            return 1
        count = make_blind_final(source, target, seed=args.seed)
        print(
            json.dumps(
                {
                    "out": str(target),
                    "rows": count,
                    "removed": ["ai_*", "audit_group"],
                    "shuffled_seed": args.seed,
                }
            )
        )
        return 0

    if args.blind_from:
        source = Path(args.blind_from)
        target = (
            Path(args.out)
            if args.out
            else source.with_name(source.stem + "_blind.csv")
        )
        if not source.exists():
            print(f"file not found: {source}", file=sys.stderr)
            return 1
        count = make_blind(source, target)
        print(
            json.dumps(
                {"out": str(target), "rows": count, "removed": "ai_*"}
            )
        )
        return 0

    out_path = Path(
        args.out or f"eval/audit_set_{args.analysis_version}.csv"
    )

    try:
        with SupabaseRest.from_env() as supabase:
            analyses = supabase.select(
                "issue_analysis",
                columns=(
                    "issue_id,product_scope,issue_type,category,surface,"
                    "platform,severity,confidence,needs_review,summary,"
                    "issues(github_issue_number,title,github_url,state,"
                    "github_created_at,body_clean,github_labels,"
                    "parsed_version,parsed_subscription,parsed_platform,"
                    "parsed_actual,parsed_steps,parsed_expected,"
                    "parsed_additional_info)"
                ),
                filters={"analysis_version": f"eq.{args.analysis_version}"},
                limit=1000,
            )
    except (SupabaseConfigError, RuntimeError) as exc:
        print(f"Audit set build failed: {exc}", file=sys.stderr)
        return 1

    selected, stats = select_audit_items(
        [select_flatten(r) for r in analyses], args.seed
    )
    write_csv(out_path, [flatten(r) for r in selected])
    print(json.dumps({"out": str(out_path), **stats}, indent=2))
    for row in selected:
        print(
            f"  [{row.get('audit_group')}] #{row['github_issue_number']} "
            f"{row['title'][:70]}"
        )
    return 0


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
