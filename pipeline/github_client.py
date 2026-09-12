"""GitHub REST client for issue ingestion (docs/DATA_PIPELINE.md Stage 1).

Anonymous access works for public repositories; when GITHUB_TOKEN exists it
is sent as a Bearer token for a higher rate limit and is otherwise optional.

Pagination walks issues sorted by created (desc). The research window is a
created_at cutoff applied locally (see `index_below_created_cutoff`):
GitHub's `since` query parameter filters by updated_at and must NOT be used.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Iterator

import httpx

GITHUB_API_BASE = "https://api.github.com"

DEFAULT_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "signal-product-ops/0.1 (issue ingestion pipeline)",
}


class GitHubError(RuntimeError):
    """Raised for non-retryable or exhausted GitHub API failures."""


class GitHubClient:
    def __init__(
        self,
        token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        headers = dict(DEFAULT_HEADERS)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._max_retries = max_retries
        self._http = httpx.Client(
            base_url=GITHUB_API_BASE, headers=headers, timeout=timeout
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _get(
        self, url: str, params: dict[str, Any] | None = None
    ) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                resp = self._http.get(url, params=params)
            except httpx.HTTPError as exc:
                last_error = exc
            else:
                if (
                    resp.status_code == 403
                    and resp.headers.get("x-ratelimit-remaining") == "0"
                ):
                    raise GitHubError(
                        "GitHub rate limit exceeded. Set GITHUB_TOKEN in "
                        ".env.local (no scopes needed) for a higher limit."
                    )
                if resp.is_success:
                    return resp
                last_error = GitHubError(
                    f"GitHub API {resp.status_code}: {resp.text[:300]}"
                )
                if resp.status_code < 500:
                    raise last_error  # 4xx (404, 422, ...) is not retryable
            time.sleep(min(2**attempt, 8))
        raise GitHubError(
            f"GitHub API request failed after {self._max_retries} attempts: "
            f"{last_error}"
        )

    def iter_issue_pages(
        self,
        repo: str,
        *,
        state: str = "all",
        per_page: int = 100,
    ) -> Iterator[list[dict[str, Any]]]:
        """Yield pages of issues sorted by created_at desc (PRs included).

        Follows the response Link header (rel="next") for cursor-based
        pagination — large repositories (e.g. openai/codex) reject plain
        page-number pagination with 422.
        """
        url: str | None = f"/repos/{repo}/issues"
        params: dict[str, Any] | None = {
            "state": state,
            "sort": "created",
            "direction": "desc",
            "per_page": per_page,
        }
        while url:
            resp = self._get(url, params=params)
            items = resp.json()
            if not isinstance(items, list):
                raise GitHubError(
                    f"Unexpected GitHub API response: {str(items)[:300]}"
                )
            if not items:
                return
            yield items
            url = resp.links.get("next", {}).get("url")
            params = None  # cursor URLs already carry their query string


def is_pull_request(item: dict[str, Any]) -> bool:
    """The issues endpoint also returns PRs; those carry a pull_request key."""
    return "pull_request" in item


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_cutoff(since: str) -> datetime:
    try:
        return datetime.strptime(since, "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        pass
    parsed = _parse_timestamp(since)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def index_below_created_cutoff(
    items: list[dict[str, Any]], since: str | None
) -> int | None:
    """First index whose created_at < since, for items sorted created desc.

    Inclusive on the cutoff date: items created exactly at cutoff midnight
    UTC stay. Returns None when every item is within the window.
    """
    if not since:
        return None
    cutoff = _parse_cutoff(since)
    for idx, item in enumerate(items):
        if _parse_timestamp(item["created_at"]) < cutoff:
            return idx
    return None
