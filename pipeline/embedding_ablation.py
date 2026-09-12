"""Embedding representation ablation A/B (Prompt 03 calibration).

A (current):   Title, Summary, Scenario, Impact, Category, Subtopic
B (candidate): Title, Summary, Scenario, Impact, Subtopic   (Category removed)

Same model (intfloat/multilingual-e5-small), same passage prefix, same
normalized vectors, same clustering config (threshold=0.15, mcs=3,
category-only). Read-only: no DB writes, no LLM calls, production
embeddings/clusters untouched.
"""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict

from pipeline.ai.base import semantic_text
from pipeline.ai.embeddings import build_embedding_provider
from pipeline.cluster_issues import (
    coherence_stats,
    default_params,
    filter_eligible,
    load_analysis_rows,
    medoid_order,
)
from pipeline.supabase_client import SupabaseRest


def semantic_text_b(row: dict) -> str:
    """Representation B: identical to semantic_text minus the Category line."""
    return (
        f"Title: {row.get('title', '')}\n"
        f"Summary: {row.get('summary', '')}\n"
        f"Scenario: {row.get('user_scenario') or ''}\n"
        f"Impact: {row.get('user_impact') or ''}\n"
        f"Subtopic: {row.get('subtopic', '')}"
    )


def global_pairwise(vectors: list[list[float]]) -> dict:
    sims = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            sims.append(sum(x * y for x, y in zip(vectors[i], vectors[j])))
    return {
        "pairs": len(sims),
        "min": round(min(sims), 3),
        "p10": round(sorted(sims)[len(sims) // 10], 3),
        "median": round(statistics.median(sims), 3),
        "mean": round(statistics.mean(sims), 3),
        "p90": round(sorted(sims)[(len(sims) * 9) // 10], 3),
        "max": round(max(sims), 3),
    }


def cluster_variant(
    rows: list[dict[str, Any]], vectors: dict[str, list[float]], threshold: float,
    min_size: int,
) -> tuple[list[dict], dict]:
    from pipeline.cluster_issues import cluster_category

    params = default_params(
        distance_threshold=threshold, min_cluster_size=min_size,
        min_category_size=min_size,
    )
    by_category: dict[str, list] = defaultdict(list)
    for row in sorted(rows, key=lambda r: int(r["github_issue_number"])):
        by_category[row["category"]].append(row)

    clusters: list[dict] = []
    noise = 0
    per_category: dict[str, Any] = {}
    for category in sorted(by_category):
        members = by_category[category]
        member_vecs = [vectors[m["issue_id"]] for m in members]
        if len(members) < min_size:
            noise += len(members)
            per_category[category] = {
                "eligible": len(members), "clusters": 0,
                "unclustered": len(members), "reason": "below min size",
            }
            continue
        grouped, unclustered = cluster_category(
            [{**m, "embedding": v} for m, v in zip(members, member_vecs)],
            params,
        )
        for group in grouped:
            vecs = [member_vecs[i] for i in group]
            co = coherence_stats(vecs, list(range(len(group))))
            order = medoid_order(vecs)
            clusters.append(
                {
                    "category": category,
                    "size": len(group),
                    "medoid": members[group[order[0]]]["github_issue_number"],
                    "coherence": co,
                    "pairwise": co["mean_pairwise_similarity"],
                    "members": [members[i] for i in group],
                    "member_numbers": [
                        members[i]["github_issue_number"] for i in group
                    ],
                }
            )
        noise += len(unclustered)
        per_category[category] = {
            "eligible": len(members),
            "clusters": len(grouped),
            "clustered": sum(len(g) for g in grouped),
            "unclustered": len(unclustered),
        }

    sizes = sorted((c["size"] for c in clusters), reverse=True)
    clustered = sum(sizes)
    diagnostics = {
        "cluster_count": len(clusters),
        "clustered": clustered,
        "noise": noise,
        "coverage_pct": round(100 * clustered / len(rows), 1),
        "max_size": sizes[0] if sizes else 0,
        "median_size": statistics.median(sizes) if sizes else 0,
        "size_distribution": dict(Counter(str(s) for s in sizes)),
        "per_category": per_category,
        "weak_clusters": sum(
            1
            for c in clusters
            if c["pairwise"] < 0.843  # dataset-wide median from variant A
        ),
    }
    return clusters, diagnostics


def print_variant(name: str, rows, vectors, threshold, min_size) -> list[dict]:
    clusters, diag = cluster_variant(rows, vectors, threshold, min_size)
    diag["global_pairwise"] = global_pairwise(list(vectors.values()))
    print(f"\n===== {name} =====")
    print(json.dumps(diag, indent=2, ensure_ascii=False))
    return clusters


def print_members(name: str, clusters: list[dict], categories) -> None:
    print(f"\n----- {name}: Reliability + App / UI / UX membership -----")
    for category in categories:
        relevant = [c for c in clusters if c["category"] == category]
        print(f"\n{category} ({len(relevant)} clusters, "
              f"{sum(c['size'] for c in relevant)} clustered)")
        for cluster in sorted(relevant, key=lambda c: -c["size"]):
            co = cluster["coherence"]
            print(
                f"  [n={cluster['size']}] medoid=#{cluster['medoid']} "
                f"sim->medoid {co['sim_to_medoid']['min']}/{co['sim_to_medoid']['median']}"
                f"/{co['sim_to_medoid']['mean']}/{co['sim_to_medoid']['max']} "
                f"pairwise={cluster['pairwise']}"
            )
            for member in cluster["members"]:
                print(
                    f"    #{member['github_issue_number']} "
                    f"{member['title'][:70]}"
                )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.embedding_ablation"
    )
    parser.add_argument("--analysis-version", default="v0.3.4")
    parser.add_argument("--threshold", type=float, default=0.15)
    parser.add_argument("--min-size", type=int, default=3)
    args = parser.parse_args()

    with SupabaseRest.from_env() as supabase:
        rows = filter_eligible(
            load_analysis_rows(supabase, args.analysis_version)
        )
    print(f"eligible rows: {len(rows)}")

    provider = build_embedding_provider(
        {
            "EMBEDDING_PROVIDER": "local",
            "LOCAL_EMBEDDING_MODEL": "intfloat/multilingual-e5-small",
            "EMBEDDING_DIMENSION": "384",
            "LOCAL_EMBEDDING_PREFIX": "passage:",
        }
    )

    vectors_a = {
        row["issue_id"]: vec
        for row, vec in zip(
            rows, provider.embed([semantic_text(row) for row in rows])
        )
    }
    vectors_b = {
        row["issue_id"]: vec
        for row, vec in zip(
            rows, provider.embed([semantic_text_b(row) for row in rows])
        )
    }

    clusters_a = print_variant(
        "A (current: includes Category line)",
        rows, vectors_a, args.threshold, args.min_size,
    )
    clusters_b = print_variant(
        "B (ablation: Category line removed)",
        rows, vectors_b, args.threshold, args.min_size,
    )
    categories = ("Reliability", "App / UI / UX")
    print_members("A", clusters_a, categories)
    print_members("B", clusters_b, categories)
    return 0


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
