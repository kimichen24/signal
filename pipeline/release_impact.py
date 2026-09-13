"""Release impact — deterministic before/after windows (Prompt 04).

For each seeded release: clip the non-overlapping before/after windows
to the dataset bounds, compute coverage days per side, and mark the
comparison sufficient only when both sides meet the minimum coverage
days.  Correlation only — this module never claims causation.

Window semantics (corrected v0.2):
  before: [max(dataset_start, release_date - window_days), release_date)
  after:  [release_date, min(dataset_end, release_date + window_days))

The v0.1 implementation used identical ±window_days ranges for both
sides, producing before_count == after_count for every cluster.  Those
rows are superseded by v0.2.

For sufficient releases: total in-scope feedback before/after plus
per-cluster before/after counts with new/increased/decreased/stable
classification, persisted to release_impacts.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

MIN_COVERAGE_DAYS = 5.0
CALC_VERSION = "v0.2"


def clipped_before_window(
    release_date: datetime, days: int, ds_start: datetime, ds_end: datetime
) -> tuple[datetime, datetime, float]:
    """Before window: [max(ds_start, release - days), release).
    Returns (start, end, coverage_days)."""
    raw_start = release_date - timedelta(days=days)
    start = max(raw_start, ds_start)
    end = min(release_date, ds_end)
    coverage = (end - start).total_seconds() / 86400.0
    return start, end, max(coverage, 0.0)


def clipped_after_window(
    release_date: datetime, days: int, ds_start: datetime, ds_end: datetime
) -> tuple[datetime, datetime, float]:
    """After window: [release, min(ds_end, release + days)).
    Returns (start, end, coverage_days)."""
    raw_end = release_date + timedelta(days=days)
    start = max(release_date, ds_start)
    end = min(raw_end, ds_end)
    coverage = (end - start).total_seconds() / 86400.0
    return start, end, max(coverage, 0.0)


def signal_type(before: int, after: int) -> str:
    if before == 0 and after > 0:
        return "new"
    if after > before:
        return "increased"
    if after < before:
        return "decreased"
    return "stable"


def change_rate(before: int, after: int) -> float | None:
    if before <= 0:
        return None  # no baseline — never report +inf or +100%
    return round((after - before) / before, 3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.release_impact",
        description="Deterministic release before/after impact (Prompt 04).",
    )
    parser.add_argument(
        "--analysis-version",
        default=os.environ.get("SIGNAL_ANALYSIS_VERSION", "v0.3.4"),
    )
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument(
        "--dataset-start", default="2026-08-23T00:00:00Z"
    )
    parser.add_argument(
        "--dataset-end", default="2026-09-06T00:00:00Z"
    )
    parser.add_argument(
        "--min-coverage-days", type=float, default=MIN_COVERAGE_DAYS
    )
    args = parser.parse_args(argv)
    started = time.monotonic()

    from pipeline.supabase_client import (
        SupabaseConfigError,
        SupabaseRest,
        load_env,
    )

    try:
        with SupabaseRest.from_env() as supabase:
            ds_start = datetime.fromisoformat(
                args.dataset_start.replace("Z", "+00:00")
            )
            ds_end = datetime.fromisoformat(
                args.dataset_end.replace("Z", "+00:00")
            )
            releases = supabase.select_paged(
                "releases",
                columns="id,name,release_date,source_url",
                order="release_date",
            )
            # in-scope issues only, with created_at
            in_scope = supabase.select_paged(
                "issue_analysis",
                columns="issue_id,product_scope,issues(github_created_at)",
                filters={
                    "analysis_version": f"eq.{args.analysis_version}",
                    "product_scope": "neq.out_of_scope",
                },
            )
            in_scope_times = [
                (
                    (r.get("issues") or {}).get("github_created_at") or ""
                ).replace("Z", "+00:00")
                for r in in_scope
            ]
            in_scope_times = [t for t in in_scope_times if t]
            in_scope_dt = [
                datetime.fromisoformat(t) for t in in_scope_times
            ]

            clusters = supabase.select_paged(
                "clusters",
                columns="id,cluster_name,category",
                filters={"analysis_version": f"eq.{args.analysis_version}"},
            )
            member_rows = supabase.select_paged(
                "cluster_members", columns="cluster_id,issue_id"
            )
            created_by_pk = {}
            for r in supabase.select_paged(
                "issue_analysis",
                columns="issue_id,issues(github_created_at)",
                filters={"analysis_version": f"eq.{args.analysis_version}"},
            ):
                created = (r.get("issues") or {}).get("github_created_at")
                if created:
                    created_by_pk[r["issue_id"]] = datetime.fromisoformat(
                        created.replace("Z", "+00:00")
                    )
            members_by_cluster: dict[str, list[datetime]] = {}
            for m in member_rows:
                ts = created_by_pk.get(m["issue_id"])
                if ts is not None:
                    members_by_cluster.setdefault(m["cluster_id"], []).append(ts)

            report = []
            for release in releases:
                r_date = datetime.fromisoformat(
                    release["release_date"].replace("Z", "+00:00")
                )
                b_start, b_end, before_days = clipped_before_window(
                    r_date, args.window_days, ds_start, ds_end
                )
                a_start, a_end, after_days = clipped_after_window(
                    r_date, args.window_days, ds_start, ds_end
                )
                sufficient = (
                    before_days >= args.min_coverage_days
                    and after_days >= args.min_coverage_days
                )
                comparison_status = (
                    "sufficient_history"
                    if sufficient
                    else "insufficient_history"
                )

                # Invariant checks
                assert b_end <= a_start, (
                    f"before_end ({b_end}) must be <= after_start ({a_start})"
                )
                assert b_start < b_end or before_days == 0, (
                    f"before_start ({b_start}) must be < before_end ({b_end})"
                )
                assert a_start < a_end or after_days == 0, (
                    f"after_start ({a_start}) must be < after_end ({a_end})"
                )

                before_total = sum(
                    1 for t in in_scope_dt if b_start <= t < b_end
                )
                after_total = sum(
                    1 for t in in_scope_dt if a_start <= t < a_end
                )
                entry = {
                    "release": release["name"],
                    "release_date": release["release_date"],
                    "source_url": release["source_url"],
                    "calc_version": CALC_VERSION,
                    "before_window": f"{b_start.isoformat()} .. {b_end.isoformat()} ({round(before_days, 1)}d)",
                    "after_window": f"{a_start.isoformat()} .. {a_end.isoformat()} ({round(after_days, 1)}d)",
                    "before_coverage_days": round(before_days, 2),
                    "after_coverage_days": round(after_days, 2),
                    "comparison_status": comparison_status,
                    "in_scope_before": before_total,
                    "in_scope_after": after_total,
                    "min_coverage_days": args.min_coverage_days,
                }
                if not sufficient:
                    report.append(entry)
                    continue

                cluster_rows = []
                for cluster in clusters:
                    times = members_by_cluster.get(cluster["id"], [])
                    before = sum(1 for t in times if b_start <= t < b_end)
                    after = sum(1 for t in times if a_start <= t < a_end)
                    if before == 0 and after == 0:
                        continue
                    cluster_rows.append(
                        {
                            "release_id": release["id"],
                            "cluster_id": cluster["id"],
                            "window_days": args.window_days,
                            "before_count": before,
                            "after_count": after,
                            "change_rate": change_rate(before, after),
                            "signal_type": signal_type(before, after),
                            "confidence": round(
                                min(before_days, after_days)
                                / args.window_days,
                                2,
                            ),
                        }
                    )
                cluster_rows.sort(
                    key=lambda r: -abs(r["after_count"] - r["before_count"])
                )
                for row in cluster_rows:
                    supabase.upsert(
                        "release_impacts",
                        [row],
                        on_conflict="release_id,cluster_id,window_days",
                    )
                entry["cluster_impacts_persisted"] = len(cluster_rows)
                entry["top_increases"] = [
                    {
                        "cluster": next(
                            c["cluster_name"]
                            for c in clusters
                            if c["id"] == row["cluster_id"]
                        ),
                        "before": row["before_count"],
                        "after": row["after_count"],
                        "signal": row["signal_type"],
                    }
                    for row in cluster_rows[:6]
                ]
                report.append(entry)

            supabase.insert(
                "analysis_runs",
                {
                    "run_type": "release_impact",
                    "analysis_version": args.analysis_version,
                    "start_date": ds_start.isoformat(),
                    "snapshot_at": ds_end.isoformat(),
                    "item_count": sum(
                        1 for r in report if r["comparison_status"] == "sufficient_history"
                    ),
                    "params": {
                        "calc_version": CALC_VERSION,
                        "window_days": args.window_days,
                        "min_coverage_days": args.min_coverage_days,
                        "releases_evaluated": len(releases),
                        "sufficient_history": sum(
                            1 for r in report if r["comparison_status"] == "sufficient_history"
                        ),
                        "insufficient_history": sum(
                            1 for r in report if r["comparison_status"] != "sufficient_history"
                        ),
                        "runtime_seconds": round(
                            time.monotonic() - started, 1
                        ),
                    },
                },
            )
            print(json.dumps(report, indent=2, ensure_ascii=False))
            return 0
    except (SupabaseConfigError, RuntimeError, ValueError) as exc:
        print(f"Release impact failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
