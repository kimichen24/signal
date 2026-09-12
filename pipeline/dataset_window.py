"""Reproducible dataset windows (docs/DATA_PIPELINE.md).

A dataset slice is fixed by:

    start_date <= github_created_at < snapshot_at   (UTC)

`snapshot_at` defaults to the run time and is recorded in `analysis_runs`
together with `start_date`, so metrics stay recomputable against exactly the
same data instead of an ever-moving live window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


class WindowError(ValueError):
    pass


def parse_bound(value: str | None, *, name: str) -> datetime | None:
    """Parse YYYY-MM-DD (UTC midnight) or an ISO datetime. Naive -> UTC."""
    if value is None or value == "":
        return None
    text = value.strip()
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError as exc:
            raise WindowError(
                f"{name} must be YYYY-MM-DD or ISO 8601 datetime, got {value!r}"
            ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _parse_created(created_at: str) -> datetime:
    return datetime.fromisoformat(created_at.replace("Z", "+00:00"))


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class DatasetWindow:
    start_date: datetime | None
    snapshot_at: datetime

    @classmethod
    def from_args(
        cls, start_date: str | None, snapshot_at: str | None
    ) -> "DatasetWindow":
        start = parse_bound(start_date, name="--start-date")
        snap = parse_bound(snapshot_at, name="--snapshot-at")
        if snap is None:
            snap = datetime.now(timezone.utc)
        if start is not None and start >= snap:
            raise WindowError("--start-date must be earlier than --snapshot-at")
        return cls(start_date=start, snapshot_at=snap)

    def contains(self, created_at: str) -> bool:
        timestamp = _parse_created(created_at)
        if self.start_date is not None and timestamp < self.start_date:
            return False
        return timestamp < self.snapshot_at

    def below_floor(self, created_at: str) -> bool:
        """Whether an item is older than the window floor. Pagination may
        stop only on this condition — items above the snapshot ceiling
        (too new) must keep paging downward."""
        if self.start_date is None:
            return False
        return _parse_created(created_at) < self.start_date

    def postgrest_filters(
        self, column: str = "github_created_at"
    ) -> dict[str, str]:
        """Filters for SupabaseRest.select on a timestamptz column."""
        upper = f"{column}.lt.{_iso(self.snapshot_at)}"
        if self.start_date is None:
            # Top-level form: ?column=lt.value
            return {column: upper.removeprefix(f"{column}.")}
        # Inside and=(...), each clause uses the full column.op.value form.
        return {"and": f"({upper},{column}.gte.{_iso(self.start_date)})"}

    def describe(self) -> str:
        start = _iso(self.start_date) if self.start_date else "(no lower bound)"
        return f"{start} <= github_created_at < {_iso(self.snapshot_at)}"
