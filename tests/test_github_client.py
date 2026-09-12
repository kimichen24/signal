"""Tests for GitHub fetch helpers: PR detection and created_at cutoff."""

from argparse import Namespace

from pipeline.dataset_window import DatasetWindow
from pipeline.github_client import (
    index_below_created_cutoff,
    is_pull_request,
)
from pipeline.ingest_github import fetch_issues


def make_issue(number: int, created_at: str) -> dict:
    return {"number": number, "created_at": created_at}


class StubClient:  # no HTTP client needed
    """Skip the HTTP client; replay canned pages."""

    def __init__(self, pages):
        self.pages = list(pages)

    def iter_issue_pages(self, repo, *, state="all", per_page=100):
        yield from self.pages


class TestFetchIssuesPagination:
    def _window(self):
        return DatasetWindow.from_args("2026-08-23", "2026-09-06T00:00:00Z")

    def test_pages_of_too_new_items_do_not_stop_pagination(self):
        # Regression: a first page entirely above the snapshot ceiling must
        # keep paginating, not break.
        too_new = [make_issue(n, "2026-09-06T08:00:00Z") for n in range(1, 101)]
        in_window = [
            make_issue(1000, "2026-09-05T10:00:00Z"),
            make_issue(1001, "2026-08-25T10:00:00Z"),
        ]
        below_floor = [make_issue(2000, "2026-08-10T00:00:00Z")]
        client = StubClient([too_new, in_window, below_floor])
        args = Namespace(
            repo="openai/codex", limit=100, state="all", start_date="2026-08-23",
            snapshot_at="2026-09-06T00:00:00Z",
        )
        issues, seen, prs, collected = fetch_issues(
            client, args, self._window()
        )
        assert [i["number"] for i in issues] == [1000, 1001]
        assert collected == 2
        assert seen == 103  # everything examined, incl. out-of-window

    def test_stops_at_floor(self):
        page = [
            make_issue(1, "2026-09-01T00:00:00Z"),
            make_issue(2, "2026-08-20T00:00:00Z"),  # below floor on this page
        ]
        client = StubClient([page, [make_issue(999, "2026-08-01T00:00:00Z")]])
        args = Namespace(
            repo="openai/codex", limit=100, state="all", start_date="2026-08-23",
            snapshot_at="2026-09-06T00:00:00Z",
        )
        issues, seen, prs, collected = fetch_issues(
            client, args, self._window()
        )
        assert [i["number"] for i in issues] == [1]
        assert seen == 2  # second page never fetched


class TestIsPullRequest:
    def test_pr_detected_by_pull_request_key(self):
        assert is_pull_request({"pull_request": {"url": "..."}}) is True

    def test_issue_without_key(self):
        assert is_pull_request({"number": 1}) is False


class TestIndexBelowCreatedCutoff:
    def test_returns_first_item_older_than_cutoff(self):
        items = [
            make_issue(3, "2026-08-10T12:00:00Z"),
            make_issue(2, "2026-08-05T00:00:00Z"),
        ]
        assert index_below_created_cutoff(items, "2026-08-07") == 1

    def test_none_when_no_cutoff(self):
        items = [make_issue(1, "2026-01-01T00:00:00Z")]
        assert index_below_created_cutoff(items, None) is None

    def test_none_when_all_items_within_window(self):
        items = [
            make_issue(2, "2026-08-09T00:00:00Z"),
            make_issue(1, "2026-08-08T00:00:00Z"),
        ]
        assert index_below_created_cutoff(items, "2026-08-07") is None

    def test_cutoff_date_is_inclusive(self):
        # Exactly at cutoff midnight UTC counts as inside the window.
        items = [make_issue(1, "2026-08-07T00:00:00Z")]
        assert index_below_created_cutoff(items, "2026-08-07") is None

    def test_all_items_old_returns_index_zero(self):
        items = [make_issue(1, "2026-01-01T00:00:00Z")]
        assert index_below_created_cutoff(items, "2026-08-07") == 0
