"""Generate frozen static data snapshot for GitHub Pages build.

Reads from the live Supabase database (frozen dataset) and writes
JSON files to generated/static-data/ for each page.

Run: .venv/Scripts/python.exe scripts/snapshot_static.py

Validates all authoritative metrics before writing.
Fails if any integrity check fails.
"""

import json
import os
import sys
import time
from pathlib import Path

# Increase recursion limit for large paginated fetches
sys.setrecursionlimit(5000)

# Ensure project root is on sys.path for pipeline imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OUT_DIR = Path(__file__).resolve().parent.parent / "generated" / "static-data"


def select_with_retry(sb, table, *, columns="*", filters=None, order=None, page_size=500, max_rows=20000):
    """select_paged with retry on transient errors (504, 429, 503)."""
    for attempt in range(3):
        try:
            return sb.select_paged(
                table, columns=columns, filters=filters, order=order,
                page_size=page_size, max_rows=max_rows,
            )
        except RuntimeError as e:
            if "504" in str(e) or "429" in str(e) or "503" in str(e):
                if attempt < 2:
                    time.sleep(5 * (attempt + 1))
                    continue
            raise


def main() -> int:
    # Load env
    env_path = Path(__file__).resolve().parent.parent / ".env.local"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

    from pipeline.supabase_client import SupabaseRest

    with SupabaseRest.from_env() as sb:
        VERSION = "v0.3.4"
        report = {}

        # ── Overview data ──────────────────────────────────────────
        issues = select_with_retry(sb, "issues", columns="id")
        total_issues = len(issues)

        analyses = select_with_retry(sb, 
            "issue_analysis",
            columns="issue_id,product_scope",
            filters={"analysis_version": f"eq.{VERSION}"},
        )
        analyzed = len(analyses)
        in_scope = [a for a in analyses if a["product_scope"] != "out_of_scope"]
        in_scope_count = len(in_scope)

        high_sev = select_with_retry(sb, 
            "issue_analysis",
            columns="issue_id",
            filters={
                "analysis_version": f"eq.{VERSION}",
                "severity": "in.(high,critical)",
            },
        )

        clusters = select_with_retry(sb, 
            "clusters",
            columns="id,cluster_key,cluster_name,category,summary,problem_statement,"
            "issue_count,primary_surface,primary_platform,avg_severity_score,"
            "is_emerging,emerging_score,growth_rate,current_period_count,"
            "previous_period_count,clustering_params",
            filters={"analysis_version": f"eq.{VERSION}"},
        )
        total_clusters = len(clusters)
        emerging = [c for c in clusters if c.get("is_emerging")]
        needs_ref = [
            c
            for c in clusters
            if (c.get("clustering_params") or {}).get("needs_refinement")
        ]

        # Distributions (in-scope, paginated)
        dist_rows = select_with_retry(sb, 
            "issue_analysis",
            columns="surface,platform,category",
            filters={
                "analysis_version": f"eq.{VERSION}",
                "product_scope": "neq.out_of_scope",
            },
        )
        surface_map, platform_map, category_map = {}, {}, {}
        for r in dist_rows:
            surface_map[r["surface"]] = surface_map.get(r["surface"], 0) + 1
            platform_map[r["platform"]] = platform_map.get(r["platform"], 0) + 1
            category_map[r["category"]] = category_map.get(r["category"], 0) + 1

        def to_slices(counter, total):
            return sorted(
                [
                    {"label": k, "count": v, "pct": round(100 * v / total) if total else 0}
                    for k, v in counter.items()
                ],
                key=lambda x: -x["count"],
            )

        total_dist = len(dist_rows)

        report["overview"] = {
            "summary": {
                "configured": True,
                "error": None,
                "totalIssues": total_issues,
                "analyzedIssues": analyzed,
                "emergingClusters": len(emerging),
                "highSeverityIssues": len(high_sev),
                "latestIssueAt": None,
            },
            "distributions": {
                "surface": to_slices(surface_map, total_dist),
                "platform": to_slices(platform_map, total_dist),
                "category": to_slices(category_map, total_dist),
                "inScopeTotal": in_scope_count,
            },
            "clusterCount": total_clusters,
        }

        # ── Feedback data ──────────────────────────────────────────
        latest_issues = select_with_retry(sb, 
            "issues",
            columns="id,github_issue_number,title,github_url,state,parsed_platform,github_created_at",
            order="github_created_at.desc",
            page_size=20,
            max_rows=20,
        )
        issue_ids = [i["id"] for i in latest_issues]
        fb_analyses = select_with_retry(sb, 
            "issue_analysis",
            columns="issue_id,issue_type,surface,platform,category,subtopic,severity,"
            "confidence,needs_review,summary,user_scenario,user_impact,"
            "product_scope,scope_reason,analysis_version,analyzed_at",
            filters={
                "analysis_version": f"eq.{VERSION}",
                "issue_id": f"in.({','.join(issue_ids)})",
            },
        )
        analysis_map = {a["issue_id"]: a for a in fb_analyses}
        feedback_rows = []
        for issue in latest_issues:
            a = analysis_map.get(issue["id"])
            row = {
                "id": issue["id"],
                "issueNumber": issue["github_issue_number"],
                "title": issue["title"],
                "githubUrl": issue["github_url"],
                "state": issue.get("state"),
                "platform": issue.get("parsed_platform"),
                "createdAt": issue.get("github_created_at", ""),
                "analysis": None,
            }
            if a:
                row["analysis"] = {
                    "issueNumber": issue["github_issue_number"],
                    "title": issue["title"],
                    "githubUrl": issue["github_url"],
                    "issueType": a["issue_type"],
                    "surface": a["surface"],
                    "platform": a["platform"],
                    "category": a["category"],
                    "subtopic": a["subtopic"],
                    "severity": a["severity"],
                    "confidence": float(a["confidence"]),
                    "needsReview": bool(a["needs_review"]),
                    "summary": a["summary"],
                    "userScenario": a.get("user_scenario"),
                    "userImpact": a.get("user_impact"),
                    "productScope": a.get("product_scope", "codex_core"),
                    "scopeReason": a.get("scope_reason"),
                    "analysisVersion": a["analysis_version"],
                    "analyzedAt": a["analyzed_at"],
                }
            feedback_rows.append(row)

        report["feedback"] = {"configured": True, "error": None, "rows": feedback_rows}

        # ── Insights data ──────────────────────────────────────────
        # Cluster members for representative evidence
        cluster_ids = [c["id"] for c in clusters]
        member_rows = select_with_retry(sb, 
            "cluster_members",
            columns="cluster_id,issue_id,is_representative",
            filters={"is_representative": "eq.true"},
        )
        rep_issue_ids = list(set(m["issue_id"] for m in member_rows))
        rep_issues = {}
        if rep_issue_ids:
            for batch_start in range(0, len(rep_issue_ids), 500):
                batch = rep_issue_ids[batch_start : batch_start + 500]
                rows = select_with_retry(sb, 
                    "issues",
                    columns="id,github_issue_number,title,github_url,state",
                    filters={"id": f"in.({','.join(batch)})"},
                )
                for r in rows:
                    rep_issues[r["id"]] = r

        evidence_by_cluster = {}
        for m in member_rows:
            issue = rep_issues.get(m["issue_id"])
            if not issue:
                continue
            evidence_by_cluster.setdefault(m["cluster_id"], []).append(
                {
                    "issueNumber": issue["github_issue_number"],
                    "title": issue["title"],
                    "githubUrl": issue["github_url"],
                    "state": issue.get("state"),
                }
            )

        def cluster_to_insight(c):
            params = c.get("clustering_params") or {}
            return {
                "id": c["id"],
                "clusterKey": c["cluster_key"],
                "name": c.get("cluster_name") or c["cluster_key"],
                "category": c["category"],
                "summary": c.get("summary"),
                "problemStatement": c.get("problem_statement"),
                "issueCount": int(c["issue_count"]),
                "primarySurface": c.get("primary_surface"),
                "primaryPlatform": c.get("primary_platform"),
                "avgSeverityScore": (
                    float(c["avg_severity_score"])
                    if c.get("avg_severity_score") is not None
                    else None
                ),
                "needsRefinement": bool(params.get("needs_refinement")),
                "isEmerging": bool(c.get("is_emerging")),
                "emergingScore": (
                    float(c["emerging_score"])
                    if c.get("emerging_score") is not None
                    else None
                ),
                "growthRate": (
                    float(c["growth_rate"])
                    if c.get("growth_rate") is not None
                    else None
                ),
                "currentPeriodCount": (
                    int(c["current_period_count"])
                    if c.get("current_period_count") is not None
                    else None
                ),
                "previousPeriodCount": (
                    int(c["previous_period_count"])
                    if c.get("previous_period_count") is not None
                    else None
                ),
                "clusteringParams": params,
                "representatives": evidence_by_cluster.get(c["id"], []),
            }

        insights_rows = sorted(
            [cluster_to_insight(c) for c in clusters],
            key=lambda x: -x["issueCount"],
        )[:50]

        report["insights"] = {
            "insights": insights_rows,
            "counts": {
                "total": total_clusters,
                "emerging": len(emerging),
                "needsRefinement": len(needs_ref),
            },
            "configured": True,
            "error": None,
        }

        # ── Releases data ──────────────────────────────────────────
        from datetime import datetime, timedelta, timezone

        releases = select_with_retry(sb, 
            "releases",
            columns="id,name,release_date,source_url,description",
            order="release_date.desc",
        )
        release_impacts = select_with_retry(sb, 
            "release_impacts",
            columns="release_id,cluster_id,before_count,after_count,signal_type",
        )
        # Paginated fetch for cluster names in impacts
        impact_cluster_ids = list(set(r["cluster_id"] for r in release_impacts))
        impact_clusters_map = {}
        if impact_cluster_ids:
            for batch_start in range(0, len(impact_cluster_ids), 500):
                batch = impact_cluster_ids[batch_start : batch_start + 500]
                rows = select_with_retry(sb, 
                    "clusters",
                    columns="id,cluster_key,cluster_name",
                    filters={"id": f"in.({','.join(batch)})"},
                )
                for r in rows:
                    impact_clusters_map[r["id"]] = r

        by_release = {}
        for imp in release_impacts:
            by_release.setdefault(imp["release_id"], []).append(imp)

        ds_start = datetime(2026, 8, 23, tzinfo=timezone.utc)
        ds_end = datetime(2026, 9, 6, tzinfo=timezone.utc)

        release_rows = []
        for r in releases:
            rd = datetime.fromisoformat(r["release_date"].replace("Z", "+00:00"))
            b_days = max(
                0,
                (min(rd, ds_end) - max(rd - timedelta(days=7), ds_start)).total_seconds()
                / 86400,
            )
            a_days = max(
                0,
                (min(rd + timedelta(days=7), ds_end) - max(rd, ds_start)).total_seconds()
                / 86400,
            )
            sufficient = b_days >= 5 and a_days >= 5

            impacts = by_release.get(r["id"], [])
            total_before = sum(i["before_count"] for i in impacts)
            total_after = sum(i["after_count"] for i in impacts)
            top_clusters = []
            for imp in sorted(impacts, key=lambda x: -abs(x["after_count"] - x["before_count"]))[:5]:
                cl = impact_clusters_map.get(imp["cluster_id"], {})
                top_clusters.append(
                    {
                        "clusterId": imp["cluster_id"],
                        "clusterKey": cl.get("cluster_key", ""),
                        "clusterName": cl.get("cluster_name", ""),
                        "beforeCount": imp["before_count"],
                        "afterCount": imp["after_count"],
                        "signalType": imp["signal_type"],
                    }
                )

            release_rows.append(
                {
                    "id": r["id"],
                    "name": r["name"],
                    "releaseDate": r["release_date"],
                    "sourceUrl": r["source_url"],
                    "description": r.get("description"),
                    "hasImpact": len(impacts) > 0,
                    "sufficientHistory": sufficient,
                    "totalBefore": total_before,
                    "totalAfter": total_after,
                    "impactedClusters": len(impacts),
                    "topClusters": top_clusters,
                }
            )

        report["releases"] = {"configured": True, "error": None, "rows": release_rows}

        # ── Opportunities data ─────────────────────────────────────
        opps = select_with_retry(sb, 
            "opportunities",
            columns="id,cluster_id,action_type,priority_score,frequency_score,severity_score,"
            "growth_score,engagement_score,priority_reason,product_hypothesis,action_brief",
        )
        opp_cluster_ids = list(set(o["cluster_id"] for o in opps))
        opp_clusters_map = {}
        if opp_cluster_ids:
            for batch_start in range(0, len(opp_cluster_ids), 500):
                batch = opp_cluster_ids[batch_start : batch_start + 500]
                rows = select_with_retry(sb, 
                    "clusters",
                    columns="id,cluster_key,cluster_name,category,issue_count,"
                    "current_period_count,previous_period_count,growth_rate,"
                    "is_emerging,clustering_params",
                    filters={"id": f"in.({','.join(batch)})"},
                )
                for r in rows:
                    opp_clusters_map[r["id"]] = r

        def opp_to_row(o):
            cl = opp_clusters_map.get(o["cluster_id"], {})
            params = cl.get("clustering_params") or {}
            trend = (params.get("trend") or {})
            reason = {}
            try:
                reason = json.loads(o.get("priority_reason") or "{}")
            except (json.JSONDecodeError, TypeError):
                pass
            components = reason.get("components", {})
            weights = reason.get("weights", {})
            brief = o.get("action_brief") or {}

            return {
                "id": o["id"],
                "clusterId": o["cluster_id"],
                "clusterKey": cl.get("cluster_key", ""),
                "name": cl.get("cluster_name", ""),
                "category": cl.get("category", ""),
                "size": int(cl.get("issue_count", 0)),
                "current": int(cl.get("current_period_count", 0)),
                "previous": int(cl.get("previous_period_count", 0)),
                "priority": float(o["priority_score"]),
                "components": components,
                "weights": weights,
                "action": o["action_type"],
                "trendState": reason.get("signal_state"),
                "signalScore": (
                    float(reason["signal_score"])
                    if reason.get("signal_score") is not None
                    else None
                ),
                "isEmerging": bool(cl.get("is_emerging")),
                "growthRate": (
                    float(cl["growth_rate"])
                    if cl.get("growth_rate") is not None
                    else None
                ),
                "shareDeltaPp": (
                    float(trend.get("share_delta_pp"))
                    if trend.get("share_delta_pp") is not None
                    else None
                ),
                "needsRefinement": bool(params.get("needs_refinement")),
                "engagement": float(o.get("engagement_score", 0)),
                "engagementAvailable": bool(reason.get("engagement_available")),
                "brief": brief if brief and brief != {} else None,
                "representatives": evidence_by_cluster.get(o["cluster_id"], []),
            }

        opp_rows = sorted(
            [opp_to_row(o) for o in opps], key=lambda x: -x["priority"]
        )

        report["opportunities"] = {"configured": True, "error": None, "rows": opp_rows}
        report["action-briefs"] = {
            "configured": True,
            "error": None,
            "rows": opp_rows,
        }

        # ── Add topOpportunities to overview ───────────────────────
        report["overview"]["topOpportunities"] = opp_rows[:50]
        report["overview"]["opportunityCount"] = len(opps)

        # ── Validation ─────────────────────────────────────────────
        print("=== SNAPSHOT VALIDATION ===")
        checks = [
            ("dataset_members", total_issues, 2254),
            ("in_scope_feedback", in_scope_count, 2096),
            ("production_clusters", total_clusters, 197),
            ("emerging_signals", len(emerging), 25),
            ("needs_refinement", len(needs_ref), 15),
            ("opportunities", len(opps), 44),
            ("non_empty_briefs", sum(1 for o in opps if o.get("action_brief") and o["action_brief"] != {}), 43),
            ("empty_briefs", sum(1 for o in opps if not o.get("action_brief") or o["action_brief"] == {}), 1),
            ("releases", len(releases), 12),
        ]

        # Count comparable releases
        comparable = sum(1 for r in release_rows if r["sufficientHistory"])
        insufficient = sum(1 for r in release_rows if not r["sufficientHistory"])
        checks.append(("comparable_releases", comparable, 1))
        checks.append(("insufficient_releases", insufficient, 11))

        # Status counts
        status_counts = {}
        for o in opps:
            status_counts[o["action_type"]] = status_counts.get(o["action_type"], 0) + 1
        checks.append(("investigate_now", status_counts.get("investigate_now", 0), 6))
        checks.append(("validate", status_counts.get("validate", 0), 9))
        checks.append(("monitor", status_counts.get("monitor", 0), 16))
        checks.append(("low_priority", status_counts.get("low_priority", 0), 13))

        all_pass = True
        for name, actual, expected in checks:
            ok = actual == expected
            status = "PASS" if ok else "FAIL"
            print(f"  {name}: {actual} (expected {expected}) [{status}]")
            if not ok:
                all_pass = False

        if not all_pass:
            print("\nVALIDATION FAILED — aborting snapshot.")
            return 1

        # ── Write snapshot ─────────────────────────────────────────
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for key, data in report.items():
            path = OUT_DIR / f"{key}.json"
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"  Wrote {path}")

        print(f"\nSnapshot complete: {len(report)} files in {OUT_DIR}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
