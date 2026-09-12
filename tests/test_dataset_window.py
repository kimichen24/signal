"""Tests for the reproducible dataset window (start <= created < snapshot)."""

from datetime import datetime, timezone

import pytest

from pipeline.dataset_window import DatasetWindow, WindowError, parse_bound


class TestParseBound:
    def test_date_only_becomes_utc_midnight(self):
        assert parse_bound("2026-09-05", name="x") == datetime(
            2026, 9, 5, tzinfo=timezone.utc
        )

    def test_iso_datetime_with_z(self):
        assert parse_bound("2026-09-05T10:30:00Z", name="x") == datetime(
            2026, 9, 5, 10, 30, tzinfo=timezone.utc
        )

    def test_rejects_garbage(self):
        with pytest.raises(WindowError):
            parse_bound("not-a-date", name="--snapshot-at")


class TestDatasetWindow:
    def test_contains_half_open_interval(self):
        window = DatasetWindow.from_args("2026-09-05", "2026-09-06T12:00:00Z")
        assert window.contains("2026-09-05T00:00:00Z") is True  # inclusive
        assert window.contains("2026-09-06T11:59:59Z") is True
        assert window.contains("2026-09-06T12:00:00Z") is False  # exclusive
        assert window.contains("2026-09-04T23:59:59Z") is False

    def test_default_snapshot_is_now(self):
        window = DatasetWindow.from_args(None, None)
        assert window.start_date is None
        assert window.snapshot_at.tzinfo is timezone.utc

    def test_start_must_precede_snapshot(self):
        with pytest.raises(WindowError):
            DatasetWindow.from_args("2026-09-06", "2026-09-05")

    def test_postgrest_filters_single_upper_bound(self):
        window = DatasetWindow.from_args(None, "2026-09-06T12:00:00Z")
        assert window.postgrest_filters() == {
            "github_created_at": "lt.2026-09-06T12:00:00Z"
        }

    def test_postgrest_filters_with_floor(self):
        window = DatasetWindow.from_args("2026-09-05", "2026-09-06T12:00:00Z")
        filters = window.postgrest_filters()
        assert "and" in filters
        assert filters["and"].startswith("(")
        assert "github_created_at.gte.2026-09-05T00:00:00Z" in filters["and"]
        assert "github_created_at.lt.2026-09-06T12:00:00Z" in filters["and"]

    def test_describe_is_human_readable(self):
        window = DatasetWindow.from_args("2026-09-05", "2026-09-06")
        assert "2026-09-05T00:00:00Z" in window.describe()
        assert "2026-09-06T00:00:00Z" in window.describe()
