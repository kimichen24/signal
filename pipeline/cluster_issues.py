"""Semantic clustering within top-level categories (Prompt 03 A/B/C).

Membership is computed deterministically from the stored normalized E5
embeddings: per top-level category, agglomerative average-linkage clustering
with a cosine-distance threshold. The LLM never decides membership — it only
names/summarizes clusters after membership is fixed. Small categories are
not clustered and small/noisy groups stay unclustered; no cluster is
invented to fill the UI.

Reproducibility: threaded BLAS reduction order varies between processes,
which cascades through near-tie agglomerative merges into different
clusterings. This module therefore pins BLAS/OpenMP to a single thread
BEFORE numpy/sklearn are imported so a given config + embeddings always
produce identical membership in any process.

All functions here are pure and unit-tested; the CLI in this module only
loads data, persists results, and triggers naming.
"""

from __future__ import annotations

import os as _os

for _var in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    _os.environ.setdefault(_var, "1")

import hashlib
import json
from collections import Counter, defaultdict
from typing import Any

IN_SCOPE_VALUES = ("codex_core", "codex_adjacent")
SEVERITY_SCORES = {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}


def default_params(
    distance_threshold: float = 0.45,
    min_cluster_size: int = 5,
    min_category_size: int = 5,
    refinement_size_threshold: int = 15,
) -> dict[str, Any]:
    return {
        "algorithm": "agglomerative_average_cosine",
        "distance_threshold": distance_threshold,
        "min_cluster_size": min_cluster_size,
        "min_category_size": min_category_size,
        "library": "scikit-learn AgglomerativeClustering",
        # Clusters at or above this size are flagged needs_refinement:
        # they are too broad to be presented as one precise product pain
        # point (user-approved calibration rule, 2026-09).
        "refinement_size_threshold": refinement_size_threshold,
    }


def filter_eligible(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """In-scope rows with a successful analysis and a usable embedding."""
    eligible = []
    for row in rows:
        if row.get("product_scope") not in IN_SCOPE_VALUES:
            continue
        if row.get("analysis_error"):
            continue
        if not row.get("embedding"):
            continue
        eligible.append(row)
    return eligible


def parse_embedding(raw: Any) -> list[float]:
    if isinstance(raw, str):
        return [float(x) for x in json.loads(raw)]
    return [float(x) for x in raw or []]


def cluster_category(
    members: list[dict[str, Any]], params: dict[str, Any]
) -> tuple[list[list[int]], list[int]]:
    """Cluster one category's members by embedding.

    Returns (clusters, unclustered) as lists of member indices into
    `members`. Categories smaller than min_category_size are left
    unclustered entirely; clusters smaller than min_cluster_size are
    treated as noise.
    """
    n = len(members)
    if n < params["min_category_size"]:
        return [], list(range(n))

    from sklearn.cluster import AgglomerativeClustering

    matrix = [parse_embedding(m["embedding"]) for m in members]
    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=params["distance_threshold"],
        metric="cosine",
        linkage="average",
    )
    labels = model.fit_predict(matrix)

    grouped: dict[int, list[int]] = defaultdict(list)
    for idx, label in enumerate(labels):
        grouped[int(label)].append(idx)

    clusters: list[list[int]] = []
    unclustered: list[int] = []
    for label in sorted(grouped):
        members_idx = grouped[label]
        if len(members_idx) < params["min_cluster_size"]:
            unclustered.extend(members_idx)
        else:
            clusters.append(sorted(members_idx))
    # Deterministic order: largest first, then by smallest member index.
    clusters.sort(key=lambda g: (-len(g), g[0]))
    return clusters, sorted(unclustered)


def medoid_order(embeddings: list[list[float]]) -> list[int]:
    """Member indices sorted by mean cosine distance to the other members
    (medoid first). Deterministic; used for representative selection."""
    import math

    def dot(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    def magnitude(a: list[float]) -> float:
        return math.sqrt(dot(a, a)) or 1.0

    norms = [magnitude(v) for v in embeddings]
    n = len(embeddings)
    scores: list[tuple[float, int]] = []
    for i in range(n):
        total = 0.0
        for j in range(n):
            if i == j:
                continue
            cos = dot(embeddings[i], embeddings[j]) / (norms[i] * norms[j])
            total += 1.0 - max(-1.0, min(1.0, cos))
        scores.append((total / max(n - 1, 1), i))
    return [i for _, i in sorted(scores)]


def cluster_key(category: str, member_ids: list[str]) -> str:
    """Content-addressed key: same members -> same key (rerun-stable)."""
    digest = hashlib.md5(
        "|".join(sorted(member_ids)).encode("utf-8")
    ).hexdigest()[:8]
    return f"{category}:{digest}"


def dominant(values: list[str | None]) -> str | None:
    counts = Counter(v for v in values if v)
    if not counts:
        return None
    top = max(counts.values())
    return sorted(v for v, c in counts.items() if c == top)[0]


def build_cluster(
    category: str, members: list[dict[str, Any]], params: dict[str, Any]
) -> dict[str, Any]:
    """Assemble one cluster record from fixed membership (name comes later)."""
    member_ids = [m["issue_id"] for m in members]
    embeddings = [parse_embedding(m["embedding"]) for m in members]
    representative_order = medoid_order(embeddings)
    representative_ids = [
        members[i]["issue_id"] for i in representative_order[:3]
    ]
    coherence = coherence_stats(embeddings, list(range(len(members))))
    needs_refinement = (
        len(members) >= params.get("refinement_size_threshold", 15)
    )
    severities = [m.get("severity") for m in members]
    avg_severity = round(
        sum(SEVERITY_SCORES.get(s, 0.5) for s in severities) / len(members), 3
    )
    top_severity = max(
        (s for s in severities if s in SEVERITY_SCORES),
        key=lambda s: SEVERITY_SCORES[s],
        default=None,
    )
    return {
        "cluster_key": cluster_key(category, member_ids),
        "category": category,
        "cluster_name": None,  # filled by the (optional) naming step
        "summary": None,
        "problem_statement": None,
        "issue_count": len(members),
        "avg_severity_score": avg_severity,
        "top_severity": top_severity,
        "primary_platform": dominant([m.get("platform") for m in members]),
        "primary_surface": dominant([m.get("surface") for m in members]),
        "representative_ids": representative_ids,
        "members": members,
        "member_numbers": [
            int(m["github_issue_number"])
            for m in members
            if m.get("github_issue_number") is not None
        ],
        "representative_order": representative_order,
        "member_ids": member_ids,
        "coherence": coherence,
        "needs_refinement": needs_refinement,
        "params": params,
    }


def silhouette_by_category(
    by_category: dict[str, list[dict[str, Any]]],
    labels_by_category: dict[str, list[int]],
) -> dict[str, Any]:
    """Silhouette per category where mathematically valid (needs >= 2
    clusters AND n_labels < n). Never fabricated for single-cluster
    categories."""
    import numpy as np
    from sklearn.metrics import silhouette_score

    results: dict[str, Any] = {}
    for category, labels in labels_by_category.items():
        n_labels = len(set(labels))
        if n_labels < 2 or n_labels >= len(labels):
            results[category] = "not meaningful (needs >= 2 clusters)"
            continue
        matrix = np.array(
            [parse_embedding(m["embedding"]) for m in by_category[category]]
        )
        score = float(
            silhouette_score(matrix, np.array(labels), metric="cosine")
        )
        results[category] = round(score, 3)
    return results


def coherence_stats(
    embeddings: list[list[float]], member_indices: list[int]
) -> dict[str, Any]:
    """Internal-coherence diagnostics for one candidate cluster (no LLM):
    medoid plus cosine-similarity distributions (member-to-medoid and mean
    pairwise)."""
    import math
    import statistics

    members = [embeddings[i] for i in member_indices]

    def cos(a: list[float], b: list[float]) -> float:
        num = sum(x * y for x, y in zip(a, b))
        den = (
            math.sqrt(sum(x * x for x in a))
            * math.sqrt(sum(y * y for y in b))
        ) or 1.0
        return max(-1.0, min(1.0, num / den))

    sims_to_medoid = []
    order = medoid_order(members)
    medoid_pos = order[0]
    medoid = members[medoid_pos]
    for pos, member in enumerate(members):
        sim = cos(medoid, member)
        sims_to_medoid.append(
            {"position": pos, "similarity": round(sim, 3)}
        )

    pairwise = []
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            pairwise.append(cos(members[i], members[j]))

    sims = sorted(s["similarity"] for s in sims_to_medoid if s["position"] != medoid_pos) or [1.0]
    return {
        "medoid_issue_position": medoid_pos,
        "sim_to_medoid": {
            "min": min(sims),
            "median": round(statistics.median(sims), 3),
            "mean": round(statistics.mean(sims), 3),
            "max": max(sims),
        },
        "mean_pairwise_similarity": round(statistics.mean(pairwise), 3)
        if pairwise
        else 1.0,
    }


def cluster_all(
    rows: list[dict[str, Any]], params: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Cluster every eligible category. Returns (clusters, noise_rows,
    diagnostics)."""
    eligible = filter_eligible(rows)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(
        eligible, key=lambda r: int(r.get("github_issue_number") or 0)
    ):
        by_category[row["category"]].append(row)

    clusters: list[dict[str, Any]] = []
    noise: list[dict[str, Any]] = []
    per_category: dict[str, Any] = {}
    labels_by_category: dict[str, list[int]] = {}
    for category in sorted(by_category):
        members = by_category[category]
        grouped, unclustered = cluster_category(members, params)
        clusters.extend(build_cluster(category, [members[i] for i in g], params) for g in grouped)
        noise.extend(members[i] for i in unclustered)
        labels = [-1] * len(members)
        for label, group in enumerate(grouped):
            for idx in group:
                labels[idx] = label
        labels_by_category[category] = labels
        per_category[category] = {
            "eligible": len(members),
            "clusters": len(grouped),
            "clustered": sum(len(g) for g in grouped),
            "unclustered": len(unclustered),
            "clustered_at_all": len(grouped) > 0,
        }
        per_category[category]["silhouette"] = silhouette_by_category(
            {category: members}, {category: labels}
        )[category]

    clustered_count = sum(c["issue_count"] for c in clusters)
    diagnostics = {
        "eligible_issues": len(eligible),
        "excluded_out_of_scope_or_no_embedding": len(rows) - len(eligible),
        "clustered_issues": clustered_count,
        "unclustered_issues": len(noise),
        "coverage_pct": round(100 * clustered_count / len(eligible), 1)
        if eligible
        else 0.0,
        "cluster_count": len(clusters),
        "size_distribution": dict(
            Counter(str(c["issue_count"]) for c in clusters)
        ),
        "clusters_per_category": per_category,
        "largest_clusters": [
            {"name": c["cluster_key"], "size": c["issue_count"]}
            for c in sorted(clusters, key=lambda c: -c["issue_count"])[:10]
        ],
        "singleton_or_tiny_treated_as_noise": "clusters below "
        f"{params['min_cluster_size']} members stay unclustered",
        "params": params,
    }
    return clusters, noise, diagnostics


NAMING_SYSTEM_PROMPT = """You name and summarize a cluster of related GitHub issues about one product problem.

Return exactly one JSON object with keys:
- "name": concise cluster name, 3-60 characters, noun-phrase style (e.g. "Remote SSH connection failures")
- "summary": 2-3 neutral sentences describing the shared problem across the members
- "problem_statement": one sentence stating the product problem users experience

Rules:
- Base everything strictly on the member issues provided — do not invent features, causes, or fixes.
- No root-cause or causal claims ("caused by", "because the app").
- No severity or priority wording.
- English only."""

NAMING_MAX_MEMBERS = 12


def naming_payload(cluster: dict[str, Any]) -> str:
    members = cluster["members"][:NAMING_MAX_MEMBERS]
    lines = [
        f"- #{m.get('github_issue_number')} {m.get('title')} — subtopic: {m.get('subtopic')}"
        for m in members
    ]
    more = (
        f"\n(+{cluster['issue_count'] - len(members)} more members with the same pattern)"
        if cluster["issue_count"] > len(members)
        else ""
    )
    return (
        f"category: {cluster['category']}\n"
        f"member_count: {cluster['issue_count']}\n"
        f"members:\n" + "\n".join(lines) + more
    )


def validate_naming(obj: dict[str, Any]) -> list[str]:
    problems = []
    name = obj.get("name")
    if not isinstance(name, str) or not (3 <= len(name.strip()) <= 60):
        problems.append("name must be a 3-60 char string")
    for key in ("summary", "problem_statement"):
        value = obj.get(key)
        if not isinstance(value, str) or len(value.strip()) < 10:
            problems.append(f"{key} must be a non-trivial string")
    return problems


def name_clusters(
    clusters: list[dict[str, Any]], provider: Any, failures: list[str]
) -> int:
    """Name clusters via MiMo — only called after membership is fixed."""
    named = 0
    for cluster in clusters:
        payload = naming_payload(cluster)
        naming = None
        for attempt in (1, 2):  # one validation retry
            try:
                obj, _usage = provider.complete_json(
                    NAMING_SYSTEM_PROMPT, payload
                )
                problems = validate_naming(obj)
                if not problems:
                    naming = obj
                    break
                retry_hint = "; ".join(problems)
            except Exception as exc:
                retry_hint = f"{type(exc).__name__}: {exc}"[:200]
        if naming is None:
            failures.append(
                f"{cluster['cluster_key']}: naming failed — {retry_hint}"
            )
            continue
        cluster["cluster_name"] = naming["name"].strip()
        cluster["summary"] = naming["summary"].strip()
        cluster["problem_statement"] = naming["problem_statement"].strip()
        named += 1
    return named


def load_analysis_rows(
    supabase: Any, version: str
) -> list[dict[str, Any]]:
    rows = supabase.select_paged(
        "issue_analysis",
        columns=(
            "issue_id,category,subtopic,severity,platform,surface,"
            "product_scope,embedding,analysis_error,summary,"
            "user_scenario,user_impact,"
            "issues(github_issue_number,title,github_url,state,github_created_at)"
        ),
        filters={"analysis_version": f"eq.{version}"},
        # Deterministic row order: PostgREST returns arbitrary order
        # otherwise, and agglomerative tie-breaking is input-order
        # sensitive — cluster membership must be rerun-stable.
        order="issue_id",
    )
    merged = []
    for row in rows:
        merged.append({**row, **(row.get("issues") or {})})
    return merged


def persist_clusters(
    supabase: Any, version: str, clusters: list[dict[str, Any]]
) -> int:
    """Idempotent replace: delete this version's clusters (members cascade),
    then insert the fresh set with members and representative flags."""
    old = supabase.select(
        "clusters", columns="id", filters={"analysis_version": f"eq.{version}"}
    )
    for row in old:
        supabase.delete("clusters", {"id": f"eq.{row['id']}"})
    for cluster in clusters:
        record = {
            "analysis_version": version,
            "cluster_key": cluster["cluster_key"],
            "cluster_name": cluster["cluster_name"]
            or f"{cluster['category']} cluster ({cluster['issue_count']} issues)",
            "category": cluster["category"],
            "summary": cluster["summary"],
            "problem_statement": cluster["problem_statement"],
            "issue_count": cluster["issue_count"],
            "avg_severity_score": cluster["avg_severity_score"],
            "primary_platform": cluster["primary_platform"],
            "primary_surface": cluster["primary_surface"],
            "representative_issue_ids": cluster["representative_ids"],
            "clustering_params": {
                **cluster["params"],
                "needs_refinement": cluster["needs_refinement"],
                "coherence": cluster["coherence"],
                "quality_note": (
                    "broad cluster spanning multiple failure modes; flagged "
                    "for subtopic refinement as data grows"
                    if cluster["needs_refinement"]
                    else None
                ),
            },
        }
        inserted = supabase.insert("clusters", record)
        cluster["id"] = inserted["id"] if isinstance(inserted, dict) else None
        members = supabase.select(
            "issues",
            columns="id,github_issue_number",
            filters={
                "github_issue_number": f"in.({','.join(str(m) for m in cluster['member_numbers'])})"
            },
            limit=1000,
        )
        id_by_number = {m["github_issue_number"]: m["id"] for m in members}
        rep_set = set(cluster["representative_ids"])
        member_rows = []
        for member in cluster["members"]:
            issue_pk = id_by_number.get(member.get("github_issue_number"))
            if not issue_pk:
                continue
            member_rows.append(
                {
                    "cluster_id": cluster["id"],
                    "issue_id": issue_pk,
                    "is_representative": member["issue_id"] in rep_set,
                }
            )
        if member_rows:
            supabase.upsert(
                "cluster_members", member_rows, on_conflict="cluster_id,issue_id"
            )
    return len(clusters)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    import os
    import sys
    import time

    from pipeline.ai.base import AIConfigError
    from pipeline.supabase_client import (
        SupabaseConfigError,
        SupabaseRest,
        load_env,
    )

    parser = argparse.ArgumentParser(
        prog="python -m pipeline.cluster_issues",
        description="Deterministic semantic clustering (Prompt 03).",
    )
    parser.add_argument(
        "--analysis-version",
        default=os.environ.get("SIGNAL_ANALYSIS_VERSION", "v0.3.4"),
    )
    parser.add_argument(
        "--distance-threshold",
        type=float,
        default=float(os.environ.get("SIGNAL_CLUSTER_DISTANCE_THRESHOLD", "0.45")),
    )
    parser.add_argument(
        "--min-cluster-size",
        type=int,
        default=int(os.environ.get("SIGNAL_MIN_CLUSTER_SIZE", "5")),
    )
    parser.add_argument(
        "--skip-naming",
        action="store_true",
        help="persist clusters without LLM naming (fallback names)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="cluster and print diagnostics without writing or naming",
    )
    args = parser.parse_args(argv)

    params = default_params(
        distance_threshold=args.distance_threshold,
        min_cluster_size=args.min_cluster_size,
        min_category_size=args.min_cluster_size,
    )
    started = time.monotonic()
    try:
        with SupabaseRest.from_env() as supabase:
            rows = load_analysis_rows(supabase, args.analysis_version)
            clusters, noise, diagnostics = cluster_all(rows, params)
            print(json.dumps(diagnostics, indent=2, ensure_ascii=False))

            if args.dry_run:
                print("\n(dry-run: nothing written, no naming)")
                for cluster in clusters:
                    top = sorted(
                        cluster["members"],
                        key=lambda m: int(m.get("github_issue_number") or 0),
                    )[:3]
                    sample = ", ".join(
                        f"#{m.get('github_issue_number')}" for m in top
                    )
                    print(
                        f"  {cluster['cluster_key']} n={cluster['issue_count']} "
                        f"[{cluster['category']}] members: {sample}..."
                    )
                return 0

            failures: list[str] = []
            named = 0
            if args.skip_naming:
                notes = "naming skipped (--skip-naming)"
            else:
                from pipeline.ai.base import build_providers

                provider = build_providers(os.environ)
                named = name_clusters(clusters, provider, failures)
                notes = f"named {named}/{len(clusters)} by LLM"
            persisted = persist_clusters(supabase, args.analysis_version, clusters)
            supabase.insert(
                "analysis_runs",
                {
                    "run_type": "clustering",
                    "analysis_version": args.analysis_version,
                    "start_date": None,
                    "snapshot_at": __import__("datetime").datetime.now(
                        __import__("datetime").timezone.utc
                    ).isoformat(),
                    "item_count": persisted,
                    "params": {
                        **params,
                        "named_by_llm": named,
                        "notes": notes,
                        "noise_count": len(noise),
                        "runtime_seconds": round(time.monotonic() - started, 1),
                        **{
                            k: v
                            for k, v in diagnostics.items()
                            if k not in ("params",)
                        },
                    },
                    "error_summary": "; ".join(failures)[:500] or None,
                },
            )
            print(
                json.dumps(
                    {
                        "persisted_clusters": persisted,
                        "named_by_llm": named,
                        "noise": len(noise),
                        "failures": failures or None,
                    },
                    indent=2,
                )
            )
            return 0
    except (SupabaseConfigError, AIConfigError, RuntimeError, ValueError) as exc:
        print(f"Clustering failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
