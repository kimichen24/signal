"""Build a reproducible stratified workload pilot sample (Prompt 03 → 04 bridge).

Selects issues from a dataset window that do NOT yet have a successful
analysis for the target version, stratified by:
    period (previous/current) × template (yes/no) × body length (short/medium/long)

Length tercile bounds are computed from the eligible pool and saved with the
sample so the split is exactly reproducible. Selection never looks at labels
(scope/category/severity do not exist yet at this stage).

Usage:
  python -m pipeline.sample_workload --analysis-version v0.3.4 \
      --dataset-id codex-14d-2026-09-06 --seed 42 --total 50 \
      --out eval/workload_pilot_v0.3.4_50.json
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from typing import Any

from pipeline.dataset_window import DatasetWindow, WindowError
from pipeline.supabase_client import SupabaseConfigError, SupabaseRest

PERIODS = ("previous", "current")
TEMPLATE_VALUES = ("template", "non_template")
LENGTH_VALUES = ("short", "medium", "long")


def length_bounds(values: list[int]) -> tuple[int, int]:
    """Tercile cut points (exclusive upper bounds for short/medium)."""
    ordered = sorted(values)
    short_cut = ordered[len(ordered) // 3]
    medium_cut = ordered[(2 * len(ordered)) // 3]
    return short_cut, medium_cut


def length_bucket(chars: int, bounds: tuple[int, int]) -> str:
    short_cut, medium_cut = bounds
    if chars < short_cut:
        return "short"
    if chars < medium_cut:
        return "medium"
    return "long"


def stratified_sample(
    pool: list[dict[str, Any]], seed: int, total: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Deterministic stratified selection. Returns (selected, meta).

    Quotas: base = total // cells, remainder distributed round-robin over
    the cells with the largest unfilled demand (deterministic order).
    Cells with fewer candidates than their quota give everything back and
    the deficit is redistributed by the same rule.
    """
    if not pool:
        return [], {"seed": seed, "requested": total, "selected": 0,
                    "shortfall": total, "cells": {}}

    bounds = length_bounds(
        [len(r.get("body_clean") or "") for r in pool]
    )

    def cell_of(row: dict[str, Any]) -> str:
        period = (
            "current"
            if row["github_created_at"] >= "2026-08-30"
            else "previous"
        )  # dataset window guarantees created_at < snapshot; ISO compares fine
        template = "template" if (
            (row.get("parsed_actual") or "").strip()
            or (row.get("parsed_version") or "").strip()
        ) else "non_template"
        length = length_bucket(len(row.get("body_clean") or ""), bounds)
        return f"{period}|{template}|{length}"

    cells: dict[str, list[dict[str, Any]]] = defaultdict_cells(pool, cell_of)
    cell_keys = sorted(
        f"{p}|{t}|{l}"
        for p in PERIODS
        for t in TEMPLATE_VALUES
        for l in LENGTH_VALUES
        if f"{p}|{t}|{l}" in cells
    )

    rng = random.Random(seed)
    taken: set[str] = set()
    allocation: dict[str, int] = {key: 0 for key in cell_keys}

    remaining = total
    while remaining > 0:
        # Round-robin: each pass gives at most one slot per cell (largest
        # remaining pool first, deterministic), so strata fill evenly
        # before any cell is drawn down.
        progress = False
        for key in sorted(
            cell_keys,
            key=lambda k: (
                -len([r for r in cells[k] if r["issue_id"] not in taken]),
                k,
            ),
        ):
            if remaining <= 0:
                break
            available = [
                r for r in cells[key] if r["issue_id"] not in taken
            ]
            if available:
                picked = rng.sample(available, 1)[0]
                taken.add(picked["issue_id"])
                allocation[key] += 1
                remaining -= 1
                progress = True
        if not progress:
            break  # every cell exhausted

    selected = sorted(
        (r for r in pool if r["issue_id"] in taken),
        key=lambda r: int(r["github_issue_number"]),
    )
    for row in selected:
        row["stratum"] = cell_of(row)
    meta = {
        "seed": seed,
        "requested": total,
        "selected": len(selected),
        "shortfall": total - len(selected),
        "length_bounds": {"short_lt": bounds[0], "medium_lt": bounds[1]},
        "allocation": {k: allocation[k] for k in sorted(allocation)},
        "pool_size": len(pool),
    }
    return selected, meta


def defaultdict_cells(pool, cell_of):
    cells: dict[str, list[dict[str, Any]]] = {}
    for row in pool:
        cells.setdefault(cell_of(row), []).append(row)
    return cells


def load_pool(
    supabase: SupabaseRest, window: DatasetWindow, version: str
) -> list[dict[str, Any]]:
    """Dataset-window issues without a successful analysis for `version`."""
    rows = supabase.select_paged(
        "issues",
        columns=(
            "id,github_issue_number,github_created_at,body_clean,"
            "parsed_actual,parsed_version"
        ),
        filters=window.postgrest_filters("github_created_at"),
    )
    rows = [{**r, "issue_id": r["id"]} for r in rows]
    analyzed = supabase.select_paged(
        "issue_analysis",
        columns="issue_id,analysis_error",
        filters={"analysis_version": f"eq.{version}"},
    )
    ok_ids = {
        r["issue_id"] for r in analyzed if not r.get("analysis_error")
    }
    return [r for r in rows if r["issue_id"] not in ok_ids]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.sample_workload",
        description="Reproducible stratified workload pilot sample.",
    )
    parser.add_argument("--analysis-version", default="v0.3.4")
    parser.add_argument("--dataset-id", default="codex-14d-2026-09-06")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--total", type=int, default=50)
    parser.add_argument(
        "--start-at", default="2026-08-23T00:00:00Z"
    )
    parser.add_argument(
        "--snapshot-at", default="2026-09-06T00:00:00Z"
    )
    parser.add_argument(
        "--out", default="eval/workload_pilot_v0.3.4_50.json"
    )
    args = parser.parse_args(argv)

    try:
        window = DatasetWindow.from_args(args.start_at, args.snapshot_at)
    except WindowError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        with SupabaseRest.from_env() as supabase:
            pool = load_pool(supabase, window, args.analysis_version)
    except (SupabaseConfigError, RuntimeError) as exc:
        print(f"Sampling failed: {exc}", file=sys.stderr)
        return 1

    selected, meta = stratified_sample(pool, args.seed, args.total)
    payload = {
        "dataset_id": args.dataset_id,
        "analysis_version": args.analysis_version,
        "repository": "openai/codex",
        "window": window.describe(),
        "purpose": "50-issue real MiMo workload pilot (reproducible)",
        **meta,
        "issue_numbers": [r["github_issue_number"] for r in selected],
        "rows": [
            {
                "github_issue_number": r["github_issue_number"],
                "stratum": r["stratum"],
                "body_clean_chars": len(r.get("body_clean") or ""),
                "template": r["stratum"].split("|")[1],
                "period": r["stratum"].split("|")[0],
            }
            for r in selected
        ],
    }
    out_path = args.out
    import pathlib

    pathlib.Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
