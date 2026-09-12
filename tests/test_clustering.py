"""Tests for deterministic clustering (Prompt 03 A/B/C)."""

from pipeline.cluster_issues import (
    build_cluster,
    cluster_all,
    cluster_category,
    cluster_key,
    default_params,
    filter_eligible,
    medoid_order,
)


def vec(values):
    return "[" + ",".join(str(v) for v in values) + "]"


def make_row(number, embedding, *, scope="codex_core", category="Reliability",
             severity="high", platform="Windows", surface="CLI", subtopic="crash"):
    return {
        "issue_id": f"id-{number}",
        "github_issue_number": number,
        "embedding": vec(embedding) if embedding is not None else None,
        "product_scope": scope,
        "category": category,
        "severity": severity,
        "platform": platform,
        "surface": surface,
        "subtopic": subtopic,
        "analysis_error": None,
        "title": f"issue {number}",
    }


def make_population():
    """Category A: two tight groups + one outlier; Category B: too small to
    cluster."""
    rows = []
    for i in range(6):  # tight cluster A1: all near [0, 0, 1]
        rows.append(make_row(100 + i, [0.0, 0.0, 1.0], category="Reliability"))
    for i in range(5):  # tight cluster A2: all near [1, 0, 0]
        rows.append(make_row(200 + i, [1.0, 0.0, 0.0], category="Reliability"))
    rows.append(make_row(300, [0.0, 1.0, 0.0], category="Reliability"))  # outlier
    rows.append(make_row(400, [1.0, 0.0, 0.0], category="Performance"))  # category too small
    rows.append(make_row(401, [0.98, 0.0, 0.0], category="Performance"))
    return rows


class TestFilterEligible:
    def test_out_of_scope_and_missing_embeddings_excluded(self):
        rows = [
            make_row(1, [1.0, 0.0, 0.0]),
            make_row(2, [1.0, 0.0, 0.0], scope="out_of_scope"),
            make_row(3, None),
            make_row(4, [1.0, 0.0, 0.0], scope="codex_adjacent"),
        ]
        eligible = filter_eligible(rows)
        assert [r["issue_id"] for r in eligible] == ["id-1", "id-4"]


class TestClusterCategory:
    def test_small_category_not_clustered(self):
        members = [make_row(1, [1.0, 0.0, 0.0]), make_row(2, [1.0, 0.0, 0.0]), make_row(3, [1.0, 0.0, 0.0])]
        clusters, unclustered = cluster_category(members, default_params(min_cluster_size=5, min_category_size=5))
        assert clusters == []
        assert len(unclustered) == 3

    def test_tight_groups_cluster_and_outlier_is_noise(self):
        members = make_population()[:12]  # category A rows only
        params = default_params(min_cluster_size=3, min_category_size=5, distance_threshold=0.45)
        clusters, unclustered = cluster_category(members, params)
        sizes = sorted((len(c) for c in clusters), reverse=True)
        assert sizes == [6, 5]
        # The outlier (issue 300) must not be forced into any cluster.
        clustered_ids = {members[i]["issue_id"] for c in clusters for i in c}
        assert "id-300" not in clustered_ids
        assert members[unclustered[0]]["github_issue_number"] == 300

    def test_reproducibility(self):
        members = make_population()[:12]
        params = default_params(min_cluster_size=3, min_category_size=5, distance_threshold=0.45)
        first = cluster_category(members, params)
        second = cluster_category(members, params)
        assert first == second


class TestQualityFlag:
    def test_broad_cluster_flagged_needs_refinement(self):
        members = [
            make_row(500 + i, [1.0, 0.0, 0.0], subtopic=f"mode {i}")
            for i in range(15)
        ]
        cluster = build_cluster("Reliability", members, default_params(refinement_size_threshold=15))
        assert cluster["needs_refinement"] is True
        assert "medoid_issue_position" in cluster["coherence"]
        assert "mean_pairwise_similarity" in cluster["coherence"]

    def test_small_cluster_not_flagged(self):
        members = [make_row(600 + i, [1.0, 0.0, 0.0]) for i in range(5)]
        cluster = build_cluster("Reliability", members, default_params(refinement_size_threshold=15))
        assert cluster["needs_refinement"] is False

    def test_coherence_metadata_present(self):
        members = make_population()[:6]
        cluster = build_cluster("Reliability", members, default_params())
        assert cluster["coherence"]["sim_to_medoid"]["max"] <= 1.0
        assert 0.0 <= cluster["coherence"]["mean_pairwise_similarity"] <= 1.0


class TestClusterAll:
    def test_end_to_end_diagnostics(self):
        rows = make_population()
        params = default_params(min_cluster_size=3, min_category_size=5, distance_threshold=0.45)
        clusters, noise, diagnostics = cluster_all(rows, params)
        assert len(clusters) == 2
        assert diagnostics["eligible_issues"] == len(rows)
        assert diagnostics["clustered_issues"] == 11
        # 3 unclustered: the outlier + both Performance rows (category below
        # min_category_size stays unclustered — no invented cluster).
        assert diagnostics["unclustered_issues"] == 3
        assert diagnostics["coverage_pct"] == round(100 * 11 / 14, 1)
        # The too-small Performance category produced no clusters.
        assert diagnostics["clusters_per_category"]["Performance"]["clustered_at_all"] is False
        assert diagnostics["clusters_per_category"]["Performance"]["unclustered"] == 2
        # No out_of_scope member could ever appear (none here, but the
        # contract is that filter_eligible ran before clustering).
        assert all(c["category"] in ("Reliability",) for c in clusters)

    def test_out_of_scope_never_clustered_end_to_end(self):
        rows = make_population()
        rows.append(make_row(999, [0.0, 0.0, 0.91], scope="out_of_scope", category="Reliability"))
        params = default_params(min_cluster_size=3, min_category_size=5, distance_threshold=0.45)
        clusters, _, diagnostics = cluster_all(rows, params)
        all_members = {m["issue_id"] for c in clusters for m in c["members"]}
        assert "id-999" not in all_members
        assert diagnostics["eligible_issues"] == len(rows) - 1


class TestEvidenceAndRepresentatives:
    def test_representatives_are_members_and_traceable(self):
        members = make_population()[:6]
        cluster = build_cluster("Reliability", members, default_params())
        assert set(cluster["representative_ids"]) <= set(cluster["member_ids"])
        assert 1 <= len(cluster["representative_ids"]) <= 3
        # Every member keeps its GitHub issue number for evidence links.
        assert all(m["github_issue_number"] for m in cluster["members"])

    def test_medoid_is_the_central_point(self):
        embeddings = [
            [1.0, 0.0],
            [1.0, 0.1],
            [1.0, -0.1],
        ]
        order = medoid_order(embeddings)
        assert order[0] == 0  # the most central point is the medoid

        with_far_outlier = embeddings + [[0.0, 1.0]]
        assert medoid_order(with_far_outlier)[-1] == 3  # outlier ranks last

    def test_cluster_key_is_content_addressed_and_stable(self):
        ids = ["id-3", "id-1", "id-2"]
        assert cluster_key("Reliability", ids) == cluster_key("Reliability", ["id-1", "id-2", "id-3"])
        assert cluster_key("Reliability", ids) != cluster_key("CLI", ids)
