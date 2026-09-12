"""Thin PostgREST client for pipeline reads/writes (Prompt 01+).

Uses the Supabase REST endpoint with the service-role key. Server-side only:
never expose these credentials to browser code (docs/ARCHITECTURE.md §9).
Upserts use explicit on_conflict targets so reruns stay idempotent.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv


class SupabaseConfigError(RuntimeError):
    pass


def load_env() -> None:
    """Load .env.local (then .env) from the current working directory."""
    for name in (".env.local", ".env"):
        if os.path.exists(name):
            load_dotenv(name, override=False)


class SupabaseRest:
    def __init__(
        self, url: str, service_role_key: str, timeout: float = 60.0
    ) -> None:
        base = url.rstrip("/")
        if base.endswith("/rest/v1"):
            base = base[: -len("/rest/v1")]
        self._http = httpx.Client(
            base_url=f"{base}/rest/v1",
            headers={
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ):
        """Request with bounded retry on transient transport errors."""
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                return self._http.request(
                    method, url, params=params, json=json, headers=headers
                )
            except httpx.HTTPError as exc:
                last_error = exc
                time.sleep(min(2**attempt, 8))
        raise RuntimeError(
            f"Supabase request failed after retries: {last_error}"
        )

    @classmethod
    def from_env(cls) -> "SupabaseRest":
        load_env()
        url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "").strip()
        if not url or not key:
            raise SupabaseConfigError(
                "Supabase is not configured: set NEXT_PUBLIC_SUPABASE_URL "
                "and SUPABASE_SERVICE_ROLE_KEY in .env.local"
            )
        return cls(url, key)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "SupabaseRest":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def upsert(
        self,
        table: str,
        rows: list[dict[str, Any]],
        *,
        on_conflict: str,
        chunk_size: int = 25,
    ) -> int:
        """Idempotent upsert; conflicts resolved on `on_conflict` columns."""
        if not rows:
            return 0
        written = 0
        for start in range(0, len(rows), chunk_size):
            chunk = rows[start : start + chunk_size]
            resp = self._request(
                "post",
                f"/{table}",
                params={"on_conflict": on_conflict},
                headers={"Prefer": "resolution=merge-duplicates"},
                json=chunk,
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(
                    f"Supabase upsert into {table} failed "
                    f"({resp.status_code}): {resp.text[:300]}"
                )
            written += len(chunk)
        return written

    def insert(self, table: str, row: dict[str, Any]) -> dict[str, Any]:
        """Plain insert (run-ledger rows and other append-only records).
        Returns the inserted row representation."""
        resp = self._request(
            "post",
            f"/{table}",
            json=row,
            headers={"Prefer": "return=representation"},
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"Supabase insert into {table} failed "
                f"({resp.status_code}): {resp.text[:300]}"
            )
        result = resp.json()
        return result[0] if isinstance(result, list) else result

    def delete(self, table: str, filters: dict[str, str]) -> int:
        """Delete rows matching filters; returns the number deleted."""
        resp = self._request("delete", f"/{table}", params=filters)
        if resp.status_code not in (200, 204):
            raise RuntimeError(
                f"Supabase delete on {table} failed "
                f"({resp.status_code}): {resp.text[:300]}"
            )
        return len(resp.json()) if resp.text.strip() else 0

    def update(
        self,
        table: str,
        filters: dict[str, str],
        fields: dict[str, Any],
    ) -> bool:
        """Pure UPDATE (no insert semantics) — used for partial column
        backfills like embeddings, where a merge-duplicates upsert would
        violate NOT NULL constraints on omitted columns."""
        resp = self._request("patch", f"/{table}", params=filters, json=fields)
        if resp.status_code not in (200, 204):
            raise RuntimeError(
                f"Supabase update on {table} failed "
                f"({resp.status_code}): {resp.text[:300]}"
            )
        return True

    def select(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: dict[str, str] | None = None,
        order: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"select": columns}
        if filters:
            params.update(filters)
        if order:
            params["order"] = order
        if limit is not None:
            params["limit"] = limit
        resp = self._request("get", f"/{table}", params=params)
        if resp.status_code != 200:
            raise RuntimeError(
                f"Supabase select from {table} failed "
                f"({resp.status_code}): {resp.text[:300]}"
            )
        return resp.json()

    def select_paged(
        self,
        table: str,
        *,
        columns: str = "*",
        filters: dict[str, str] | None = None,
        order: str | None = None,
        page_size: int = 999,
        max_rows: int = 20000,
    ) -> list[dict[str, Any]]:
        """Full-select with Range-header pagination (Supabase caps single
        requests — often at 1000 rows). Returns every matching row."""
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            params: dict[str, Any] = {"select": columns}
            if filters:
                params.update(filters)
            if order:
                params["order"] = order
            resp = self._request(
                "get",
                f"/{table}",
                params=params,
                headers={"Range": f"{offset}-{offset + page_size - 1}"},
            )
            if resp.status_code not in (200, 206):
                raise RuntimeError(
                    f"Supabase paged select from {table} failed "
                    f"({resp.status_code}): {resp.text[:300]}"
                )
            batch = resp.json()
            rows.extend(batch)
            if len(batch) < page_size or len(rows) >= max_rows:
                return rows
            offset += page_size

    def count(self, table: str, filters: dict[str, str] | None = None) -> int:
        params: dict[str, Any] = {"select": "*"}
        if filters:
            params.update(filters)
        resp = self._request(
            "get",
            f"/{table}",
            params=params,
            headers={"Prefer": "count=exact", "Range": "0-0"},
        )
        if resp.status_code not in (200, 206):
            raise RuntimeError(
                f"Supabase count on {table} failed "
                f"({resp.status_code}): {resp.text[:300]}"
            )
        content_range = resp.headers.get("content-range", "")
        total = content_range.rsplit("/", 1)[-1]
        return int(total) if total.isdigit() else len(resp.json())
