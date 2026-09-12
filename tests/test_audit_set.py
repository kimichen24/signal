"""Tests for the audit-set sampling and the agreement calculator."""

import csv

from pipeline.audit_set import (
    AUDIT_FIELDS,
    make_blind,
    make_blind_final,
    select_audit_items,
)
from pipeline.eval_agreement import (
    compute_agreement,
    join_blind_with_reference,
)


def make_row(num, *, needs_review=False, severity="medium",
             confidence=0.9, scope="codex_core"):
    return {
        "issue_id": f"id-{num}",
        "github_issue_number": num,
        "needs_review": needs_review,
        "severity": severity,
        "confidence": confidence,
        "product_scope": scope,
        "title": f"issue {num}",
    }


def make_population() -> list[dict]:
    rows = []
    # 5 needs_review issues (group A)
    for n in (100, 101, 102, 103, 104):
        rows.append(make_row(n, needs_review=True, severity="low",
                             confidence=0.5, scope="out_of_scope"))
    # 10 critical high-confidence candidates (group B pool)
    for n in range(200, 210):
        rows.append(make_row(n, severity="critical", confidence=0.95))
    # 7 out-of-scope high-confidence candidates (group C pool)
    for n in range(300, 307):
        rows.append(make_row(n, confidence=0.85, scope="out_of_scope"))
    # 8 remaining (group D pool)
    for n in range(400, 408):
        rows.append(make_row(n))
    return rows


class TestSelectAuditItems:
    def test_selects_exactly_20_unique_with_expected_groups(self):
        selected, stats = select_audit_items(make_population(), seed=42)
        assert stats["unique_total"] == 20
        numbers = [r["github_issue_number"] for r in selected]
        assert len(numbers) == len(set(numbers)) == 20
        # All 5 needs_review issues are included (group A takes all).
        assert all(n in numbers for n in range(100, 105))

    def test_deterministic_for_fixed_seed(self):
        a, _ = select_audit_items(make_population(), seed=42)
        b, _ = select_audit_items(make_population(), seed=42)
        assert [r["issue_id"] for r in a] == [r["issue_id"] for r in b]

    def test_different_seeds_can_differ(self):
        a, _ = select_audit_items(make_population(), seed=42)
        b, _ = select_audit_items(make_population(), seed=7)
        assert [r["issue_id"] for r in a] != [r["issue_id"] for r in b]

    def test_no_duplicates_across_groups(self):
        selected, stats = select_audit_items(make_population(), seed=42)
        ids = [r["issue_id"] for r in selected]
        assert len(ids) == stats["unique_total"]

    def test_reports_shortfall_when_pool_too_small(self):
        rows = [
            make_row(1, needs_review=True),
            make_row(2, severity="critical", confidence=0.95),
            *[
                make_row(n, confidence=0.9, scope="out_of_scope")
                for n in range(10, 30)
            ],
        ]
        selected, stats = select_audit_items(rows, seed=42)
        # Critical pool has only 1 candidate -> taken in full, logged.
        assert stats["taken"] == {
            "needs_review": 1,
            "critical_high_confidence": 1,
            "out_of_scope_high_confidence": 5,
            "remaining": 5,
        }
        assert stats["unique_total"] == 12
        assert stats["unique_total"] == sum(stats["taken"].values())

    def test_needs_review_rows_are_all_taken_regardless_of_other_groups(self):
        rows = make_population()
        selected, _ = select_audit_items(rows, seed=42)
        nr_ids = {r["issue_id"] for r in rows if r["needs_review"]}
        chosen = {r["issue_id"] for r in selected}
        assert nr_ids <= chosen


class TestMakeBlind:
    def test_strips_ai_columns_and_keeps_labelling_fields(self, tmp_path):
        reference = tmp_path / "ref.csv"
        with reference.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "github_issue_number",
                    "audit_group",
                    "ai_platform",
                    "ai_confidence",
                    "ai_summary",
                    "human_platform",
                    "reviewer_note",
                    "body_clean",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "github_issue_number": "43064",
                    "audit_group": "critical_high_confidence",
                    "ai_platform": "Windows",
                    "ai_confidence": "0.82",
                    "ai_summary": "secret",
                    "human_platform": "",
                    "reviewer_note": "",
                    "body_clean": "material",
                }
            )
        blind_path = tmp_path / "ref_blind.csv"
        count = make_blind(reference, blind_path)
        assert count == 1
        with blind_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
        assert all(
            not column.startswith("ai_") for column in rows[0]
        )
        assert rows[0]["github_issue_number"] == "43064"
        assert rows[0]["audit_group"] == "critical_high_confidence"
        assert rows[0]["human_platform"] == ""
        assert rows[0]["reviewer_note"] == ""
        assert rows[0]["body_clean"] == "material"


class TestMakeBlindFinal:
    @staticmethod
    def _write_reference(tmp_path):
        reference = tmp_path / "ref.csv"
        fieldnames = [
            "github_issue_number",
            "audit_group",
            "ai_platform",
            "ai_summary",
            "human_platform",
            "reviewer_note",
            "title",
        ]
        rows = [
            {
                "github_issue_number": str(number),
                "audit_group": f"group{number % 2}",
                "ai_platform": "Windows",
                "ai_summary": "secret",
                "human_platform": "",
                "reviewer_note": "",
                "title": f"t{number}",
            }
            for number in range(1, 11)
        ]
        with reference.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return reference, rows

    def test_strips_ai_and_group_shuffles_deterministically(self, tmp_path):
        reference, _ = self._write_reference(tmp_path)
        out1 = tmp_path / "final1.csv"
        out2 = tmp_path / "final2.csv"
        assert make_blind_final(reference, out1, seed=42) == 10
        assert make_blind_final(reference, out2, seed=42) == 10
        rows1 = list(
            csv.DictReader(out1.open(encoding="utf-8-sig", newline=""))
        )
        rows2 = list(
            csv.DictReader(out2.open(encoding="utf-8-sig", newline=""))
        )
        assert list(rows1[0].keys()) == [
            "github_issue_number",
            "human_platform",
            "reviewer_note",
            "title",
        ]
        assert [r["github_issue_number"] for r in rows1] == [
            r["github_issue_number"] for r in rows2
        ]
        assert sorted(
            int(r["github_issue_number"]) for r in rows1
        ) == list(range(1, 11))
        assert [int(r["github_issue_number"]) for r in rows1] != list(
            range(1, 11)
        )  # actually shuffled, grouping order not preserved

    def test_join_works_after_shuffle(self, tmp_path):
        reference, source_rows = self._write_reference(tmp_path)
        out = tmp_path / "final.csv"
        make_blind_final(reference, out, seed=42)
        shuffled = list(
            csv.DictReader(out.open(encoding="utf-8-sig", newline=""))
        )
        predictions = [
            {
                "github_issue_number": r["github_issue_number"],
                "ai_platform": "Windows",
            }
            for r in source_rows
        ]
        joined, missing = join_blind_with_reference(shuffled, predictions)
        assert missing == []
        assert len(joined) == 10
        assert all(r["ai_platform"] == "Windows" for r in joined)


class TestJoinBlindWithReference:
    @staticmethod
    def _blind(number: int, **human) -> dict:
        return {
            "github_issue_number": str(number),
            **{f"human_{f}": human.get(f, "") for f in AUDIT_FIELDS},
        }

    @staticmethod
    def _reference(number: int, **ai) -> dict:
        return {
            "github_issue_number": str(number),
            **{f"ai_{f}": ai.get(f, f"a_{f}") for f in AUDIT_FIELDS},
        }

    def test_join_then_agree(self):
        agreed = {f: f"a_{f}" for f in AUDIT_FIELDS}
        blind = [
            self._blind(1, **agreed),
            self._blind(2, **{**agreed, "severity": "wrong"}),
        ]
        reference = [self._reference(1), self._reference(2)]
        joined, missing = join_blind_with_reference(blind, reference)
        assert missing == []
        results = compute_agreement(joined)
        assert results["platform"]["accuracy"] == 1.0
        assert results["severity"]["accuracy"] == 0.5
        assert results["severity"]["disagreements"] == [
            {"issue": "2", "ai": "a_severity", "human": "wrong"}
        ]

    def test_unmatched_numbers_reported(self):
        joined, missing = join_blind_with_reference(
            [self._blind(99)], [self._reference(1)]
        )
        assert joined == []
        assert missing == ["99"]


class TestComputeAgreement:
    def _rows(self):
        base = {
            "github_issue_number": 1,
            **{f"ai_{f}": f"v_{f}" for f in AUDIT_FIELDS},
        }
        row1 = {**base, **{f"human_{f}": f"V_{f} " for f in AUDIT_FIELDS}}
        row2 = {
            **base,
            "github_issue_number": 2,
            **{f"human_{f}": f"v_{f}" for f in AUDIT_FIELDS},
            "human_severity": "different",
        }
        return [row1, row2]

    def test_per_field_accuracy_with_normalization(self):
        results = compute_agreement(self._rows())
        # Row 1 matches case-insensitively with stray space; row 2 disagrees
        # only on severity.
        assert results["platform"]["labeled"] == 2
        assert results["platform"]["accuracy"] == 1.0
        assert results["severity"]["accuracy"] == 0.5
        assert results["severity"]["disagreements"] == [
            {"issue": 2, "ai": "v_severity", "human": "different"}
        ]

    def test_unlabeled_fields_are_excluded(self):
        rows = [{**self._rows()[0], "human_platform": ""}]
        results = compute_agreement(rows)
        assert results["platform"]["labeled"] == 0
        assert results["platform"]["accuracy"] is None

    def test_overall_fully_labelled_section(self):
        results = compute_agreement(self._rows())
        assert results["overall_fully_labelled"]["rows"] == 2
        assert results["overall_fully_labelled"]["all_fields_match"] == 1
        assert results["overall_fully_labelled"]["accuracy"] == 0.5


class TestCsvRoundTrip:
    def test_written_csv_reads_back_with_columns(self, tmp_path):
        from pipeline.audit_set import CSV_COLUMNS, flatten, write_csv

        flat = flatten(
            {
                "issue_id": "id-1",
                "summary": "s",
                "confidence": 0.82,
                "scope_confidence": 0.9,
                "needs_review": True,
                **{f: f"val_{f}" for f in AUDIT_FIELDS},
                "issues": {
                    "github_issue_number": 43064,
                    "title": "Cant open codex",
                    "github_url": "u",
                    "state": "open",
                    "github_created_at": "t",
                    "body_clean": "line1\nline2, with comma",
                    "github_labels": [{"name": "bug"}, {"name": "app"}],
                    "parsed_platform": "Microsoft Windows NT 10.0.26200.0 x64",
                },
            }
        )
        path = tmp_path / "audit.csv"
        write_csv(path, [flat])
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            assert reader.fieldnames == CSV_COLUMNS
        assert rows[0]["github_issue_number"] == "43064"
        assert rows[0]["github_labels"] == "bug, app"
        assert rows[0]["body_clean"] == "line1\nline2, with comma"
        assert rows[0]["ai_platform"] == "val_platform"
        assert rows[0]["human_platform"] == ""
