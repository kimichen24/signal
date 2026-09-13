"""Tests for release_impact window computation (v0.2 fix).

Validates that before/after windows are non-overlapping, correctly
clipped, and produce the expected counts for synthetic fixtures.
"""

from datetime import datetime, timezone

from pipeline.release_impact import (
    MIN_COVERAGE_DAYS,
    clipped_before_window,
    clipped_after_window,
    signal_type,
    change_rate,
)

DS_START = datetime(2026, 8, 23, tzinfo=timezone.utc)
DS_END = datetime(2026, 9, 6, tzinfo=timezone.utc)
WINDOW_DAYS = 7


class TestWindowNonOverlap:
    """Before and after windows must not overlap."""

    def test_before_end_equals_after_start(self):
        release = datetime(2026, 8, 29, tzinfo=timezone.utc)
        _, b_end, _ = clipped_before_window(release, WINDOW_DAYS, DS_START, DS_END)
        a_start, _, _ = clipped_after_window(release, WINDOW_DAYS, DS_START, DS_END)
        assert b_end == a_start == release

    def test_no_overlapping_issues_mid_dataset(self):
        """3 issues before, 5 after — non-overlapping counts."""
        release = datetime(2026, 8, 29, tzinfo=timezone.utc)
        b_start, b_end, _ = clipped_before_window(release, WINDOW_DAYS, DS_START, DS_END)
        a_start, a_end, _ = clipped_after_window(release, WINDOW_DAYS, DS_START, DS_END)
        # Synthetic issues
        issues = [
            datetime(2026, 8, 24, tzinfo=timezone.utc),  # before
            datetime(2026, 8, 26, tzinfo=timezone.utc),  # before
            datetime(2026, 8, 28, tzinfo=timezone.utc),  # before
            datetime(2026, 8, 29, tzinfo=timezone.utc),  # after (== release)
            datetime(2026, 8, 30, tzinfo=timezone.utc),  # after
            datetime(2026, 9, 1, tzinfo=timezone.utc),   # after
            datetime(2026, 9, 3, tzinfo=timezone.utc),   # after
            datetime(2026, 9, 4, tzinfo=timezone.utc),   # after
        ]
        before_count = sum(1 for t in issues if b_start <= t < b_end)
        after_count = sum(1 for t in issues if a_start <= t < a_end)
        assert before_count == 3, f"Expected 3 before, got {before_count}"
        assert after_count == 5, f"Expected 5 after, got {after_count}"
        # Verify no overlap: no issue counted in both
        for t in issues:
            in_before = b_start <= t < b_end
            in_after = a_start <= t < a_end
            assert not (in_before and in_after), f"{t} counted in both windows"


class TestDatasetStartClipping:
    """Releases near dataset start get clipped before windows."""

    def test_before_window_clipped_at_dataset_start(self):
        release = datetime(2026, 8, 25, tzinfo=timezone.utc)
        b_start, b_end, days = clipped_before_window(release, WINDOW_DAYS, DS_START, DS_END)
        assert b_start == DS_START, f"Should clip to ds_start, got {b_start}"
        assert b_end == release
        assert abs(days - 2.0) < 0.01, f"Expected ~2 days, got {days}"

    def test_after_window_not_clipped_near_start(self):
        release = datetime(2026, 8, 25, tzinfo=timezone.utc)
        a_start, a_end, days = clipped_after_window(release, WINDOW_DAYS, DS_START, DS_END)
        assert a_start == release
        expected_end = datetime(2026, 9, 1, tzinfo=timezone.utc)
        assert a_end == expected_end
        assert abs(days - 7.0) < 0.01


class TestDatasetEndClipping:
    """Releases near dataset end get clipped after windows."""

    def test_after_window_clipped_at_dataset_end(self):
        release = datetime(2026, 9, 4, tzinfo=timezone.utc)
        a_start, a_end, days = clipped_after_window(release, WINDOW_DAYS, DS_START, DS_END)
        assert a_start == release
        assert a_end == DS_END
        assert abs(days - 2.0) < 0.01, f"Expected ~2 days, got {days}"

    def test_before_window_not_clipped_near_end(self):
        release = datetime(2026, 9, 4, tzinfo=timezone.utc)
        b_start, b_end, days = clipped_before_window(release, WINDOW_DAYS, DS_START, DS_END)
        expected_start = datetime(2026, 8, 28, tzinfo=timezone.utc)
        assert b_start == expected_start
        assert b_end == release
        assert abs(days - 7.0) < 0.01


class TestInsufficientCoverage:
    """Releases with < MIN_COVERAGE_DAYS on either side."""

    def test_insufficient_before(self):
        release = datetime(2026, 8, 24, tzinfo=timezone.utc)
        _, _, b_days = clipped_before_window(release, WINDOW_DAYS, DS_START, DS_END)
        _, _, a_days = clipped_after_window(release, WINDOW_DAYS, DS_START, DS_END)
        assert b_days < MIN_COVERAGE_DAYS
        assert a_days >= MIN_COVERAGE_DAYS

    def test_insufficient_after(self):
        release = datetime(2026, 9, 5, tzinfo=timezone.utc)
        _, _, b_days = clipped_before_window(release, WINDOW_DAYS, DS_START, DS_END)
        _, _, a_days = clipped_after_window(release, WINDOW_DAYS, DS_START, DS_END)
        assert b_days >= MIN_COVERAGE_DAYS
        assert a_days < MIN_COVERAGE_DAYS

    def test_outside_dataset_both_insufficient(self):
        release = datetime(2026, 9, 10, tzinfo=timezone.utc)
        _, _, b_days = clipped_before_window(release, WINDOW_DAYS, DS_START, DS_END)
        _, _, a_days = clipped_after_window(release, WINDOW_DAYS, DS_START, DS_END)
        assert b_days < MIN_COVERAGE_DAYS
        assert a_days < MIN_COVERAGE_DAYS


class TestBoundaryCoverage:
    """Exact MIN_COVERAGE_DAYS boundary."""

    def test_exactly_min_coverage_is_sufficient(self):
        # Release at Aug28: before = Aug21..Aug28, clipped to Aug23..Aug28 = 5.0d
        release = datetime(2026, 8, 28, tzinfo=timezone.utc)
        _, _, b_days = clipped_before_window(release, WINDOW_DAYS, DS_START, DS_END)
        _, _, a_days = clipped_after_window(release, WINDOW_DAYS, DS_START, DS_END)
        assert b_days >= MIN_COVERAGE_DAYS, f"Expected >= 5, got {b_days}"
        assert a_days >= MIN_COVERAGE_DAYS

    def test_just_below_min_is_insufficient(self):
        # Release at Aug27: before = Aug20..Aug27, clipped to Aug23..Aug27 = 4.0d
        release = datetime(2026, 8, 27, tzinfo=timezone.utc)
        _, _, b_days = clipped_before_window(release, WINDOW_DAYS, DS_START, DS_END)
        assert b_days < MIN_COVERAGE_DAYS, f"Expected < 5, got {b_days}"


class TestSignalType:
    def test_stable(self):
        assert signal_type(5, 5) == "stable"

    def test_increased(self):
        assert signal_type(3, 7) == "increased"

    def test_decreased(self):
        assert signal_type(7, 3) == "decreased"

    def test_new(self):
        assert signal_type(0, 5) == "new"


class TestChangeRate:
    def test_zero_change(self):
        assert change_rate(5, 5) == 0.0

    def test_increase(self):
        assert change_rate(4, 6) == 0.5

    def test_no_baseline(self):
        assert change_rate(0, 5) is None
