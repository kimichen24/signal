"""Fresh holdout evaluation sample (Prompt 05, Phase 1).

Selection uses ONLY non-leaking information:
    period × template-availability × body-length terciles, with
    platform-group round-robin inside each cell for diversity.

Never consulted during selection: AI labels, confidence, needs_review,
cluster membership, priority, AI summaries.

Excluded populations (all previously-used samples):
    - the original 100-issue development dataset (v0.3.3 analyses)
    - the 50-issue workload pilot (eval/workload_pilot_v0.3.4_50.json)
    - the 20-item development diagnostic audit (eval/audit_set_v0.3.3.csv)

Outputs (frozen once generated):
    manifest JSON: seed, exclusions, strata, bounds, issue numbers
    blind CSV:     evidence + parsed deterministic metadata + empty human
                   columns — no AI fields of any kind
"""

from __future__ import annotations

import argparse
import csv
import json
import pathlib
import random
import sys
from collections import defaultdict
from typing import Any

from pipeline.dataset_window import DatasetWindow, WindowError
from pipeline.supabase_client import SupabaseConfigError, SupabaseRest

PERIODS = ("previous", "current")
TEMPLATE_VALUES = ("template", "non_template")
LENGTH_VALUES = ("short", "medium", "long")

PLATFORM_GROUP_RULES = (
    ("windows", "Windows"),
    ("macos", "macOS"),
    ("darwin", "macOS"),
    ("linux", "Linux"),
    ("ubuntu", "Linux"),
    ("debian", "Linux"),
    ("ios", "iOS"),
    ("iphone", "iOS"),
    ("ipad", "iOS"),
    ("android", "Android"),
)

BLIND_COLUMNS = (
    ["github_issue_number", "title", "github_url", "body_clean"]
    + [
        "parsed_version",
        "parsed_subscription",
        "parsed_platform",
        "parsed_actual",
        "parsed_steps",
        "parsed_expected",
        "parsed_additional_info",
        "github_labels",
    ]
    + [
        "human_product_scope",
        "human_issue_type",
        "human_category",
        "human_surface",
        "human_platform",
        "human_severity",
        "human_notes",
    ]
)


def labels_to_names(raw: Any) -> str:
    """github_labels jsonb -> 'bug, app' style readable string."""
    if isinstance(raw, str):
        return raw
    names = []
    for item in raw or []:
        if isinstance(item, dict) and item.get("name"):
            names.append(str(item["name"]))
    return ", ".join(names)


def platform_group(parsed_platform: str | None) -> str:
    text = (parsed_platform or "").lower()
    for token, group in PLATFORM_GROUP_RULES:
        if token in text:
            return group
    return "unknown_or_other"


def length_bounds(values: list[int]) -> tuple[int, int]:
    ordered = sorted(values)
    return ordered[len(ordered) // 3], ordered[(2 * len(ordered)) // 3]


def length_bucket(chars: int, bounds: tuple[int, int]) -> str:
    if chars < bounds[0]:
        return "short"
    if chars < bounds[1]:
        return "medium"
    return "long"


def period_of(created_at: str, boundary: str = "2026-08-30") -> str:
    return "current" if created_at >= boundary else "previous"


def interleave_by_platform(
    members: list[dict[str, Any]], rng: random.Random
) -> list[dict[str, Any]]:
    """Deterministic platform-diverse order: groups shuffled by rng, then
    cycled round-robin so each group contributes evenly."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for m in members:
        groups[platform_group(m.get("parsed_platform"))].append(m)
    for g in groups:
        rng.shuffle(groups[g])
    ordered: list[dict[str, Any]] = []
    keys = sorted(groups)
    while any(groups[g] for g in keys):
        for g in keys:
            if groups[g]:
                ordered.append(groups[g].pop(0))
    return ordered


def select_holdout(
    pool: list[dict[str, Any]],
    excluded_ids: set[str],
    seed: int,
    total: int,
    platform_strata: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng = random.Random(seed)
    candidates = [
        r
        for r in pool
        if r["issue_id"] not in excluded_ids
    ]
    bounds = length_bounds(
        [len(r.get("body_clean") or "") for r in candidates]
    )

    cells: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        platform_part = (
            f"|{platform_group(row.get('parsed_platform'))}"
            if platform_strata
            else ""
        )
        key = (
            f"{period_of(row['github_created_at'])}|"
            f"{'template' if any((row.get(k) or '').strip() for k in ('parsed_actual', 'parsed_version')) else 'non_template'}|"
            f"{length_bucket(len(row.get('body_clean') or ''), bounds)}"
            f"{platform_part}"
        )
        cells[key].append(row)

    # Platform-diverse candidate order per cell, fixed for the allocation.
    ordered_cells = {
        key: interleave_by_platform(cells[key], rng) for key in sorted(cells)
    }

    taken: set[str] = set()
    allocation: dict[str, int] = {}
    remaining = total
    keys = sorted(ordered_cells)
    while remaining > 0:
        progress = False
        for key in keys:
            if remaining <= 0:
                break
            cell_order = ordered_cells[key]
            available = [
                r for r in cell_order if r["issue_id"] not in taken
            ]
            if available:
                picked = available[0]
                taken.add(picked["issue_id"])
                allocation[key] = allocation.get(key, 0) + 1
                remaining -= 1
                progress = True
        if not progress:
            break

    selected = sorted(
        (r for r in candidates if r["issue_id"] in taken),
        key=lambda r: int(r["github_issue_number"]),
    )
    for row in selected:
        row["stratum"] = (
            f"{period_of(row['github_created_at'])}|"
            f"{'template' if any((row.get(k) or '').strip() for k in ('parsed_actual', 'parsed_version')) else 'non_template'}|"
            f"{length_bucket(len(row.get('body_clean') or ''), bounds)}"
        )

    platform_mix = dict(
        Counter := statistics_counter(
            [platform_group(r.get("parsed_platform")) for r in selected]
        )
    )
    meta = {
        "seed": seed,
        "requested": total,
        "selected": len(selected),
        "shortfall": total - len(selected),
        "pool_size": len(candidates),
        "length_bounds": {"short_lt": bounds[0], "medium_lt": bounds[1]},
        "allocation": {k: allocation[k] for k in sorted(allocation)},
        "period_mix": dict(
            statistics_counter(
                [period_of(r["github_created_at"]) for r in selected]
            )
        ),
        "template_mix": dict(
            statistics_counter(
                [
                    "template"
                    if any(
                        (r.get(k) or "").strip()
                        for k in ("parsed_actual", "parsed_version")
                    )
                    else "non_template"
                    for r in selected
                ]
            )
        ),
        "platform_mix": platform_mix,
    }
    return selected, meta


def statistics_counter(values):
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


def load_exclusions(supabase: SupabaseRest, pilot_path: str, audit_path: str):
    """Union of every previously-used sample, by GitHub issue number."""
    excluded_numbers: set[int] = set()
    sources: dict[str, int] = {}

    dev = supabase.select_paged(
        "issue_analysis",
        columns="issues(github_issue_number)",
        filters={"analysis_version": "eq.v0.3.3"},
    )
    for r in dev:
        excluded_numbers.add((r["issues"] or {})["github_issue_number"])
    sources["dev_100"] = len(dev)

    pilot = json.loads(
        pathlib.Path(pilot_path).read_text(encoding="utf-8")
    )
    pilot_numbers = set(pilot["issue_numbers"])
    excluded_numbers |= pilot_numbers
    sources["workload_pilot_50"] = len(pilot_numbers)

    audit_rows = list(
        csv.DictReader(
            open(audit_path, encoding="utf-8-sig", newline="")
        )
    )
    audit_numbers = {
        int(r["github_issue_number"]) for r in audit_rows
    }
    excluded_numbers |= audit_numbers
    sources["dev_diagnostic_audit_20"] = len(audit_numbers)

    return excluded_numbers, sources


def load_exclusions_extended(
    supabase: SupabaseRest,
    pilot_path: str,
    audit_path: str,
    holdout_path: str,
) -> tuple[set[int], dict[str, int]]:
    """All previously-used populations: dev100 + pilot50 + audit20 + holdout50."""
    excluded_numbers, sources = load_exclusions(
        supabase, pilot_path, audit_path
    )
    holdout = json.loads(
        pathlib.Path(holdout_path).read_text(encoding="utf-8")
    )
    holdout_numbers = set(holdout["issue_numbers"])
    excluded_numbers |= holdout_numbers
    sources["holdout_50"] = len(holdout_numbers)
    return excluded_numbers, sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.sample_holdout",
        description="Fresh stratified 50-issue holdout + blind labeling CSV.",
    )
    parser.add_argument("--analysis-version", default="v0.3.4")
    parser.add_argument("--dataset-id", default="codex-14d-2026-09-06")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--total", type=int, default=50)
    parser.add_argument("--start-at", default="2026-08-23T00:00:00Z")
    parser.add_argument("--snapshot-at", default="2026-09-06T00:00:00Z")
    parser.add_argument(
        "--pilot-manifest", default="eval/workload_pilot_v0.3.4_50.json"
    )
    parser.add_argument("--audit-csv", default="eval/audit_set_v0.3.3.csv")
    parser.add_argument(
        "--manifest-out", default="eval/holdout_v0.3.4_manifest.json"
    )
    parser.add_argument(
        "--blind-out", default="eval/holdout_v0.3.4_blind.csv"
    )
    args = parser.parse_args(argv)

    try:
        window = DatasetWindow.from_args(args.start_at, args.snapshot_at)
    except WindowError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        with SupabaseRest.from_env() as supabase:
            rows = supabase.select_paged(
                "issues",
                columns=(
                    "id,github_issue_number,title,github_url,"
                    "github_created_at,body_clean,github_labels,"
                    "parsed_version,parsed_subscription,parsed_platform,"
                    "parsed_actual,parsed_steps,parsed_expected,"
                    "parsed_additional_info"
                ),
                filters=window.postgrest_filters("github_created_at"),
            )
            rows = [{**r, "issue_id": r["id"]} for r in rows]
            excluded_numbers, sources = load_exclusions(
                supabase, args.pilot_manifest, args.audit_csv
            )
    except (SupabaseConfigError, RuntimeError) as exc:
        print(f"Holdout sampling failed: {exc}", file=sys.stderr)
        return 1

    pool = [
        r
        for r in rows
        if r["github_issue_number"] not in excluded_numbers
    ]
    selected, meta = select_holdout(
        pool, excluded_numbers, args.seed, args.total
    )

    manifest = {
        "dataset_id": args.dataset_id,
        "analysis_version_under_evaluation": args.analysis_version,
        "purpose": (
            "fresh 50-item holdout for human evaluation — NEVER to be used "
            "to change prompt/taxonomy/severity rubric/normalization/"
            "thresholds (those were calibrated on the 20-item dev "
            "diagnostic set)"
        ),
        "excluded_populations": {
            "original_development_dataset_100": "v0.3.3-analyzed issues",
            "workload_pilot_50": args.pilot_manifest,
            "dev_diagnostic_audit_20": args.audit_csv,
        },
        "exclusion_counts": sources,
        "pool_after_exclusions": len(pool),
        "stratification": (
            "period x template-availability x body-length terciles; "
            "platform-group round-robin within cells; no AI labels consulted"
        ),
        **meta,
        "issue_numbers": [
            r["github_issue_number"] for r in selected
        ],
        "frozen": True,
    }
    manifest_path = pathlib.Path(args.manifest_out)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    blind_rows = []
    for row in sorted(
        selected, key=lambda r: int(r["github_issue_number"])
    ):
        blind_rows.append(
            {
                "github_issue_number": row["github_issue_number"],
                "title": row.get("title"),
                "github_url": row.get("github_url"),
                "body_clean": row.get("body_clean"),
                "parsed_version": row.get("parsed_version"),
                "parsed_subscription": row.get("parsed_subscription"),
                "parsed_platform": row.get("parsed_platform"),
                "parsed_actual": row.get("parsed_actual"),
                "parsed_steps": row.get("parsed_steps"),
                "parsed_expected": row.get("parsed_expected"),
                "parsed_additional_info": row.get("parsed_additional_info"),
                "github_labels": labels_to_names(row.get("github_labels")),
                "human_product_scope": "",
                "human_issue_type": "",
                "human_category": "",
                "human_surface": "",
                "human_platform": "",
                "human_severity": "",
                "human_notes": "",
            }
        )
    blind_path = pathlib.Path(args.blind_out)
    blind_path.parent.mkdir(parents=True, exist_ok=True)
    with blind_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=BLIND_COLUMNS, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(blind_rows)

    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "blind_csv": str(blind_path),
                "blind_rows": len(blind_rows),
                **{k: v for k, v in meta.items()},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
