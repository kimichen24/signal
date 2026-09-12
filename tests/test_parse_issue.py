"""Parser + cleaner tests using realistic Codex issue-template fixtures."""

from pipeline.clean_issue import build_body_clean, parse_issue_body

BUG_TEMPLATE = """### What version of the Codex App are you using (From "About Codex" dialog)?

Codex 0.5.42

### What subscription do you have?

Plus

### What platform is your computer?

Microsoft Windows NT 10.0.26200.0 x64

### What issue are you seeing?

I'm unable to open Codex on my PC. I tried uninstalling and reinstalling the
app, restarting multiple times, and switching networks.

### What steps can reproduce the bug?

1. Launch the Codex app
2. It shows "no active thread" and never loads

### What is the expected behavior?

The app should open and let me chat.

### Additional information

_No response_
"""

FEATURE_TEMPLATE = """### What variant of Codex are you using?

Codex desktop app on macOS

### What feature would you like to see?

## Problem

I often queue several tasks in the same Codex conversation and return after
they have finished. Earlier task results can be buried above the latest one.

## Requested behavior

- A per-thread list of unread final turn results
- A "Jump to first unread result" action
"""


def _fields(body: str) -> dict[str, str | None]:
    return parse_issue_body(body)


class TestParseBugTemplate:
    def test_extracts_all_sections(self):
        fields = _fields(BUG_TEMPLATE)
        assert fields["parsed_version"] == "Codex 0.5.42"
        assert fields["parsed_subscription"] == "Plus"
        assert fields["parsed_platform"] == "Microsoft Windows NT 10.0.26200.0 x64"
        assert fields["parsed_actual"].startswith("I'm unable to open Codex")
        assert "no active thread" in fields["parsed_steps"]
        assert fields["parsed_expected"] == "The app should open and let me chat."
        assert fields["parsed_additional_info"] is None  # _No response_

    def test_matches_curly_quote_heading_variant(self):
        curly = BUG_TEMPLATE.replace(
            '(From "About Codex" dialog)', "(From \u201cAbout Codex\u201d dialog)"
        )
        assert _fields(curly)["parsed_version"] == "Codex 0.5.42"


class TestParseFeatureTemplate:
    def test_variant_maps_to_version_and_body_to_actual(self):
        fields = _fields(FEATURE_TEMPLATE)
        assert fields["parsed_version"] == "Codex desktop app on macOS"
        assert "queue several tasks" in fields["parsed_actual"]
        assert fields["parsed_steps"] is None
        assert fields["parsed_expected"] is None


class TestParseEdgeCases:
    def test_plain_body_without_template(self):
        fields = _fields("Random text\nwith no headings at all.")
        assert set(fields) == {
            "parsed_version",
            "parsed_subscription",
            "parsed_platform",
            "parsed_actual",
            "parsed_steps",
            "parsed_expected",
            "parsed_additional_info",
        }
        assert all(value is None for value in fields.values())

    def test_none_body(self):
        assert all(v is None for v in _fields(None).values())

    def test_na_values_become_none(self):
        body = "### What platform is your computer?\n\nN/A\n"
        assert _fields(body)["parsed_platform"] is None


class TestBuildBodyClean:
    def test_short_code_block_preserved(self):
        body = "Before\n```bash\nnpm run dev\nnpm run build\n```\nAfter"
        clean = build_body_clean(body)
        assert "npm run dev" in clean
        assert "code block removed" not in clean

    def test_long_code_block_collapsed(self):
        code = "\n".join(f"error line {i}" for i in range(60))
        body = f"Crash log:\n```\n{code}\n```"
        clean = build_body_clean(body)
        assert "[code block removed: 60 lines]" in clean
        assert "error line 59" not in clean

    def test_repeated_lines_collapsed(self):
        body = "start\n" + ("Connection refused\n" * 10) + "end"
        clean = build_body_clean(body)
        assert clean.count("Connection refused") == 1
        assert "[repeated 10 times]" in clean

    def test_total_length_cap(self):
        body = "x" * 20000
        clean = build_body_clean(body)
        assert len(clean) <= 8100
        assert clean.endswith("[truncated]")

    def test_none_and_empty(self):
        assert build_body_clean(None) is None
        assert build_body_clean("") is None
