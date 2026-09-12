"""Tests for the deterministic Opportunities core (Prompt 04)."""

import pytest

from pipeline.opportunities import (
    clip_norm,
    emerging_eligible,
    opportunity_eligibility,
    p95,
    priority_breakdown,
    signal_score,
    status_for,
)


def row(state, *, current=10, prev=5, growth=1.0, share_pp=1.0,
        abs_delta=5, current_share=0.02, severity=0.75):
    return {
        "trend_state": state,
        "current_period_count": current,
        "previous_period_count": prev,
        "growth_rate": growth,
        "share_delta_pp": share_pp,
        "absolute_delta": abs_delta,
        "current_share": current_share,
        "avg_severity_score": severity,
    }


class TestP95AndClip:
    def test_p95_basic(self):
        assert p95([1.0] * 20) == 1.0
        assert p95(list(range(1, 21))) == 20

    def test_p95_empty(self):
        assert p95([]) == 0.0

    def test_clip_norm_negative_and_cap(self):
        assert clip_norm(-5, 10) == 0.0
        assert clip_norm(50, 10) == 1.0
        assert clip_norm(5, 10) == 0.5
        assert clip_norm(None, 10) == 0.0
        assert clip_norm(5, 0) == 0.0


class TestEmergingEligibility:
    def test_normal_growth_requires_all_three(self):
        assert emerging_eligible("normal_growth", row("normal_growth")) is True
        assert (
            emerging_eligible(
                "normal_growth", row("normal_growth", share_pp=-1)
            )
            is False
        )
        assert (
            emerging_eligible("normal_growth", row("normal_growth", growth=0.3))
            is False
        )
        assert (
            emerging_eligible("normal_growth", row("normal_growth", current=4))
            is False
        )

    def test_low_base_requires_share_lift(self):
        assert emerging_eligible("low_base_acceleration", row("low_base_acceleration", prev=1)) is True
        assert (
            emerging_eligible(
                "low_base_acceleration", row("low_base_acceleration", prev=1, share_pp=0)
            )
            is False
        )

    def test_new_signal_only_volume(self):
        assert emerging_eligible("new_signal", row("new_signal", prev=0, current=6)) is True
        assert emerging_eligible("new_signal", row("new_signal", prev=0, current=4)) is False


class TestSignalScore:
    def test_normal_growth_formula(self):
        comps = {"share_lift_pp": 1.0, "abs_delta": 10.0, "growth_capped": 1.0,
                 "current_share": 0.02, "current_count": 10.0, "severity": 0.8}
        caps = {"share_lift_pp": 2.0, "abs_delta": 20.0, "growth_capped": 2.0,
                "current_share": 0.05, "current_count": 20.0, "severity": 1.0}
        expected = round(
            0.35 * (1.0 / 2.0) + 0.30 * (10.0 / 20.0) + 0.20 * (1.0 / 2.0)
            + 0.15 * 0.8,
            4,
        )
        assert signal_score("normal_growth", comps, {"normal_growth": caps}) == expected

    def test_low_base_excludes_growth(self):
        comps = {"share_lift_pp": 1.0, "abs_delta": 10.0,
                 "current_share": 0.02, "current_count": 10.0, "severity": 0.8,
                 "growth_capped": 99.0}
        caps = {"share_lift_pp": 1.0, "abs_delta": 10.0,
                "current_share": 0.02, "current_count": 10.0, "severity": 1.0,
                "growth_capped": 99.0}
        expected = round(0.40 * 1.0 + 0.35 * 1.0 + 0.25 * 0.8, 4)
        assert signal_score("low_base_acceleration", comps, {"low_base_acceleration": caps}) == expected

    def test_new_signal_excludes_growth(self):
        comps = {"share_lift_pp": 0.0, "abs_delta": 0.0, "growth_capped": 0.0,
                 "current_share": 0.025, "current_count": 12.0, "severity": 0.9}
        caps = {"share_lift_pp": 1.0, "abs_delta": 1.0, "growth_capped": 1.0,
                "current_share": 0.05, "current_count": 20.0, "severity": 1.0}
        expected = round(0.45 * (0.025 / 0.05) + 0.35 * (12.0 / 20.0) + 0.20 * 0.9, 4)
        assert signal_score("new_signal", comps, {"new_signal": caps}) == expected


class TestOpportunityGate:
    def test_standard(self):
        eligible, rule = opportunity_eligibility(10, 8, 0)
        assert eligible and "standard" in rule

    def test_rejects_tiny_without_critical(self):
        eligible, _ = opportunity_eligibility(3, 8, 0)
        assert eligible is False

    def test_critical_exception(self):
        eligible, rule = opportunity_eligibility(3, 8, 2)
        assert eligible and "critical_exception" in rule

    def test_rejects_low_current(self):
        eligible, _ = opportunity_eligibility(20, 2, 5)
        assert eligible is False


class TestPriorityAndStatus:
    def test_engagement_renormalized_when_unavailable(self):
        result = priority_breakdown(
            frequency_count=10, severity_score=0.8, signal_score=0.5,
            engagement_total=0, freq_cap=20, engagement_cap=10,
            engagement_available=False,
        )
        assert result["engagement_available"] is False
        assert "engagement" not in result["components"]
        assert abs(sum(result["weights"].values()) - 1.0) < 1e-6

    def test_engagement_included_when_available(self):
        result = priority_breakdown(
            frequency_count=20, severity_score=1.0, signal_score=1.0,
            engagement_total=50, freq_cap=20, engagement_cap=50,
            engagement_available=True,
        )
        assert result["components"]["engagement"] == 1.0
        assert result["priority"] == 1.0

    def test_status_mapping_deterministic(self):
        assert status_for(0.7, 10, 0, False) == "investigate_now"
        assert status_for(0.5, 10, 0, False) == "validate"
        assert status_for(0.35, 10, 0, False) == "monitor"
        assert status_for(0.1, 10, 0, False) == "low_priority"

    def test_critical_exception_capped_at_validate(self):
        assert status_for(0.9, 3, 2, True) == "validate"
        assert status_for(0.5, 3, 2, True) == "validate"
        assert status_for(0.35, 3, 2, True) == "monitor"
