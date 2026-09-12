"""Tests for the fresh holdout sampler: exclusions, non-leaking strata,
platform diversity, blind CSV shape (no AI fields)."""

import csv

from pipeline.sample_holdout import (
    interleave_by_platform,
    labels_to_names,
    length_bounds,
    platform_group,
    select_holdout,
)


def make_row(number, created_at, chars, *, platform=None, template=True,
             scope=None, has_embedding=True):
    return {
        "issue_id": f"id-{number}",
        "github_issue_number": number,
        "github_created_at": created_at,
        "body_clean": "x" * chars,
        "parsed_platform": platform,
        "parsed_actual": "What happened" if template else None,
        "parsed_version": "1.0" if template else None,
        "github_labels": [{"name": "bug"}, {"name": "app"}],
        # AI fields must never influence selection or appear in blind output
        "product_scope": scope,
        "avg_severity_score": 0.9,
        "confidence": 0.95,
        "needs_review": False,
        "embedding": "[1,2,3]" if has_embedding else None,
    }


def make_pool():
    rows = []
    number = 2000
    # 60 rows across both periods, 4 platforms, all length terciles,
    # mixed template availability — plus the entire excluded population.
    for period_start, n in (("2026-08-24T00:00:00Z", 30), ("2026-09-01T00:00:00Z", 30)):
        for i in range(n):
            platform = ["Windows", "macOS", "Linux", None][i % 4]
            rows.append(
                make_row(
                    number,
                    period_start,
                    200 + (i % 9) * 400,
                    platform=platform,
                    template=(i % 3 != 0),
                )
            )
            number += 1
    return rows


class TestExclusions:
    def test_excluded_ids_never_selected(self):
        pool = make_pool()
        excluded = {f"id-{n}" for n in range(2000, 2015)}
        selected, meta = select_holdout(pool, excluded, seed=42, total=20)
        numbers = {r["github_issue_number"] for r in selected}
        assert numbers.isdisjoint(range(2000, 2015))
        assert meta["pool_size"] == len(pool) - 15

    def test_previously_used_samples_not_consulted_for_strata(self):
        # AI fields on rows are irrelevant to selection: same selection with
        # and without AI fields present.
        pool = make_pool()
        a, _ = select_holdout(pool, {f"id-{n}" for n in range(2100, 2105)}, 42, 20)
        stripped = [
            {k: v for k, v in r.items() if k not in ("product_scope", "avg_severity_score", "confidence", "needs_review")}
            for r in pool
        ]
        b, _ = select_holdout(stripped, {f"id-{n}" for n in range(2100, 2105)}, 42, 20)
        assert [r["issue_id"] for r in a] == [r["issue_id"] for r in b]


class TestStrataAndDiversity:
    def test_both_periods_represented(self):
        selected, _ = select_holdout(make_pool(), set(), seed=42, total=30)
        periods = {r["github_created_at"][:7] for r in selected}
        assert len(periods) == 2  # 2026-08 and 2026-09 both present

    def test_platform_mix_not_degenerate(self):
        selected, _ = select_holdout(make_pool(), set(), seed=42, total=30)
        groups = {platform_group(r.get("parsed_platform")) for r in selected}
        assert len(groups) >= 2  # more than a single platform group

    def test_deterministic_for_fixed_seed(self):
        a, _ = select_holdout(make_pool(), set(), seed=42, total=30)
        b, _ = select_holdout(make_pool(), set(), seed=42, total=30)
        assert [r["issue_id"] for r in a] == [r["issue_id"] for r in b]

    def test_interleave_covers_all_and_is_deterministic(self):
        import random

        members = [
            make_row(1, "2026-09-01T00:00:00Z", 100, platform="Windows"),
            make_row(2, "2026-09-01T00:00:00Z", 100, platform="macOS"),
            make_row(3, "2026-09-01T00:00:00Z", 100, platform=None),
        ]
        rng = random.Random(42)
        order = interleave_by_platform(members, rng)
        assert len(order) == 3
        again = interleave_by_platform(members, random.Random(42))
        assert [r["issue_id"] for r in order] == [r["issue_id"] for r in again]


class TestHelpers:
    def test_platform_group_mapping(self):
        assert platform_group("Microsoft Windows NT 10.0") == "Windows"
        assert platform_group("macOS 15.5") == "macOS"
        assert platform_group("Ubuntu 24.04") == "Linux"
        assert platform_group(None) == "unknown_or_other"

    def test_labels_to_names(self):
        assert labels_to_names([{"name": "bug"}, {"name": "app"}]) == "bug, app"
        assert labels_to_names("bug, app") == "bug, app"
        assert labels_to_names(None) == ""

    def test_length_bounds(self):
        short, medium = length_bounds([100, 200, 300, 400, 500, 600])
        assert short == 300 and medium == 500


class TestBlindCsvShape:
    def test_written_csv_has_no_ai_columns(self, tmp_path):
        blind_path = tmp_path / "blind.csv"
        manifest_path = tmp_path / "manifest.json"
        # The writer is exercised end-to-end via the module CLI in
        # test_holdout_cli.py; here we assert the column contract directly
        # against the generator's column list.
        from pipeline.sample_holdout import BLIND_COLUMNS

        assert not any(c.startswith("ai_") for c in BLIND_COLUMNS)
        assert "audit_group" not in BLIND_COLUMNS
        assert "cluster_name" not in BLIND_COLUMNS
        for col in (
            "github_issue_number",
            "title",
            "body_clean",
            "human_product_scope",
            "human_issue_type",
            "human_category",
            "human_surface",
            "human_platform",
            "human_severity",
            "human_notes",
        ):
            assert col in BLIND_COLUMNS
        with blind_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=BLIND_COLUMNS)
            writer.writeheader()
            writer.writerow({col: "" for col in BLIND_COLUMNS})
        with blind_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert rows[0]["human_product_scope"] == ""
