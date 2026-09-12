"""Compute human-AI agreement per field from a labelled audit CSV.

Blind workflow (recommended):
  1. label eval/audit_set_<v>_blind.csv (no AI columns visible)
  2. python -m pipeline.eval_agreement eval/audit_set_<v>_blind.csv \
         --reference eval/audit_set_<v>.csv
     Human labels are joined to the AI predictions by github_issue_number.

Single-file mode still works when one CSV contains both ai_* and human_*
columns:
  python -m pipeline.eval_agreement eval/audit_set_<v>.csv

Only rows with a non-empty human_<field> cell are counted for that field.
Comparison is exact after strip/lower-case normalization; the AI column in
the reference shows the exact enum value to copy.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

from pipeline.audit_set import AUDIT_FIELDS


def _norm(value: Any) -> str:
    return (str(value) if value is not None else "").strip().lower()


def join_blind_with_reference(
    blind_rows: list[dict[str, Any]],
    reference_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Attach ai_* prediction columns to labelled blind rows by
    github_issue_number. Returns (joined_rows, unmatched_numbers)."""
    reference_by_number: dict[int, dict[str, Any]] = {}
    for row in reference_rows:
        number = (row.get("github_issue_number") or "").strip()
        if number.isdigit():
            reference_by_number[int(number)] = row

    joined: list[dict[str, Any]] = []
    unmatched: list[str] = []
    for row in blind_rows:
        number = (row.get("github_issue_number") or "").strip()
        match = (
            reference_by_number.get(int(number)) if number.isdigit() else None
        )
        if match is None:
            unmatched.append(number)
            continue
        merged = dict(row)
        for field in AUDIT_FIELDS:
            merged[f"ai_{field}"] = match.get(f"ai_{field}")
        joined.append(merged)
    return joined, unmatched


def compute_agreement(
    rows: list[dict[str, Any]], fields: list[str] | None = None
) -> dict[str, dict[str, Any]]:
    """Per-field exact-match agreement between human_<field> and ai_<field>."""
    fields = fields or list(AUDIT_FIELDS)
    results: dict[str, dict[str, Any]] = {}
    for field in fields:
        labeled = [
            r
            for r in rows
            if (r.get(f"human_{field}") or "").strip()
        ]
        disagreements = [
            {
                "issue": r.get("github_issue_number"),
                "ai": r.get(f"ai_{field}"),
                "human": r.get(f"human_{field}"),
            }
            for r in labeled
            if _norm(r.get(f"human_{field}")) != _norm(r.get(f"ai_{field}"))
        ]
        results[field] = {
            "labeled": len(labeled),
            "agreements": len(labeled) - len(disagreements),
            "accuracy": (
                round((len(labeled) - len(disagreements)) / len(labeled), 3)
                if labeled
                else None
            ),
            "disagreements": disagreements,
        }
    fully = [
        r
        for r in rows
        if all((r.get(f"human_{f}") or "").strip() for f in fields)
    ]
    if fully:
        matches = sum(
            1
            for r in fully
            if all(
                _norm(r.get(f"human_{f}")) == _norm(r.get(f"ai_{f}"))
                for f in fields
            )
        )
        results["overall_fully_labelled"] = {
            "rows": len(fully),
            "all_fields_match": matches,
            "accuracy": round(matches / len(fully), 3),
        }
    return results


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.eval_agreement",
        description="Human-AI agreement per field from a labelled audit CSV.",
    )
    parser.add_argument("csv_path", help="labelled audit CSV (or blind CSV)")
    parser.add_argument(
        "--reference",
        default=None,
        help="reference CSV holding the ai_* prediction columns; human "
        "labels from csv_path are joined to it by github_issue_number",
    )
    args = parser.parse_args(argv)

    path = Path(args.csv_path)
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        return 1
    rows = read_csv(path)
    if args.reference:
        reference_path = Path(args.reference)
        if not reference_path.exists():
            print(f"file not found: {reference_path}", file=sys.stderr)
            return 1
        reference_rows = read_csv(reference_path)
        rows, unmatched = join_blind_with_reference(rows, reference_rows)
        if unmatched:
            print(
                f"warning: {len(unmatched)} blind rows had no reference "
                f"match: {unmatched}",
                file=sys.stderr,
            )
        print(f"joined {len(rows)} blind rows against {args.reference}")
    results = compute_agreement(rows)

    print(json.dumps(results, indent=2, ensure_ascii=False))
    unlabeled = sum(
        1
        for r in rows
        if not any((r.get(f"human_{f}") or "").strip() for f in AUDIT_FIELDS)
    )
    print(
        f"\n{len(rows)} rows; {unlabeled} not labelled at all yet. "
        f"Fill human_* columns in the blind file (your own judgement) and "
        f"re-run with --reference."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
