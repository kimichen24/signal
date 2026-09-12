"""Opportunities + Action Briefs (Prompt 04).

Deterministic core (this module's pure functions, unit-tested):
  1. Emerging signal scores per frozen trend state (P95-clipped component
     normalization over emerging-eligible clusters; params recorded).
  2. Opportunity evidence gate: size >= 5 AND current >= 5, with the narrow
     critical exception (3 <= size < 5 AND >= 2 AI-critical members, status
     capped at Validate).
  3. Investigation Priority = 30% frequency + 25% AI-estimated severity
     + 25% growth/signal strength + 20% engagement — engagement uses only
     real GitHub fields (comments + reactions) and is renormalized out
     transparently when too sparse. Never labeled P0/P1.
  4. Deterministic status mapping BEFORE any LLM prose:
     Investigate Now / Validate / Monitor / Low Priority.

MiMo only writes Action Brief prose from stored evidence after scores and
statuses are fixed (needs_refinement clusters get a broad-family variant
that preserves uncertainty).
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
import os
import sys
import time
from typing import Any

SEVERITY_SCORES = {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}

# Frozen Investigation Priority framework (docs/PRD.md §8).
PRIORITY_WEIGHTS = {
    "frequency": 0.30,
    "severity": 0.25,
    "signal": 0.25,
    "engagement": 0.20,
}

MIN_OPPORTUNITY_SIZE = 5
MIN_OPPORTUNITY_CURRENT = 5
CRITICAL_EXCEPTION_SIZE = 3
CRITICAL_EXCEPTION_MIN_CRITICAL = 2

BRIEF_SYSTEM_PROMPT = """You write concise Action Briefs for a product-ops intelligence system, based ONLY on the stored evidence provided.

Return exactly one JSON object with keys:
- "what_changed": 1-2 sentences on the trend change (use the provided counts/state)
- "affected_workflow": the user workflow impacted (short phrase)
- "affected_surface_platform": surface/platform summary from the evidence
- "evidence_summary": 2-3 sentences citing the member issues (by issue number)
- "product_hypothesis": one sentence, explicitly a possible hypothesis (NOT a proven cause)
- "recommended_investigation": 1-2 concrete investigation steps
- "suggested_validation": 1-2 validation actions
- "metrics_to_monitor": array of 3-5 short metric name strings (public/observable only)

Hard rules:
- Never claim proven root cause, release causality, internal user/revenue impact, or certainty beyond the evidence.
- No P0/P1 wording; priority is already computed deterministically.
- If needs_refinement is true: this is a BROAD problem family — recommend investigation/refinement of the family instead of a specific fix, and explicitly state the uncertainty.
- English only."""


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[min(int(0.95 * len(ordered)), len(ordered) - 1)])


def clip_norm(value: float | None, cap: float) -> float:
    """P95-clipped normalization; negative values contribute 0."""
    if value is None or cap <= 0:
        return 0.0
    return round(max(0.0, min(float(value), cap)) / cap, 4)


def emerging_eligible(state: str, row: dict[str, Any]) -> bool:
    """State-specific Emerging Signal eligibility (frozen)."""
    current = row["current_period_count"]
    if current < 5:
        return False
    if state == "normal_growth":
        growth = row.get("growth_rate")
        return growth is not None and growth >= 0.5 and (
            row.get("share_delta_pp") or 0
        ) > 0
    if state == "low_base_acceleration":
        return (row.get("share_delta_pp") or 0) > 0
    if state == "new_signal":
        return True
    return False


def signal_components(state: str, row: dict[str, Any]) -> dict[str, float]:
    """Raw (unnormalized) component values for the state-specific score."""
    if state == "normal_growth":
        return {
            "share_lift_pp": max(row.get("share_delta_pp") or 0.0, 0.0),
            "abs_delta": max(float(row.get("absolute_delta") or 0.0), 0.0),
            "growth_capped": min(max(row.get("growth_rate") or 0.0, 0.0), 2.0),
            "current_share": row.get("current_share") or 0.0,
            "current_count": float(row["current_period_count"]),
            "severity": float(row.get("avg_severity_score") or 0.0),
        }
    if state == "low_base_acceleration":
        return {
            "share_lift_pp": max(row.get("share_delta_pp") or 0.0, 0.0),
            "abs_delta": max(float(row.get("absolute_delta") or 0.0), 0.0),
            "current_share": row.get("current_share") or 0.0,
            "current_count": float(row["current_period_count"]),
            "severity": float(row.get("avg_severity_score") or 0.0),
        }
    return {
        "share_lift_pp": 0.0,
        "abs_delta": 0.0,
        "growth_capped": 0.0,
        "current_share": row.get("current_share") or 0.0,
        "current_count": float(row["current_period_count"]),
        "severity": float(row.get("avg_severity_score") or 0.0),
    }


def signal_score(
    state: str, comps: dict[str, float], caps: dict[str, dict[str, float]]
) -> float:
    """State-specific Emerging score (frozen formulas). `caps` is the nested
    state→component-cap mapping produced by state_caps()."""
    cap = caps.get(state, {})
    if state == "normal_growth":
        return round(
            0.35 * clip_norm(comps["share_lift_pp"], cap.get("share_lift_pp", 0.0))
            + 0.30 * clip_norm(comps["abs_delta"], cap.get("abs_delta", 0.0))
            + 0.20 * clip_norm(comps["growth_capped"], cap.get("growth_capped", 0.0))
            + 0.15 * comps["severity"],
            4,
        )
    if state == "low_base_acceleration":
        return round(
            0.40 * clip_norm(comps["share_lift_pp"], cap.get("share_lift_pp", 0.0))
            + 0.35 * clip_norm(comps["abs_delta"], cap.get("abs_delta", 0.0))
            + 0.25 * comps["severity"],
            4,
        )
    if state == "new_signal":
        return round(
            0.45 * clip_norm(comps["current_share"], cap.get("current_share", 0.0))
            + 0.35 * clip_norm(comps["current_count"], cap.get("current_count", 0.0))
            + 0.20 * comps["severity"],
            4,
        )
    return 0.0


def state_caps(
    scored_components: list[tuple[str, dict[str, float]]],
) -> dict[str, dict[str, float]]:
    """P95 caps per state/component over Emerging-ELIGIBLE clusters only."""
    caps: dict[str, dict[str, float]] = {}
    eligible_by_state: dict[str, list[dict[str, float]]] = {}
    for state, comps in scored_components:
        eligible_by_state.setdefault(state, []).append(comps)
    for state, comps_list in eligible_by_state.items():
        keys = comps_list[0].keys() if comps_list else []
        caps[state] = {key: p95([c[key] for c in comps_list]) for key in keys}
    return caps


def opportunity_eligibility(
    cluster_size: int, current_count: int, critical_members: int
) -> tuple[bool, str]:
    """Evidence gate. Returns (eligible, rule)."""
    if cluster_size >= MIN_OPPORTUNITY_SIZE and (
        current_count >= MIN_OPPORTUNITY_CURRENT
    ):
        return True, "standard: size>=5 and current>=5"
    if (
        CRITICAL_EXCEPTION_SIZE
        <= cluster_size
        < MIN_OPPORTUNITY_SIZE
        and critical_members >= CRITICAL_EXCEPTION_MIN_CRITICAL
    ):
        return True, "critical_exception: 3<=size<5 with >=2 AI-critical members (status capped at Validate)"
    return False, (
        f"rejected: size={cluster_size}, current={current_count}, "
        f"critical_members={critical_members}"
    )


def priority_breakdown(
    frequency_count: int,
    severity_score: float,
    signal_score: float,
    engagement_total: int,
    freq_cap: float,
    engagement_cap: float,
    engagement_available: bool,
) -> dict[str, Any]:
    """Transparent Investigation Priority. Engagement is renormalized out
    (documented) when unavailable/sparse — never faked as neutral."""
    freq_n = clip_norm(float(frequency_count), freq_cap)
    sev_n = round(max(0.0, min(severity_score, 1.0)), 4)
    sig_n = round(max(0.0, min(signal_score, 1.0)), 4)
    eng_n = clip_norm(float(engagement_total), engagement_cap)

    components = {"frequency": freq_n, "severity": sev_n, "signal": sig_n}
    weights = {"frequency": 0.30, "severity": 0.25, "signal": 0.25}
    if engagement_available:
        components["engagement"] = eng_n
        weights["engagement"] = 0.20
    else:
        wsum = sum(weights.values())
        weights = {k: round(v / wsum, 4) for k, v in weights.items()}

    priority = round(sum(weights[k] * components[k] for k in weights), 4)
    return {
        "priority": priority,
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "engagement_available": engagement_available,
    }


def status_for(
    priority: float, cluster_size: int, critical_members: int, critical_exception: bool
) -> str:
    """Deterministic status mapping (applied before any LLM prose)."""
    if critical_exception:
        if priority >= 0.45:
            return "validate"
        if priority >= 0.30:
            return "monitor"
        return "low_priority"
    if priority >= 0.60 and cluster_size >= 5:
        return "investigate_now"
    if priority >= 0.45:
        return "validate"
    if priority >= 0.30:
        return "monitor"
    return "low_priority"


def validate_brief(obj: dict[str, Any]) -> list[str]:
    keys = (
        "what_changed",
        "affected_workflow",
        "affected_surface_platform",
        "evidence_summary",
        "product_hypothesis",
        "recommended_investigation",
        "suggested_validation",
        "metrics_to_monitor",
    )
    problems = []
    for key in keys[:-1]:
        value = obj.get(key)
        if not isinstance(value, str) or len(value.strip()) < 8:
            problems.append(f"{key} must be a non-trivial string")
    metrics = obj.get("metrics_to_monitor")
    if not isinstance(metrics, list) or not (
        1 <= len([m for m in metrics if isinstance(m, str) and m.strip()]) <= 6
    ):
        problems.append("metrics_to_monitor must be 1-6 short strings")
    return problems


def brief_payload(
    cluster: dict[str, Any], members: list[dict[str, Any]], engagement: dict[str, Any]
) -> str:
    sample = sorted(members, key=lambda m: int(m["github_issue_number"]))[:8]
    lines = [
        f"- #{m['github_issue_number']} {m['title']} — severity: {m['severity']}"
        for m in sample
    ]
    more = (
        f"\n(+{cluster['issue_count'] - len(sample)} more members)"
        if cluster["issue_count"] > len(sample)
        else ""
    )
    trend = cluster.get("trend") or {}
    needs_ref = bool((cluster["clustering_params"] or {}).get("needs_refinement"))
    return (
        f"cluster_name: {cluster['cluster_name']}\n"
        f"category: {cluster['category']}\n"
        f"issue_count: {cluster['issue_count']}\n"
        f"period_counts: previous={cluster['previous_period_count']}, "
        f"current={cluster['current_period_count']}\n"
        f"trend_state: {trend.get('trend_state')}\n"
        f"raw_growth_rate: {cluster.get('growth_rate')}\n"
        f"share_delta_pp: {trend.get('share_delta_pp')}\n"
        f"needs_refinement: {str(needs_ref).lower()}\n"
        f"primary_surface: {cluster['primary_surface']}\n"
        f"primary_platform: {cluster['primary_platform']}\n"
        f"member_engagement: {json.dumps(engagement)}\n"
        f"members:\n" + "\n".join(lines) + more
        + (
            "\nThis cluster is a BROAD problem family flagged "
            "needs_refinement: recommend investigation and refinement of the "
            "family, preserve uncertainty, do not propose a specific "
            "root-cause fix."
            if needs_ref
            else ""
        )
    )


def main(argv: list[str] | None = None) -> int:
    from pipeline.ai.base import AIConfigError, build_providers
    from pipeline.supabase_client import (
        SupabaseConfigError,
        SupabaseRest,
        load_env,
    )

    parser = argparse.ArgumentParser(
        prog="python -m pipeline.opportunities",
        description="Investigation Priority + Action Briefs (Prompt 04).",
    )
    parser.add_argument(
        "--analysis-version",
        default=os.environ.get("SIGNAL_ANALYSIS_VERSION", "v0.3.4"),
    )
    parser.add_argument(
        "--start-date",
        default="2026-08-23",
        help="dataset window lower bound (recorded with the run)",
    )
    parser.add_argument(
        "--snapshot-at",
        default="2026-09-06T00:00:00Z",
        help="dataset window upper bound (recorded with the run)",
    )
    parser.add_argument("--skip-briefs", action="store_true")
    args = parser.parse_args(argv)
    started = time.monotonic()
    min_volume = int(os.environ.get("SIGNAL_EMERGING_MIN_VOLUME", "5"))
    min_growth = float(os.environ.get("SIGNAL_EMERGING_MIN_GROWTH", "0.5"))

    try:
        with SupabaseRest.from_env() as supabase:
            clusters = supabase.select_paged(
                "clusters",
                columns=(
                    "id,cluster_key,cluster_name,category,issue_count,"
                    "current_period_count,previous_period_count,growth_rate,"
                    "is_emerging,emerging_score,avg_severity_score,"
                    "primary_surface,primary_platform,clustering_params"
                ),
                filters={"analysis_version": f"eq.{args.analysis_version}"},
            )
            members = supabase.select_paged(
                "cluster_members", columns="cluster_id,issue_id"
            )
            issues = supabase.select_paged(
                "issues",
                columns="id,github_issue_number,title,comments_count,reactions_count",
            )
            engagement_by_pk = {}
            info_by_pk = {}
            for r in issues:
                engagement_by_pk[r["id"]] = (r.get("comments_count") or 0) + (
                    r.get("reactions_count") or 0
                )
                info_by_pk[r["id"]] = {
                    "github_issue_number": r["github_issue_number"],
                    "title": r.get("title") or "",
                }
            severity_rows = supabase.select_paged(
                "issue_analysis",
                columns="issue_id,severity",
                filters={"analysis_version": f"eq.{args.analysis_version}"},
            )
            severity_by_issue = {
                r["issue_id"]: r["severity"] for r in severity_rows
            }
            member_ids: dict[str, list[str]] = {}
            for m in members:
                member_ids.setdefault(m["cluster_id"], []).append(m["issue_id"])

            enriched: list[dict[str, Any]] = []
            for cluster in clusters:
                ids = member_ids.get(cluster["id"], [])
                trend = (cluster.get("clustering_params") or {}).get("trend") or {}
                enriched.append(
                    {
                        **cluster,
                        # Flatten stored trend metrics (share_delta_pp etc.)
                        # so eligibility/scoring read them at top level.
                        **trend,
                        "trend": trend,
                        "engagement_total": sum(
                            engagement_by_pk.get(i, 0) for i in ids
                        ),
                        "critical_members": sum(
                            1
                            for i in ids
                            if severity_by_issue.get(i) == "critical"
                        ),
                    }
                )

            # --- Emerging eligibility + state-specific scores ---------------
            scored: list[tuple[str, dict[str, float], dict[str, Any]]] = []
            for cluster in enriched:
                state = (cluster.get("trend") or {}).get(
                    "trend_state"
                ) or "normal_growth"
                if emerging_eligible(state, cluster):
                    comps = signal_components(state, cluster)
                    scored.append((state, comps, cluster))
            caps = state_caps([(s, c) for s, c, _ in scored])
            for state, comps, cluster in scored:
                cluster["signal_score"] = signal_score(state, comps, caps)

            # --- Opportunity evidence gate ---------------------------------
            eligible: list[dict[str, Any]] = []
            rejected: list[str] = []
            for cluster in enriched:
                ok, rule = opportunity_eligibility(
                    cluster["issue_count"],
                    cluster["current_period_count"],
                    cluster["critical_members"],
                )
                if ok:
                    cluster["exception"] = "critical_exception" in rule
                    eligible.append(cluster)
                else:
                    rejected.append(f"{cluster['cluster_name']}: {rule}")

            freq_cap = p95([float(c["issue_count"]) for c in eligible])
            eng_cap = p95([float(c["engagement_total"]) for c in eligible])
            engagement_available = eng_cap > 0

            for cluster in eligible:
                breakdown = priority_breakdown(
                    frequency_count=cluster["issue_count"],
                    severity_score=float(cluster.get("avg_severity_score") or 0.0),
                    signal_score=float(cluster.get("signal_score") or 0.0),
                    engagement_total=cluster["engagement_total"],
                    freq_cap=freq_cap,
                    engagement_cap=eng_cap,
                    engagement_available=engagement_available,
                )
                cluster["priority"] = breakdown
                cluster["action_type"] = status_for(
                    breakdown["priority"],
                    cluster["issue_count"],
                    cluster["critical_members"],
                    cluster["exception"],
                )
            eligible.sort(key=lambda c: -c["priority"]["priority"])

            # --- persist (full recompute each run) --------------------------
            supabase.delete("opportunities", {"id": "not.is.null"})
            for rank, cluster in enumerate(eligible, start=1):
                inserted = supabase.upsert(
                    "opportunities",
                    [{
                        "cluster_id": cluster["id"],
                        "frequency_score": cluster["priority"]["components"]["frequency"],
                        "severity_score": cluster["priority"]["components"]["severity"],
                        "growth_score": cluster["priority"]["components"]["signal"],
                        "engagement_score": cluster["priority"]["components"].get("engagement"),
                        "priority_score": cluster["priority"]["priority"],
                        "action_type": cluster["action_type"],
                        "priority_reason": json.dumps(
                            {
                                "rank": rank,
                                "components": cluster["priority"]["components"],
                                "weights": cluster["priority"]["weights"],
                                "engagement_available": cluster["priority"]["engagement_available"],
                                "signal_state": (cluster.get("trend") or {}).get("trend_state"),
                                "signal_score": cluster.get("signal_score"),
                                "signal_caps": caps.get((cluster.get("trend") or {}).get("trend_state")),
                                "exception": cluster["exception"],
                            },
                            ensure_ascii=False,
                        ),
                    }],
                    on_conflict="cluster_id",
                )

            # --- Action Briefs (MiMo, after scores/statuses are fixed) ------
            brief_failures: list[str] = []
            briefed = 0
            if not args.skip_briefs and eligible:
                provider = build_providers(os.environ)
                for cluster in eligible:
                    members_of = [
                        {
                            "github_issue_number": info_by_pk.get(
                                issue_id, {}
                            ).get("github_issue_number", 0),
                            "title": info_by_pk.get(issue_id, {}).get("title", ""),
                            "severity": severity_by_issue.get(issue_id, "medium"),
                        }
                        for issue_id in member_ids.get(cluster["id"], [])
                    ]
                    payload = brief_payload(
                        cluster, members_of,
                        {"total": cluster["engagement_total"],
                         "available": cluster["priority"]["engagement_available"]},
                    )
                    brief = None
                    problems_hint = ""
                    for _attempt in (1, 2):
                        try:
                            obj, _usage = provider.complete_json(
                                BRIEF_SYSTEM_PROMPT, payload
                            )
                            problems = validate_brief(obj)
                            if not problems:
                                brief = obj
                                break
                            problems_hint = "; ".join(problems)
                        except Exception as exc:
                            problems_hint = f"{type(exc).__name__}: {exc}"[:200]
                    if brief is None:
                        brief_failures.append(
                            f"{cluster['cluster_name']}: {problems_hint}"
                        )
                        continue
                    supabase.update(
                        "opportunities",
                        {"cluster_id": f"eq.{cluster['id']}"},
                        {
                            "product_hypothesis": brief["product_hypothesis"],
                            "suggested_metrics": brief["metrics_to_monitor"],
                            "action_brief": brief,
                        },
                    )
                    briefed += 1

            # --- audit ------------------------------------------------------
            eligible.sort(key=lambda c: -c["priority"]["priority"])
            state_counts: dict[str, int] = {}
            for state, _comps, _cluster in scored:
                state_counts[state] = state_counts.get(state, 0) + 1
            audit = {
                "analysis_version": args.analysis_version,
                "emerging_by_state": state_counts,
                "signal_caps": caps,
                "opportunity_eligible": len(eligible),
                "rejected_by_gate": len(rejected),
                "status_distribution": dict(
                    Counter(c["action_type"] for c in eligible)
                ),
                "priority_range": {
                    "min": min((c["priority"]["priority"] for c in eligible), default=None),
                    "max": max((c["priority"]["priority"] for c in eligible), default=None),
                },
                "engagement_available": engagement_available,
                "briefs_generated": briefed,
                "brief_failures": brief_failures or None,
                "rejected_sample": rejected[:10],
                "runtime_seconds": round(time.monotonic() - started, 1),
            }
            with open("logs/opportunities_audit.json", "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        **audit,
                        "eligible_rows": [
                            {
                                "name": c["cluster_name"],
                                "category": c["category"],
                                "size": c["issue_count"],
                                "current": c["current_period_count"],
                                "priority": c["priority"]["priority"],
                                "components": c["priority"]["components"],
                                "weights": c["priority"]["weights"],
                                "action": c["action_type"],
                                "state": (c.get("trend") or {}).get("trend_state"),
                                "signal_score": c.get("signal_score"),
                                "needs_refinement": bool(
                                    (c["clustering_params"] or {}).get("needs_refinement")
                                ),
                                "engagement": c["engagement_total"],
                            }
                            for c in eligible
                        ],
                    },
                    fh,
                    indent=2,
                    ensure_ascii=False,
                )
            print(json.dumps(audit, indent=2, ensure_ascii=False))
            return 0
    except (SupabaseConfigError, AIConfigError, RuntimeError, ValueError) as exc:
        print(f"Opportunities failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
