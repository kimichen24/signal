"""Read-only clustering parameter sweep + coherence diagnostics (Prompt 03
calibration). Never writes to the database and never invokes an LLM.

Subcommands:
  table    sweep distance thresholds x min_cluster_size, print diagnostics
  deep     full Reliability + App/UI/UX membership under one configuration
  compare  category-only vs category+issue_type partitioning
  final    full audit listing of every cluster for one configuration
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from typing import Any

from pipeline.cluster_issues import (
    coherence_stats,
    default_params,
    filter_eligible,
    load_analysis_rows,
    parse_embedding,
)
from pipeline.supabase_client import SupabaseRest, load_env

THRESHOLDS = (
    0.05, 0.08, 0.10, 0.12, 0.15, 0.18,
    0.20, 0.25, 0.30, 0.35, 0.40, 0.45,
)
MIN_SIZES = (3, 4, 5)


def dataset_median_similarity(
    embeddings: dict[str, list[float]], sample: int = 25, seed: int = 7
) -> float:
    """Dataset-wide median pairwise cosine on a seeded sample — the
    reference point for flagging loose clusters (e5 similarities live in a
    narrow high band)."""
    import random

    vectors = list(embeddings.values())
    pairs: list[float] = []
    rng = random.Random(seed)
    for i in rng.sample(range(len(vectors)), min(sample, len(vectors))):
        for j in rng.sample(range(len(vectors)), min(sample, len(vectors))):
            if i >= j:
                continue
            a, b = vectors[i], vectors[j]
            pairs.append(sum(x * y for x, y in zip(a, b)))
    return statistics.median(pairs) if pairs else 0.0

AUDIT_CATEGORIES = ("Reliability", "App / UI / UX")


def load_eligible(supabase: SupabaseRest, version: str) -> list[dict[str, Any]]:
    rows = supabase.select(
        "issue_analysis",
        columns=(
            "issue_id,issue_type,category,subtopic,severity,platform,surface,"
            "product_scope,embedding,analysis_error,"
            "issues(github_issue_number,title,github_url,state,github_created_at)"
        ),
        filters={"analysis_version": f"eq.{version}"},
        limit=1000,
    )
    merged = [{**row, **(row.get("issues") or {})} for row in rows]
    return filter_eligible(merged)


def group_rows(rows: list[dict[str, Any]], partition: str) -> dict[str, list]:
    grouped: dict[str, list] = defaultdict(list)
    for row in sorted(rows, key=lambda r: int(r["github_issue_number"])):
        key = (
            f"{row['category']}|{row.get('issue_type')}"
            if partition == "category_type"
            else row["category"]
        )
        grouped[key].append(row)
    return grouped


def run_config(
    rows: list[dict[str, Any]],
    threshold: float,
    min_size: int,
    partition: str = "category",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Cluster all rows under one configuration. Returns (clusters, stats)."""
    params = default_params(
        distance_threshold=threshold,
        min_cluster_size=min_size,
        min_category_size=min_size,
    )
    grouped = group_rows(rows, partition)
    embeddings = {
        r["issue_id"]: parse_embedding(r["embedding"]) for r in rows
    }
    weak_bar = dataset_median_similarity(embeddings)
    clusters: list[dict[str, Any]] = []
    noise_total = 0
    tiny_rejected_members = 0
    small_category_members = 0
    per_category: dict[str, Any] = {}

    for key in sorted(grouped):
        members = grouped[key]
        category_label = key.split("|")[0]
        if len(members) < min_size:
            small_category_members += len(members)
            noise_total += len(members)
            per_category[key] = {
                "eligible": len(members),
                "clusters": 0,
                "clustered": 0,
                "unclustered": len(members),
                "reason": "category below min size",
            }
            continue
        result_clusters, unclustered = [], []
        try:
            from pipeline.cluster_issues import cluster_category

            result_clusters, unclustered = cluster_category(members, params)
        except Exception as exc:
            per_category[key] = {"error": str(exc)}
            continue
        category_clusters = []
        for group in result_clusters:
            member_rows = [members[i] for i in group]
            stats = coherence_stats(
                [embeddings[r["issue_id"]] for r in member_rows],
                list(range(len(group))),
            )
            cluster = {
                "partition_key": key,
                "category": category_label,
                "issue_type": (
                    members[group[0]].get("issue_type")
                    if partition == "category_type"
                    else None
                ),
                "size": len(group),
                "members": member_rows,
                "coherence": stats,
                "weak": stats["mean_pairwise_similarity"] < weak_bar,
            }
            category_clusters.append(cluster)
            clusters.append(cluster)
        tiny = sum(len(unclustered_group) for unclustered_group in [unclustered])
        tiny_rejected_members += tiny
        noise_total += tiny
        per_category[key] = {
            "eligible": len(members),
            "clusters": len(category_clusters),
            "clustered": sum(c["size"] for c in category_clusters),
            "unclustered": tiny,
            "weak_clusters": sum(1 for c in category_clusters if c["weak"]),
        }

    sizes = sorted((c["size"] for c in clusters), reverse=True)
    stats = {
        "threshold": threshold,
        "min_cluster_size": min_size,
        "partition": partition,
        "total_clusters": len(clusters),
        "clustered_issues": sum(sizes),
        "noise_issues": noise_total,
        "coverage_pct": round(100 * sum(sizes) / len(rows), 1) if rows else 0.0,
        "largest_cluster": sizes[0] if sizes else 0,
        "median_cluster_size": statistics.median(sizes) if sizes else 0,
        "clusters_per_category": per_category,
        "tiny_groups_rejected_members": tiny_rejected_members,
        "small_category_unclustered_members": small_category_members,
        "weak_clusters": sum(1 for c in clusters if c["weak"]),
        "clusters": clusters,
    }
    return clusters, stats


def print_table(all_stats: list[dict[str, Any]]) -> None:
    header = (
        f"{'thr':>5} {'mcs':>4} {'clusters':>8} {'clustered':>9} {'noise':>6} "
        f"{'cover%':>7} {'largest':>8} {'median':>7} {'weak':>5} {'cats':>5}"
    )
    print(header)
    print("-" * len(header))
    for s in sorted(
        all_stats, key=lambda s: (s["threshold"], s["min_cluster_size"])
    ):
        n_cats = sum(
            1
            for v in s["clusters_per_category"].values()
            if isinstance(v, dict) and v.get("clusters")
        )
        print(
            f"{s['threshold']:>5.2f} {s['min_cluster_size']:>4} "
            f"{s['total_clusters']:>8} {s['clustered_issues']:>9} "
            f"{s['noise_issues']:>6} {s['coverage_pct']:>7} "
            f"{s['largest_cluster']:>8} {s['median_cluster_size']:>7} "
            f"{s['weak_clusters']:>5} {n_cats:>5}"
        )


def print_deep(
    clusters: list[dict[str, Any]], categories: tuple[str, ...]
) -> None:
    for category in categories:
        relevant = sorted(
            [c for c in clusters if c["category"] == category],
            key=lambda c: -c["size"],
        )
        print(f"\n### {category} ({len(relevant)} clusters)")
        for cluster in relevant:
            medoid = cluster["members"][
                cluster["coherence"]["medoid_issue_position"]
            ]
            sim = cluster["coherence"]["sim_to_medoid"]
            print(
                f"\n  [n={cluster['size']}] medoid=#{medoid['github_issue_number']} "
                f"sim->medoid min/med/mean/max = {sim['min']}/{sim['median']}/"
                f"{sim['mean']}/{sim['max']} | pairwise={cluster['coherence']['mean_pairwise_similarity']}"
                f"{'  << WEAK' if cluster['weak'] else ''}"
            )
            for member in cluster["members"]:
                print(
                    f"    #{member['github_issue_number']} "
                    f"[{member.get('issue_type')}] {member['title'][:66]} "
                    f"— {member.get('subtopic', '')[:40]}"
                )


def print_final(clusters: list[dict[str, Any]]) -> None:
    ordered = sorted(clusters, key=lambda c: (c["category"], -c["size"]))
    for cluster in ordered:
        medoid = cluster["members"][
            cluster["coherence"]["medoid_issue_position"]
        ]
        sim = cluster["coherence"]["sim_to_medoid"]
        print(f"\n[{cluster['category']}] n={cluster['size']}  "
              f"medoid=#{medoid['github_issue_number']}  "
              f"pairwise={cluster['coherence']['mean_pairwise_similarity']}")
        print(f"  members: " + ", ".join(
            f"#{m['github_issue_number']}" for m in cluster["members"]
        ))
        print(f"  titles :")
        for m in cluster["members"]:
            print(f"    #{m['github_issue_number']} {m['title'][:78]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline.cluster_sweep")
    parser.add_argument("command", choices=["table", "deep", "compare", "final"])
    parser.add_argument("--analysis-version", default="v0.3.4")
    parser.add_argument("--threshold", type=float, default=0.30)
    parser.add_argument("--min-size", type=int, default=3)
    parser.add_argument(
        "--partition", choices=["category", "category_type"], default="category"
    )
    args = parser.parse_args(argv)

    with SupabaseRest.from_env() as supabase:
        rows = load_eligible(supabase, args.analysis_version)
    print(f"eligible rows: {len(rows)}")

    if args.command == "table":
        all_stats = []
        for threshold in THRESHOLDS:
            for min_size in MIN_SIZES:
                _, stats = run_config(rows, threshold, min_size)
                all_stats.append({k: v for k, v in stats.items() if k != "clusters"})
        print_table(all_stats)
        return 0

    if args.command == "deep":
        clusters, _ = run_config(rows, args.threshold, args.min_size, args.partition)
        print_deep(clusters, AUDIT_CATEGORIES)
        return 0

    if args.command == "compare":
        print(f"=== threshold={args.threshold} min_size={args.min_size} ===")
        for partition in ("category", "category_type"):
            clusters, stats = run_config(rows, args.threshold, args.min_size, partition)
            print(
                f"\n[{partition}] clusters={stats['total_clusters']} "
                f"clustered={stats['clustered_issues']} noise={stats['noise_issues']} "
                f"coverage={stats['coverage_pct']}% largest={stats['largest_cluster']} "
                f"median={stats['median_cluster_size']} weak={stats['weak_clusters']}"
            )
            for cluster in sorted(clusters, key=lambda c: -c["size"]):
                print(
                    f"  [{cluster['partition_key']}] n={cluster['size']} "
                    f"pairwise={cluster['coherence']['mean_pairwise_similarity']}"
                    f"{' WEAK' if cluster['weak'] else ''}"
                )
        return 0

    if args.command == "final":
        clusters, stats = run_config(rows, args.threshold, args.min_size)
        print(
            json.dumps(
                {
                    k: v
                    for k, v in stats.items()
                    if k not in ("clusters", "clusters_per_category")
                },
                indent=2,
            )
        )
        print_final(clusters)
        return 0
    return 1


if __name__ == "__main__":
    load_env()
    raise SystemExit(main())
