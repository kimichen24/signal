"""Seed real public Codex release events (Prompt 04).

Fetches stable (non-prerelease) releases from the openai/codex GitHub
releases API — each with an authoritative source_url — and persists them
idempotently (skip if a release with the same name already exists).
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

import httpx

GITHUB_API = "https://api.github.com"


def main(argv: list[str] | None = None) -> int:
    from pipeline.supabase_client import (
        SupabaseConfigError,
        SupabaseRest,
        load_env,
    )

    repo = os.environ.get("GITHUB_REPO", "openai/codex")
    per_page = 60
    try:
        with httpx.Client(
            headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "signal-product-ops/0.1",
            },
            timeout=30.0,
        ) as gh:
            resp = gh.get(
                f"{GITHUB_API}/repos/{repo}/releases",
                params={"per_page": per_page},
            )
            if resp.status_code != 200:
                print(
                    f"GitHub releases fetch failed ({resp.status_code}): "
                    f"{resp.text[:200]}",
                    file=sys.stderr,
                )
                return 1
            releases = resp.json()

        stable = [
            r
            for r in releases
            if not r.get("prerelease") and r.get("published_at")
        ]
        with SupabaseRest.from_env() as supabase:
            existing = {
                r["name"] for r in supabase.select("releases", columns="name")
            }
            inserted = 0
            for r in stable:
                name = r.get("name") or r.get("tag_name")
                if name in existing:
                    continue
                body = (r.get("body") or "")[:500]
                supabase.insert(
                    "releases",
                    {
                        "product": "Codex",
                        "name": name,
                        "release_date": r["published_at"],
                        "source_url": r["html_url"],
                        "description": body,
                    },
                )
                inserted += 1
                print(f"seeded: {name} @ {r['published_at']}")
            total = supabase.count("releases")
            print(json.dumps({"inserted": inserted, "total_releases": total}))
            return 0
    except (SupabaseConfigError, RuntimeError) as exc:
        print(f"Release seeding failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
