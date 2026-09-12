"""Deterministic normalization must outrank LLM inference (platform/surface)."""

from pipeline.normalize import (
    apply_deterministic_overrides,
    platform_from_labels,
    platform_from_parsed,
    surface_from_labels,
)

WINDOWS_PARSED = "Microsoft Windows NT 10.0.26200.0 x64"  # real #43064 value


class TestPlatformFromParsed:
    def test_windows_nt_string(self):
        assert platform_from_parsed(WINDOWS_PARSED) == "Windows"

    def test_common_platform_strings(self):
        assert platform_from_parsed("macOS 15.5 (Arm)") == "macOS"
        assert platform_from_parsed("Ubuntu 24.04 LTS") == "Linux"
        assert platform_from_parsed("Android 15; Pixel 9") == "Android"
        assert platform_from_parsed("iPhone 15 Pro, iOS 18.1") == "iOS"

    def test_unparseable_returns_none(self):
        assert platform_from_parsed("a very unusual machine") is None
        assert platform_from_parsed(None) is None
        assert platform_from_parsed("") is None


class TestFromLabels:
    def test_platform_label_token(self):
        assert platform_from_labels([{"name": "windows-os"}]) == "Windows"
        assert platform_from_labels([{"name": "bug"}, {"name": "macos-os"}]) == "macOS"
        assert platform_from_labels([{"name": "linux-os"}]) == "Linux"
        assert platform_from_labels([{"name": "app"}]) is None

    def test_surface_labels(self):
        assert surface_from_labels([{"name": "bug"}, {"name": "app"}]) == "Codex App"
        assert surface_from_labels([{"name": "cli"}]) == "CLI"
        assert surface_from_labels([{"name": "ide-extension"}]) == "IDE Extension"
        assert surface_from_labels([{"name": "enhancement"}]) is None


class TestApplyDeterministicOverrides:
    def test_issue_43064_regression_windows_app(self):
        """LLM said Unknown; parsed metadata + labels must win."""
        issue = {
            "parsed_platform": WINDOWS_PARSED,
            "github_labels": [{"name": "bug"}, {"name": "windows-os"}, {"name": "app"}],
        }
        output = {"platform": "Unknown", "surface": "Unknown", "severity": "critical"}
        final = apply_deterministic_overrides(output, issue)
        assert final["platform"] == "Windows"
        assert final["surface"] == "Codex App"
        assert final["severity"] == "critical"  # untouched field

    def test_deterministic_beats_contradicting_llm(self):
        issue = {"parsed_platform": WINDOWS_PARSED, "github_labels": []}
        output = {"platform": "macOS", "surface": "CLI"}
        final = apply_deterministic_overrides(output, issue)
        assert final["platform"] == "Windows"
        assert final["surface"] == "CLI"  # no deterministic surface → LLM stands

    def test_llm_value_stands_without_deterministic_source(self):
        issue = {"parsed_platform": None, "github_labels": [{"name": "bug"}]}
        output = {"platform": "macOS", "surface": "Unknown"}
        final = apply_deterministic_overrides(output, issue)
        assert final["platform"] == "macOS"
        assert final["surface"] == "Unknown"

    def test_original_output_not_mutated(self):
        issue = {"parsed_platform": WINDOWS_PARSED, "github_labels": []}
        output = {"platform": "Unknown"}
        apply_deterministic_overrides(output, issue)
        assert output["platform"] == "Unknown"
