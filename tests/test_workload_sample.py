"""Tests for the reproducible stratified workload sample + input hash."""

from pipeline.analyze_issue import compute_input_hash
from pipeline.sample_workload import length_bounds, length_bucket, stratified_sample


def make_row(number, created_at, body_chars, *, template=True):
    return {
        "issue_id": f"id-{number}",
        "github_issue_number": number,
        "github_created_at": created_at,
        "body_clean": "x" * body_chars,
        "parsed_actual": "What happened" if template else None,
        "parsed_version": "1.0" if template else None,
    }


def make_pool() -> list[dict]:
    rows = []
    # 30 per period; lengths cycle 100..2710 across template/non-template.
    number = 1000
    for period_start, period_rows in (
        ("2026-08-24T00:00:00Z", 30),
        ("2026-09-01T00:00:00Z", 30),
    ):
        for i in range(period_rows):
            rows.append(
                make_row(
                    number,
                    period_start,
                    100 + (i % 10) * 290,
                    template=(i % 2 == 0),
                )
            )
            number += 1
    return rows


class TestLengthBuckets:
    def test_bounds_split_pool_in_terciles(self):
        rows = make_pool()
        bounds = length_bounds([len(r["body_clean"]) for r in rows])
        buckets = [length_bucket(len(r["body_clean"]), bounds) for r in rows]
        assert set(buckets) == {"short", "medium", "long"}

    def test_bucket_assignment(self):
        bounds = (100, 200)
        assert length_bucket(50, bounds) == "short"
        assert length_bucket(150, bounds) == "medium"
        assert length_bucket(500, bounds) == "long"


class TestStratifiedSample:
    def test_selects_requested_unique_rows(self):
        selected, meta = stratified_sample(make_pool(), seed=42, total=50)
        assert meta["selected"] == 50
        assert meta["shortfall"] == 0
        numbers = [r["github_issue_number"] for r in selected]
        assert len(numbers) == len(set(numbers)) == 50

    def test_deterministic_for_fixed_seed(self):
        a, _ = stratified_sample(make_pool(), seed=42, total=50)
        b, _ = stratified_sample(make_pool(), seed=42, total=50)
        assert [r["issue_id"] for r in a] == [r["issue_id"] for r in b]

    def test_strata_are_recorded_and_varied(self):
        selected, meta = stratified_sample(make_pool(), seed=42, total=50)
        strata = {r["stratum"] for r in selected}
        # Both periods and template/non-template must appear.
        assert any(s.startswith("previous|") for s in strata)
        assert any(s.startswith("current|") for s in strata)
        assert any("|template|" in s for s in strata)
        assert any("|non_template|" in s for s in strata)
        assert meta["allocation"]

    def test_shortfall_reported_when_pool_too_small(self):
        small = make_pool()[:6]
        selected, meta = stratified_sample(small, seed=42, total=50)
        assert meta["shortfall"] == 50 - len(selected)
        assert len(selected) == 6


class TestComputeInputHash:
    def test_deterministic_and_sensitive(self):
        assert compute_input_hash("payload") == compute_input_hash("payload")
        assert compute_input_hash("payload") != compute_input_hash("payload2")

    def test_sha256_hex_format(self):
        value = compute_input_hash("a")
        assert len(value) == 64
        int(value, 16)  # valid hex
