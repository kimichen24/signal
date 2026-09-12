"""Deterministic current-vs-previous trends with a history-sufficiency guard
(Prompt 03 D/E).

Default periods (complete UTC days):
    current  = [today_start - window_days, today_start)
    previous = [today_start - 2*window_days, today_start - window_days)

The sufficiency guard is the critical rule: when the dataset does not cover
both periods or a period lacks meaningful volume, the state is
`insufficient_history` and NOTHING is written — a missing previous period is
never converted into "+100%" or "new emerging signal" claims.

All math is deterministic and unit-tested; the LLM never computes growth.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

SEVERITY_SCORES = {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}
INSUFFICIENT_HISTORY = "insufficient_history"


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    try:
        return datetime.strptime(text, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        pass
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def period_bounds(
    snapshot_at: datetime | None = None, window_days: int = 7
) -> tuple[datetime, datetime, datetime]:
    """Returns (current_start, current_end, previous_start) using complete
    UTC days before the snapshot date."""
    snapshot = snapshot_at or datetime.now(timezone.utc)
    today_start = snapshot.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    current_end = today_start
    current_start = current_end - timedelta(days=window_days)
    previous_start = current_start - timedelta(days=window_days)
    return current_start, current_end, previous_start


def in_period(created_at: str, start: datetime, end: datetime) -> bool:
    ts = parse_ts(created_at)
    if ts is None:
        return False
    return start <= ts < end


def history_sufficiency(
    *,
    min_created_at: str | None,
    current_count: int,
    previous_count: int,
    current_start: datetime,
    previous_start: datetime,
    min_period_volume: int,
    window_start: datetime | None = None,
    window_snapshot: datetime | None = None,
) -> tuple[bool, str]:
    """The guard: both periods must be covered by the dataset range AND
    contain at least min_period_volume observations.

    Coverage is checked against the recorded dataset window
    [window_start, window_snapshot) when provided (stronger evidence than
    the earliest observation, which legitimately arrives minutes AFTER a
    period boundary on an exactly-aligned dataset)."""
    if window_start is not None and window_start > previous_start:
        return False, (
            "dataset window does not cover the previous period "
            f"(window starts {window_start.isoformat()})"
        )
    if window_snapshot is not None and window_snapshot < current_start:
        return False, (
            "dataset window does not reach the current period "
            f"(snapshot {window_snapshot.isoformat()})"
        )
    if window_start is None:
        earliest = parse_ts(min_created_at)
        if earliest is None or earliest >= previous_start:
            return False, (
                "dataset does not cover the previous period "
                f"(earliest observation {min_created_at})"
            )
    if previous_count < min_period_volume:
        return False, (
            f"previous period has only {previous_count} observations "
            f"(minimum {min_period_volume})"
        )
    if current_count < min_period_volume:
        return False, (
            f"current period has only {current_count} observations "
            f"(minimum {min_period_volume})"
        )
    return True, "sufficient"


def growth_rate(current_count: int, previous_count: int) -> float | None:
    """(current - previous) / previous. Zero baselines are handled
    explicitly: no baseline -> None (never +inf, never '+100%')."""
    if previous_count <= 0:
        return None
    return (current_count - previous_count) / previous_count


def is_emerging(
    current_count: int,
    growth: float | None,
    min_volume: int,
    min_growth: float,
) -> bool:
    """A signal is Emerging only with enough current volume AND computed
    growth above the threshold. No growth (zero baseline) -> never."""
    if growth is None or current_count < min_volume:
        return False
    return growth >= min_growth


def emerging_score(
    current_count: int, growth: float | None, avg_severity_score: float
) -> float | None:
    """Transparent 0-1 blend: 40% capped growth, 30% capped volume,
    30% average severity. None without a computable growth value."""
    if growth is None:
        return None
    growth_part = min(max(growth, 0.0), 3.0) / 3.0
    volume_part = min(current_count / 20.0, 1.0)
    return round(0.4 * growth_part + 0.3 * volume_part + 0.3 * avg_severity_score, 3)


def trend_state(previous_count: int) -> str:
    """Deterministic baseline classification (frozen, Prompt 04).

    normal_growth: previous >= 3
    low_base_acceleration: previous in (1, 2)
    new_signal: previous = 0 (growth is never computed for this state)
    """
    if previous_count <= 0:
        return "new_signal"
    if previous_count <= 2:
        return "low_base_acceleration"
    return "normal_growth"


def trend_metrics(
    current_count: int,
    previous_count: int,
    in_scope_current_total: int,
    in_scope_previous_total: int,
    min_volume: int,
    min_growth: float,
) -> dict[str, Any]:
    """Full WoW metrics for one cluster. Shares use in-scope period totals
    as denominators (never raw totals containing out_of_scope)."""
    growth = growth_rate(current_count, previous_count)
    state = trend_state(previous_count)
    previous_share = (
        previous_count / in_scope_previous_total
        if in_scope_previous_total > 0
        else None
    )
    current_share = (
        current_count / in_scope_current_total
        if in_scope_current_total > 0
        else None
    )
    share_delta_pp = (
        round((current_share - previous_share) * 100, 2)
        if previous_share is not None and current_share is not None
        else None
    )
    # State-based Emerging eligibility (frozen, Prompt 04):
    #   normal_growth: current >= 5 AND growth >= threshold AND share lift > 0
    #   low_base_acceleration: current >= 5 AND share lift > 0
    #   new_signal: current >= 5 (no growth math)
    if state == "normal_growth":
        emerging = (
            current_count >= min_volume
            and growth is not None
            and growth >= min_growth
            and (share_delta_pp or 0) > 0
        )
    elif state == "low_base_acceleration":
        emerging = (
            current_count >= min_volume and (share_delta_pp or 0) > 0
        )
    else:  # new_signal
        emerging = current_count >= min_volume
    return {
        "absolute_delta": current_count - previous_count,
        "growth_rate": growth,
        "trend_state": state,
        "previous_share": previous_share,
        "current_share": current_share,
        "share_delta_pp": share_delta_pp,
        "is_emerging": emerging,
        # Emerging score is computed downstream by the state-specific
        # formula (pipeline.opportunities.signal_score) with P95 caps —
        # new_signal rows have no growth math here by design.
        "emerging_score": emerging_score(current_count, growth, 0.5)
        if emerging and state == "normal_growth"
        else None,
    }


def avg_severity_score(severities: list[str | None]) -> float:
    values = [SEVERITY_SCORES.get(s or "", 0.5) for s in severities]
    return round(sum(values) / len(values), 3) if values else 0.0


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import os
    import sys
    import time
    from collections import defaultdict

    from pipeline.cluster_issues import parse_embedding  # noqa: F401 (re-export parity)
    from pipeline.supabase_client import (
        SupabaseConfigError,
        SupabaseRest,
        load_env,
    )

    parser = argparse.ArgumentParser(
        prog="python -m pipeline.compute_trends",
        description="Deterministic trends + Emerging Signals (Prompt 03 D/E).",
    )
    parser.add_argument(
        "--analysis-version",
        default=os.environ.get("SIGNAL_ANALYSIS_VERSION", "v0.3.4"),
    )
    parser.add_argument(
        "--window-days", type=int, default=7, help="comparison window in days"
    )
    parser.add_argument(
        "--snapshot-at",
        default=os.environ.get("SIGNAL_SNAPSHOT_AT"),
        help="window anchor (default: now)",
    )
    parser.add_argument(
        "--start-date",
        default=os.environ.get("SIGNAL_START_DATE"),
        help="dataset window lower bound (YYYY-MM-DD or ISO, inclusive)",
    )
    args = parser.parse_args(argv)

    min_period_volume = int(
        os.environ.get("SIGNAL_TREND_MIN_PERIOD_VOLUME", "10")
    )
    min_volume = int(os.environ.get("SIGNAL_EMERGING_MIN_VOLUME", "5"))
    min_growth = float(os.environ.get("SIGNAL_EMERGING_MIN_GROWTH", "0.5"))
    started = time.monotonic()

    try:
        with SupabaseRest.from_env() as supabase:
            clusters = supabase.select_paged(
                "clusters",
                columns=(
                    "id,cluster_key,cluster_name,category,issue_count,"
                    "avg_severity_score,clustering_params"
                ),
                filters={"analysis_version": f"eq.{args.analysis_version}"},
            )
            members = supabase.select_paged(
                "cluster_members",
                columns="cluster_id,issues(github_created_at)",
            )
            members_by_cluster: dict[str, list[str]] = defaultdict(list)
            for m in members:
                created = (m.get("issues") or {}).get("github_created_at")
                if created:
                    members_by_cluster[m["cluster_id"]].append(created)

            current_start, current_end, previous_start = period_bounds(
                parse_ts(args.snapshot_at) or datetime.now(timezone.utc),
                args.window_days,
            )
            window_start = parse_ts(args.start_date)
            window_snapshot = parse_ts(args.snapshot_at)
            current_counts, previous_counts = {}, {}
            for cluster in clusters:
                dates = members_by_cluster.get(cluster["id"], [])
                current_counts[cluster["id"]] = sum(
                    1
                    for d in dates
                    if in_period(d, current_start, current_end)
                )
                previous_counts[cluster["id"]] = sum(
                    1
                    for d in dates
                    if in_period(d, previous_start, current_start)
                )

            total_current = sum(current_counts.values())
            total_previous = sum(previous_counts.values())
            all_dates = [
                d
                for dates in members_by_cluster.values()
                for d in dates
            ]
            earliest = min(all_dates) if all_dates else None
            in_scope_rows = supabase.select_paged(
                "issue_analysis",
                columns="issues(github_created_at)",
                filters={
                    "analysis_version": f"eq.{args.analysis_version}",
                    "product_scope": "neq.out_of_scope",
                },
            )
            in_scope_current_total = sum(
                1
                for r in in_scope_rows
                if in_period(
                    (r.get("issues") or {}).get("github_created_at") or "",
                    current_start,
                    current_end,
                )
            )
            in_scope_previous_total = sum(
                1
                for r in in_scope_rows
                if in_period(
                    (r.get("issues") or {}).get("github_created_at") or "",
                    previous_start,
                    current_start,
                )
            )

            sufficient, reason = history_sufficiency(
                min_created_at=earliest,
                current_count=total_current,
                previous_count=total_previous,
                current_start=current_start,
                previous_start=previous_start,
                min_period_volume=min_period_volume,
                window_start=window_start,
                window_snapshot=window_snapshot,
            )

            report: dict[str, Any] = {
                "analysis_version": args.analysis_version,
                "window_days": args.window_days,
                "periods": {
                    "current": f"{current_start.isoformat()} .. {current_end.isoformat()}",
                    "previous": f"{previous_start.isoformat()} .. {current_start.isoformat()}",
                },
                "total_current": total_current,
                "total_previous": total_previous,
                "earliest_cluster_member": earliest,
                "state": (
                    "ok" if sufficient else INSUFFICIENT_HISTORY
                ),
                "reason": reason,
                "thresholds": {
                    "min_period_volume": min_period_volume,
                    "emerging_min_volume": min_volume,
                    "emerging_min_growth": min_growth,
                },
            }

            if not sufficient:
                # NOTHING is written: no growth, no "+100%", no "new signal".
                report["written"] = 0
                supabase.insert(
                    "analysis_runs",
                    {
                        "run_type": "trends",
                        "analysis_version": args.analysis_version,
                        "start_date": previous_start.isoformat(),
                        "snapshot_at": current_end.isoformat(),
                        "item_count": 0,
                        "params": {
                            **report["thresholds"],
                            "state": report["state"],
                            "reason": reason,
                            "total_current": total_current,
                            "total_previous": total_previous,
                            "runtime_seconds": round(
                                time.monotonic() - started, 1
                            ),
                        },
                    },
                )
                print(json.dumps(report, indent=2))
                print(
                    "\ninsufficient_history — no trend columns written. "
                    "The UI will show the honest 'more historical feedback "
                    "required' state."
                )
                return 0

            updated = 0
            for cluster in clusters:
                cid = cluster["id"]
                current = current_counts[cid]
                previous = previous_counts[cid]
                metrics = trend_metrics(
                    current,
                    previous,
                    in_scope_current_total,
                    in_scope_previous_total,
                    min_volume,
                    min_growth,
                )
                fields = {
                    "current_period_count": current,
                    "previous_period_count": previous,
                    "growth_rate": metrics["growth_rate"],
                    "is_emerging": metrics["is_emerging"],
                    "emerging_score": metrics["emerging_score"],
                    "clustering_params": {
                        **(cluster.get("clustering_params") or {}),
                        "trend": {
                            "absolute_delta": metrics["absolute_delta"],
                            "trend_state": metrics["trend_state"],
                            "previous_share": metrics["previous_share"],
                            "current_share": metrics["current_share"],
                            "share_delta_pp": metrics["share_delta_pp"],
                            "in_scope_current_total": in_scope_current_total,
                            "in_scope_previous_total": in_scope_previous_total,
                        },
                    },
                }
                supabase.update(
                    "clusters", {"id": f"eq.{cid}"}, fields
                )
                updated += 1
            report["written"] = updated
            supabase.insert(
                "analysis_runs",
                {
                    "run_type": "trends",
                    "analysis_version": args.analysis_version,
                    "start_date": previous_start.isoformat(),
                    "snapshot_at": current_end.isoformat(),
                    "item_count": updated,
                    "params": {
                        **report["thresholds"],
                        "state": report["state"],
                        "runtime_seconds": round(
                            time.monotonic() - started, 1
                        ),
                    },
                },
            )
            print(json.dumps(report, indent=2))
            return 0
    except (SupabaseConfigError, RuntimeError, ValueError) as exc:
        print(f"Trend computation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
