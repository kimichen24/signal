"""Ingest real GitHub issues into Supabase (Prompt 01).

Usage:
  python -m pipeline.ingest_github --repo openai/codex --limit 100 \
      [--since 2026-08-07] [--state all] [--dry-run]

- Fetches issues sorted by created desc via the GitHub REST API
  (anonymous, or authenticated when GITHUB_TOKEN exists).
- Dataset window: --start-date/--since (inclusive) <= created_at <
  --snapshot-at (default: now). The floor is applied locally because
  GitHub's `since` parameter filters by updated_at; the snapshot ceiling
  bounds the dataset so reruns reproduce the same slice. The window is
  recorded in analysis_runs.
- Entries carrying a `pull_request` field are counted and never stored.
- Upsert conflicts on github_issue_number, so reruns are idempotent.
- body_raw and source_payload are stored exactly as fetched; cleaning only
  produces body_clean.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from pipeline.clean_issue import build_body_clean, parse_issue_body
from pipeline.dataset_window import DatasetWindow, WindowError
from pipeline.github_client import (
    GitHubClient,
    GitHubError,
    is_pull_request,
)
from pipeline.supabase_client import SupabaseConfigError, SupabaseRest

UNKNOWN_PLATFORM_VALUES = {"", "unknown", "n/a", "na", "none"}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.ingest_github",
        description="Import real GitHub issues into Supabase (issues only).",
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPO", "openai/codex"),
        help="owner/repo to ingest (default: GITHUB_REPO or openai/codex)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="max number of real issues to import (default: 100)",
    )
    parser.add_argument(
        "--start-date",
        "--since",
        dest="start_date",
        default=None,
        help="dataset window lower bound, created_at >= start (YYYY-MM-DD, "
        "inclusive, UTC). Applied locally — GitHub `since` filters by "
        "updated_at and is not used.",
    )
    parser.add_argument(
        "--snapshot-at",
        default=None,
        help="dataset window upper bound, created_at < snapshot "
        "(default: now; recorded in analysis_runs)",
    )
    parser.add_argument(
        "--dataset-id",
        default=None,
        help="register this run under a persistent dataset id (requires "
        "--start-date and --snapshot-at; supabase/migrations/0006)",
    )
    parser.add_argument(
        "--state",
        default="all",
        choices=("all", "open", "closed"),
        help="GitHub issue state filter (default: all — open + closed)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="fetch and prepare rows but do not write to Supabase",
    )
    return parser


def fetch_issues(
    client: GitHubClient,
    args: argparse.Namespace,
    window: DatasetWindow,
) -> tuple[list[dict[str, Any]], int, int, int]:
    """Collect up to --limit real issues inside the dataset window.

    Returns (issues, seen_items, pr_count, collected). `seen_items` counts
    every item examined including those outside the window (above the
    snapshot ceiling / below the floor on the terminating page).
    """
    collected: list[dict[str, Any]] = []
    seen = 0
    pr_count = 0

    for page in client.iter_issue_pages(args.repo, state=args.state):
        for item in page:
            seen += 1
            if not window.contains(item["created_at"]):
                continue  # outside [start, snapshot) — examined, not stored
            if is_pull_request(item):
                pr_count += 1
                continue
            collected.append(item)
            if len(collected) >= args.limit:
                return collected[: args.limit], seen, pr_count, len(collected)
        # Items sorted created desc: stop only once the page's oldest entry
        # is OLDER than the window floor. Pages of too-new items (above the
        # snapshot ceiling) must keep paginating downward.
        if page and window.below_floor(page[-1]["created_at"]):
            break
    return collected, seen, pr_count, len(collected)


def build_row(issue: dict[str, Any]) -> dict[str, Any]:
    body = issue.get("body")
    return {
        "github_issue_number": issue["number"],
        "title": issue.get("title") or "",
        "body_raw": body,
        "body_clean": build_body_clean(body),
        "github_url": issue.get("html_url") or "",
        "state": issue.get("state"),
        "github_labels": [
            {"name": label.get("name")}
            for label in issue.get("labels", [])
            if isinstance(label, dict)
        ],
        "comments_count": int(issue.get("comments") or 0),
        "reactions_count": int(
            (issue.get("reactions") or {}).get("total_count") or 0
        ),
        "github_created_at": issue["created_at"],
        "github_updated_at": issue.get("updated_at"),
        "github_closed_at": issue.get("closed_at"),
        "source_payload": issue,
        **parse_issue_body(body),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    created = [row["github_created_at"] for row in rows]
    platform_missing = sum(
        1
        for row in rows
        if (row["parsed_platform"] or "").strip().lower()
        in UNKNOWN_PLATFORM_VALUES
    )
    return {
        "imported": len(rows),
        "open": sum(1 for row in rows if row["state"] == "open"),
        "closed": sum(1 for row in rows if row["state"] == "closed"),
        "earliest_created_at": min(created) if created else None,
        "latest_created_at": max(created) if created else None,
        "parsed_platform_missing": platform_missing,
    }


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.limit < 1:
        print("--limit must be >= 1", file=sys.stderr)
        return 1
    try:
        window = DatasetWindow.from_args(args.start_date, args.snapshot_at)
    except WindowError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.dataset_id and not (args.start_date and args.snapshot_at):
        print(
            "--dataset-id requires explicit --start-date and --snapshot-at "
            "so the dataset definition always resolves to the same window",
            file=sys.stderr,
        )
        return 1

    token = os.environ.get("GITHUB_TOKEN", "").strip() or None
    try:
        with GitHubClient(token=token) as client:
            issues, seen, pr_count, fetched = fetch_issues(client, args, window)
    except GitHubError as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1

    rows = [build_row(issue) for issue in issues]
    summary = {
        "repo": args.repo,
        "window": window.describe(),
        "dataset_id": args.dataset_id,
        "items_seen": seen,
        "items_in_window": fetched,
        "pr_filtered": pr_count,
        **summarize(rows),
    }

    if args.dry_run:
        summary["mode"] = "dry-run (nothing written)"
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    try:
        with SupabaseRest.from_env() as supabase:
            written = supabase.upsert(
                "issues", rows, on_conflict="github_issue_number"
            )
            supabase.insert(
                "analysis_runs",
                {
                    "run_type": "ingestion",
                    "repo": args.repo,
                    "start_date": window.start_date.isoformat()
                    if window.start_date
                    else None,
                    "snapshot_at": window.snapshot_at.isoformat(),
                    "item_count": written,
                    "params": {
                        "state": args.state,
                        "limit": args.limit,
                        "dataset_id": args.dataset_id,
                        "items_seen": seen,
                        "items_in_window": fetched,
                        "pr_filtered": pr_count,
                    },
                },
            )
            if args.dataset_id:
                try:
                    window_count = supabase.count(
                        "issues",
                        filters=window.postgrest_filters("github_created_at"),
                    )
                    supabase.upsert(
                        "datasets",
                        [
                            {
                                "dataset_id": args.dataset_id,
                                "repository": args.repo,
                                "start_at": window.start_date.isoformat(),
                                "snapshot_at": window.snapshot_at.isoformat(),
                                "raw_issue_count": window_count,
                            }
                        ],
                        on_conflict="dataset_id",
                    )
                    summary["dataset_registered"] = {
                        "dataset_id": args.dataset_id,
                        "raw_issue_count": window_count,
                    }
                except RuntimeError as exc:
                    summary["dataset_registered"] = (
                        f"failed (non-fatal): {exc}"
                    )
                    print(
                        f"warning: dataset registration failed — apply "
                        f"supabase/migrations/0006_datasets.sql "
                        f"({exc})",
                        file=sys.stderr,
                    )
    except (SupabaseConfigError, RuntimeError) as exc:
        print(f"Ingestion failed: {exc}", file=sys.stderr)
        return 1

    summary["written"] = written
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
