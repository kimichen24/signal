"""Tests for the trend engine: sufficiency guard, growth, thresholds."""

from datetime import datetime, timedelta, timezone

from pipeline.compute_trends import (
    INSUFFICIENT_HISTORY,
    avg_severity_score,
    emerging_score,
    growth_rate,
    history_sufficiency,
    in_period,
    is_emerging,
    period_bounds,
)

NOW = datetime(2026, 9, 6, 15, 0, tzinfo=timezone.utc)


class TestPeriodBounds:
    def test_complete_days_anchored_to_utc_midnight(self):
        current_start, current_end, previous_start = period_bounds(NOW, 7)
        assert current_end == datetime(2026, 9, 6, tzinfo=timezone.utc)
        assert current_start == datetime(2026, 8, 30, tzinfo=timezone.utc)
        assert previous_start == datetime(2026, 8, 23, tzinfo=timezone.utc)


class TestInPeriod:
    def test_half_open_interval(self):
        start = datetime(2026, 8, 30, tzinfo=timezone.utc)
        end = datetime(2026, 9, 6, tzinfo=timezone.utc)
        assert in_period("2026-08-30T00:00:00Z", start, end) is True
        assert in_period("2026-09-05T23:59:59Z", start, end) is True
        assert in_period("2026-09-06T00:00:00Z", start, end) is False


class TestHistorySufficiency:
    def test_fails_when_range_does_not_cover_previous_period(self):
        ok, reason = history_sufficiency(
            min_created_at="2026-09-01T00:00:00Z",
            current_count=50,
            previous_count=50,
            current_start=datetime(2026, 8, 30, tzinfo=timezone.utc),
            previous_start=datetime(2026, 8, 23, tzinfo=timezone.utc),
            min_period_volume=10,
        )
        assert ok is False
        assert INSUFFICIENT_HISTORY != "ok"
        assert "does not cover" in reason

    def test_fails_when_previous_volume_too_low(self):
        ok, reason = history_sufficiency(
            min_created_at="2026-08-01T00:00:00Z",
            current_count=50,
            previous_count=3,
            current_start=datetime(2026, 8, 30, tzinfo=timezone.utc),
            previous_start=datetime(2026, 8, 23, tzinfo=timezone.utc),
            min_period_volume=10,
        )
        assert ok is False and "previous period" in reason

    def test_fails_when_current_volume_too_low(self):
        ok, _ = history_sufficiency(
            min_created_at="2026-08-01T00:00:00Z",
            current_count=2,
            previous_count=50,
            current_start=datetime(2026, 8, 30, tzinfo=timezone.utc),
            previous_start=datetime(2026, 8, 23, tzinfo=timezone.utc),
            min_period_volume=10,
        )
        assert ok is False

    def test_passes_with_sufficient_history(self):
        ok, reason = history_sufficiency(
            min_created_at="2026-08-01T00:00:00Z",
            current_count=50,
            previous_count=20,
            current_start=datetime(2026, 8, 30, tzinfo=timezone.utc),
            previous_start=datetime(2026, 8, 23, tzinfo=timezone.utc),
            min_period_volume=10,
        )
        assert ok is True and reason == "sufficient"


class TestGrowthRate:
    def test_standard_growth(self):
        assert growth_rate(15, 10) == 0.5
        assert growth_rate(5, 10) == -0.5

    def test_zero_baseline_is_none_never_infinity(self):
        assert growth_rate(7, 0) is None
        assert growth_rate(0, 0) is None


class TestEmerging:
    def test_requires_minimum_current_volume(self):
        assert is_emerging(4, 3.0, min_volume=5, min_growth=0.5) is False
        assert is_emerging(5, 3.0, min_volume=5, min_growth=0.5) is True

    def test_requires_computed_growth(self):
        # Zero baseline -> no growth -> never "new emerging signal".
        assert is_emerging(50, None, min_volume=5, min_growth=0.5) is False

    def test_requires_growth_above_threshold(self):
        assert is_emerging(10, 0.4, min_volume=5, min_growth=0.5) is False
        assert is_emerging(10, 0.5, min_volume=5, min_growth=0.5) is True


class TestEmergingScore:
    def test_none_without_growth(self):
        assert emerging_score(10, None, 0.75) is None

    def test_deterministic_blend(self):
        assert emerging_score(20, 3.0, 1.0) == 1.0  # all parts maxed
        assert emerging_score(10, 0.5, 0.5) == round(
            0.4 * (0.5 / 3.0) + 0.3 * 0.5 + 0.3 * 0.5, 3
        )


class TestSeverityScore:
    def test_average(self):
        assert avg_severity_score(["high", "medium", "high"]) == round(
            (0.75 + 0.5 + 0.75) / 3, 3
        )


class TestTrendState:
    def test_baseline_classification(self):
        from pipeline.compute_trends import trend_state

        assert trend_state(0) == "new_signal"
        assert trend_state(1) == "low_base_acceleration"
        assert trend_state(2) == "low_base_acceleration"
        assert trend_state(3) == "normal_growth"
        assert trend_state(50) == "normal_growth"


class TestTrendMetrics:
    def test_shares_use_in_scope_denominators(self):
        from pipeline.compute_trends import trend_metrics

        m = trend_metrics(20, 10, 524, 476, min_volume=5, min_growth=0.5)
        assert m["previous_share"] == round(10 / 476, 6) or abs(
            m["previous_share"] - 10 / 476
        ) < 1e-9
        assert abs(m["current_share"] - 20 / 524) < 1e-9
        # share delta in percentage points
        expected_pp = round((20 / 524 - 10 / 476) * 100, 2)
        assert m["share_delta_pp"] == expected_pp
        assert m["absolute_delta"] == 10

    def test_low_base_state_preserved_with_counts(self):
        from pipeline.compute_trends import trend_metrics

        m = trend_metrics(8, 1, 524, 476, min_volume=5, min_growth=0.5)
        assert m["trend_state"] == "low_base_acceleration"
        assert m["growth_rate"] == 7.0  # raw growth preserved, not hidden
        assert m["is_emerging"] is True

    def test_new_signal_has_null_growth_but_can_surface(self):
        from pipeline.compute_trends import trend_metrics

        m = trend_metrics(6, 0, 524, 476, min_volume=5, min_growth=0.5)
        assert m["trend_state"] == "new_signal"
        assert m["growth_rate"] is None  # growth never computed
        assert m["emerging_score"] is None  # score needs growth math
        assert m["absolute_delta"] == 6
        # Eligibility (frozen): current >= 5 — surfaced, without % claims.
        assert m["is_emerging"] is True

        low = trend_metrics(3, 0, 524, 476, min_volume=5, min_growth=0.5)
        assert low["is_emerging"] is False  # below volume threshold
