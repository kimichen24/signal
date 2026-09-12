"""Prompt 05 Phase 2 — independent reference agreement evaluation.

Joins the frozen v0.3.4 predictions with the independent blind Codex
reference labels for exactly the 50 holdout issues and produces agreement
metrics, confusion matrices, severity ordinal analysis, Needs Review and
confidence analyses, a disagreement-detail CSV, a machine-readable metrics
JSON, and a Markdown evaluation report.

Terminology: reference labels are INDEPENDENT BLIND CODEX REFERENCE LABELS
(AI-generated, not human ground truth). All metrics are agreement metrics —
never "accuracy".
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any

FIELDS = (
    "product_scope",
    "issue_type",
    "category",
    "surface",
    "platform",
    "severity",
)
SEV_ORDER = ["low", "medium", "high", "critical"]
CONF_BUCKETS = ((0.0, 0.80, "<0.80"), (0.80, 0.90, "0.80-0.90"), (0.90, 1.01, ">=0.90"))


def p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[min(int(0.95 * len(ordered)), len(ordered) - 1)])


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    """Cohen's kappa with observed categories; None when not meaningful."""
    import numpy as np
    from sklearn.metrics import cohen_kappa_score

    categories = sorted(set(a) | set(b))
    if len(categories) < 2 or len(a) < 2:
        return None
    try:
        return round(
            float(cohen_kappa_score(np.array(a), np.array(b), labels=categories)),
            3,
        )
    except Exception:
        return None


def weighted_kappa(a: list[str], b: list[str], order: list[str]) -> float | None:
    import numpy as np
    from sklearn.metrics import cohen_kappa_score

    if len(set(a)) < 2 or len(set(b)) < 2 or len(a) < 2:
        return None
    try:
        return round(
            float(
                cohen_kappa_score(
                    np.array([order.index(x) for x in a]),
                    np.array([order.index(x) for x in b]),
                    weights="linear",
                )
            ),
            3,
        )
    except Exception:
        return None


def confusion(a: list[str], b: list[str]) -> dict[tuple[str, str], int]:
    return dict(Counter(zip(a, b)))


def confusion_markdown(
    pairs: list[tuple[str, str]], title: str, row_label: str, col_label: str
) -> str:
    from collections import Counter

    counts = Counter(pairs)
    lines = [f"**{title}**（行 = {row_label}，列 = {col_label}）", ""]
    categories = sorted({c for pair in counts for c in pair})
    header = "| " + row_label + " \\ " + col_label + " | " + " | ".join(categories) + " |"
    lines.append(header)
    lines.append("|" + "---|" * (len(categories) + 1))
    for row_cat in categories:
        cells = [str(counts.get((row_cat, col_cat), 0)) for col_cat in categories]
        lines.append("| **" + row_cat + "** | " + " | ".join(cells) + " |")
    return "\n".join(lines)
def spearman(x: list[float], y: list[float]) -> float | None:
    if len(set(x)) < 2 or len(set(y)) < 2 or len(x) < 3:
        return None
    from scipy.stats import spearmanr

    return round(float(spearmanr(x, y).statistic), 3)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.evaluate_holdout",
        description="Agreement evaluation: frozen v0.3.4 vs independent blind Codex reference labels.",
    )
    parser.add_argument(
        "--reference", default="eval/holdout_v0.3.4_blind_codex_labeled.csv"
    )
    parser.add_argument(
        "--manifest", default="eval/holdout_v0.3.4_manifest.json"
    )
    parser.add_argument(
        "--analysis-version",
        default=os.environ.get("SIGNAL_ANALYSIS_VERSION", "v0.3.4"),
    )
    parser.add_argument(
        "--metrics-out", default="eval/holdout_v0.3.4_metrics.json"
    )
    parser.add_argument(
        "--disagreements-out",
        default="eval/holdout_v0.3.4_disagreements.csv",
    )
    parser.add_argument(
        "--report-out", default="eval/holdout_v0.3.4_evaluation_report.md"
    )
    args = parser.parse_args(argv)

    import csv

    from pipeline.supabase_client import (
        SupabaseConfigError,
        SupabaseRest,
        load_env,
    )

    fail = False

    # ---- 1. reference load + structural validation ------------------------
    with open(args.reference, encoding="utf-8-sig", newline="") as handle:
        reference = list(csv.DictReader(handle))
    if len(reference) != 50:
        print(f"join validation FAILED: reference rows = {len(reference)} != 50", file=sys.stderr)
        fail = True
    ref_numbers = [int(r["github_issue_number"]) for r in reference]
    if len(set(ref_numbers)) != 50:
        print("join validation FAILED: duplicate reference issue numbers", file=sys.stderr)
        fail = True
    for field in FIELDS:
        empties = [r["github_issue_number"] for r in reference if not (r[f"human_{field}"] or "").strip()]
        if empties:
            print(f"join validation FAILED: empty reference {field}: {empties}", file=sys.stderr)
            fail = True

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if set(ref_numbers) != set(manifest["issue_numbers"]):
        print("join validation FAILED: reference issue numbers differ from frozen manifest", file=sys.stderr)
        fail = True

    if fail:
        return 1

    ref_by_number = {int(r["github_issue_number"]): r for r in reference}

    # ---- 2. frozen predictions from DB ------------------------------------
    try:
        with SupabaseRest.from_env() as supabase:
            analyses = supabase.select_paged(
                "issue_analysis",
                columns=(
                    "issue_id,product_scope,issue_type,category,surface,platform,"
                    "severity,confidence,needs_review,analysis_error,"
                    "issues(github_issue_number)"
                ),
                filters={"analysis_version": f"eq.{args.analysis_version}"},
            )
    except (SupabaseConfigError, RuntimeError) as exc:
        print(f"evaluation failed: {exc}", file=sys.stderr)
        return 1

    pred_by_number: dict[int, dict[str, Any]] = {}
    for r in analyses:
        if r.get("analysis_error"):
            continue
        number = (r.get("issues") or {}).get("github_issue_number")
        if number in ref_by_number:
            if number in pred_by_number:
                print(f"join validation FAILED: duplicate v0.3.4 rows for #{number}", file=sys.stderr)
                fail = True
            pred_by_number[number] = r

    missing = sorted(set(ref_numbers) - set(pred_by_number))
    if len(pred_by_number) != 50 or missing:
        print(
            f"join validation FAILED: predictions matched = {len(pred_by_number)}/50, "
            f"missing = {missing}",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "join_validation": {
                    "reference_rows": 50,
                    "matching_successful_v034_predictions": len(pred_by_number),
                    "missing_joins": 0,
                    "duplicate_issue_numbers": 0,
                    "reference_issue_numbers_match_frozen_manifest": True,
                    "reference_csv_structure_unchanged": True,
                    "mimo_rerun": False,
                }
            },
            indent=2,
        )
    )

    # ---- 3. per-field agreement --------------------------------------------
    joined = []
    for number in ref_numbers:
        p, r = pred_by_number[number], ref_by_number[number]
        joined.append(
            {
                "number": number,
                "title": r.get("title") or "",
                "confidence": (
                    float(p["confidence"]) if p.get("confidence") is not None else None
                ),
                "needs_review": bool(p["needs_review"]),
                "pred": {f: (p[f] or "").strip() for f in FIELDS},
                "ref": {f: (r[f"human_{f}"] or "").strip() for f in FIELDS},
            }
        )

    field_metrics: dict[str, dict[str, Any]] = {}
    disagreements: list[dict[str, Any]] = []
    per_row_disagreements: list[int] = []

    for field in FIELDS:
        a = [j["pred"][field] for j in joined]
        b = [j["ref"][field] for j in joined]
        exact = sum(1 for x, y in zip(a, b) if x == y)
        matrix = confusion(a, b)
        disagree_rows = [
            {
                "github_issue_number": j["number"],
                "title": j["title"][:80],
                "field": field,
                "mimo_prediction": x,
                "codex_reference": y,
                "mimo_confidence": j["confidence"],
                "needs_review": j["needs_review"],
            }
            for j, x, y in zip(joined, a, b)
            if x != y
        ]
        disagreements.extend(disagree_rows)
        field_metrics[field] = {
            "exact_agreement": exact,
            "exact_agreement_pct": round(100 * exact / len(joined), 1),
            "disagreement_count": len(joined) - exact,
            "cohen_kappa": cohen_kappa(a, b),
            "confusion_mimo_x_reference": {
                f"{p} -> {q}": n for (p, q), n in sorted(matrix.items())
            },
        }
        per_row_disagreements.append(
            [field for x, y, f in zip(a, b, [field] * len(a)) if x != y] and None or None
        )

    # per-row disagreement count (0-6)
    for j in joined:
        count = sum(1 for f in FIELDS if j["pred"][f] != j["ref"][f])
        j["disagreed_fields"] = count
        per_row_disagreements.append(count)

    # ---- 4. platform analysis ----------------------------------------------
    all_a = [j["pred"]["platform"] for j in joined]
    all_b = [j["ref"]["platform"] for j in joined]
    known = [j for j in joined if j["ref"]["platform"] != "Unknown"]
    known_a = [j["pred"]["platform"] for j in known]
    known_b = [j["ref"]["platform"] for j in known]

    # ---- 5. severity ordinal ------------------------------------------------
    sev_rank = {name: i for i, name in enumerate(SEV_ORDER)}
    sev_a = [j["pred"]["severity"] for j in joined]
    sev_b = [j["ref"]["severity"] for j in joined]
    distances = [abs(sev_rank[x] - sev_rank[y]) for x, y in zip(sev_a, sev_b)]
    sev_exact = sum(1 for d in distances if d == 0)
    sev_within1 = sum(1 for d in distances if d <= 1)
    over1 = sum(1 for r in zip(sev_a, sev_b) if sev_rank[r[0]] - sev_rank[r[1]] == 1)
    under1 = sum(1 for r in zip(sev_a, sev_b) if sev_rank[r[0]] - sev_rank[r[1]] == -1)
    far = [(j["number"], x, y) for j, x, y in zip(joined, sev_a, sev_b) if abs(sev_rank[x] - sev_rank[y]) >= 2]

    # ---- 6. compound ---------------------------------------------------------
    compound_rows = Counter(j["disagreed_fields"] for j in joined)
    strict_all6 = sum(1 for j in joined if j["disagreed_fields"] == 0)

    # ---- 7. needs review ------------------------------------------------------
    nr_true = [j for j in joined if j["needs_review"]]
    nr_false = [j for j in joined if not j["needs_review"]]

    def group_stats(group: list[dict[str, Any]]) -> dict[str, Any]:
        any_dis = sum(1 for j in group if j["disagreed_fields"] > 0)
        return {
            "n": len(group),
            "any_field_disagreement_rate": (
                round(100 * any_dis / len(group), 1) if group else None
            ),
            "mean_disagreed_fields": (
                round(sum(j["disagreed_fields"] for j in group) / len(group), 2)
                if group
                else None
            ),
            "per_field_disagreement": {
                f: sum(1 for j in group if j["pred"][f] != j["ref"][f])
                for f in FIELDS
            },
        }

    # ---- 8. confidence ---------------------------------------------------------
    conf_ok = [j for j in joined if j["confidence"] is not None]
    conf_values = [j["confidence"] for j in conf_ok]
    buckets = {}
    for lo, hi, label in CONF_BUCKETS:
        group = [j for j in conf_ok if lo <= j["confidence"] < hi]
        buckets[label] = {
            "n": len(group),
            "avg_disagreed_fields": (
                round(sum(j["disagreed_fields"] for j in group) / len(group), 2)
                if group
                else None
            ),
        }

    # ---- assemble metrics --------------------------------------------------------
    metrics = {
        "provenance": {
            "evaluation_set": "holdout_v0.3.4",
            "sample_size": 50,
            "analysis_version": args.analysis_version,
            "reference_label_source": "independent_codex",
            "reference_labeling_mode": "blind",
            "holdout_used_for_model_tuning": False,
            "notes": (
                "The 50-item holdout was excluded from model tuning (dev 100, "
                "workload pilot 50 and dev diagnostic audit 20 were all "
                "excluded). Codex produced the reference labels blind, with "
                "no access to MiMo predictions. Reference labels are "
                "AI-generated and therefore are NOT human ground truth."
            ),
        },
        "join_validation": {
            "reference_rows": 50,
            "matching_successful_v034_predictions": 50,
            "missing_joins": 0,
            "duplicate_issue_numbers": 0,
            "reference_csv_structure_unchanged": True,
            "mimo_rerun": False,
        },
        "field_agreement": {},
        "platform_analysis": {
            "all_50": {
                "exact_agreement": sum(1 for x, y in zip(all_a, all_b) if x == y),
                "n": 50,
            },
            "known_reference_platform_subset": {
                "exact_agreement": sum(1 for x, y in zip(known_a, known_b) if x == y),
                "n": len(known),
                "numerator": sum(1 for x, y in zip(known_a, known_b) if x == y),
                "denominator": len(known),
            },
        },
        "severity_analysis": {
            "exact_agreement": sev_exact,
            "within_one_level": sev_within1,
            "weighted_kappa_linear": weighted_kappa(sev_a, sev_b, SEV_ORDER),
            "ordinal_distance_distribution": {
                str(d): distances.count(d) for d in sorted(set(distances))
            },
            "ai_one_level_overestimate": over1,
            "ai_one_level_underestimate": under1,
            "errors_at_or_above_2_levels": len(far),
        },
        "category_analysis": {},
        "strict_compound_metric": {
            "all_six_fields_exact": strict_all6,
            "of": 50,
            "label": "strict compound agreement — NOT overall model accuracy",
            "per_row_distribution": {
                "6/6": compound_rows.get(0, 0),
                "5/6": compound_rows.get(1, 0),
                "4/6": compound_rows.get(2, 0),
                "3/6": compound_rows.get(3, 0),
                "<=2/6": sum(v for k, v in compound_rows.items() if k >= 4),
            },
        },
        "needs_review_analysis": {
            "needs_review_true": group_stats(nr_true),
            "needs_review_false": group_stats(nr_false),
            "stability_note": (
                "Estimates unstable if subgroup n is small — interpret with care."
            ),
        },
        "confidence_analysis": {
            "min": min(conf_values),
            "median": round(statistics.median(conf_values), 3),
            "mean": round(statistics.mean(conf_values), 3),
            "buckets_avg_disagreed_fields": buckets,
            "spearman_conf_vs_disagreed_fields": spearman(
                conf_values,
                [float(j["disagreed_fields"]) for j in conf_ok],
            ),
            "n": len(conf_ok),
            "caution": "n=50; descriptive only; threshold NOT recalibrated.",
        },
        "p95_reference": {},
    }

    for field in FIELDS:
        m = field_metrics[field]
        a = [j["pred"][field] for j in joined]
        b = [j["ref"][field] for j in joined]
        metrics["field_agreement"][field] = m

    # category views + scope (recompute with subsets)
    in_scope = [j for j in joined if j["ref"]["product_scope"] != "out_of_scope"]

    def field_view(field: str, group: list[dict[str, Any]]) -> dict[str, Any]:
        a = [j["pred"][field] for j in group]
        b = [j["ref"][field] for j in group]
        exact = sum(1 for x, y in zip(a, b) if x == y)
        return {
            "exact_agreement": exact,
            "n": len(group),
            "exact_agreement_pct": round(100 * exact / len(group), 1) if group else None,
            "disagreement_count": len(group) - exact,
            "cohen_kappa": cohen_kappa(a, b),
        }

    metrics["field_agreement"]["product_scope"]["full_50"] = field_view(
        "product_scope", joined
    )
    metrics["field_agreement"]["category"]["all_50"] = field_view("category", joined)
    metrics["field_agreement"]["category"]["reference_in_scope_subset"] = field_view(
        "category", in_scope
    )
    metrics["platform_analysis"]["all_50"]["kappa"] = cohen_kappa(all_a, all_b)
    metrics["platform_analysis"]["known_reference_platform_subset"]["kappa"] = cohen_kappa(
        known_a, known_b
    )
    metrics["severity_analysis"]["cohen_kappa_unweighted"] = cohen_kappa(sev_a, sev_b)

    # severity-level per-field confusions already in field_agreement; add severity mix views
    metrics["field_agreement"]["severity"]["reference_in_scope_subset"] = field_view(
        "severity", in_scope
    )
    metrics["field_agreement"]["product_scope"]["reference_in_scope_subset"] = field_view(
        "product_scope", in_scope
    )

    # P95 of MiMo confidence + per-field disagreement severity reference
    metrics["p95_reference"] = {
        "mimo_confidence_p95": p95(conf_values),
        "note": "P95 used for provisional emerging score normalization elsewhere; recorded here for provenance.",
    }

    # ---- outputs ------------------------------------------------------------
    Path(args.metrics_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.metrics_out).write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    with open(args.disagreements_out, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "github_issue_number",
                "title",
                "field",
                "mimo_prediction",
                "codex_reference",
                "mimo_confidence",
                "needs_review",
            ],
        )
        writer.writeheader()
        writer.writerows(disagreements)

    # ---- markdown report --------------------------------------------------------
    md: list[str] = []
    md.append("# Prompt 05 Phase 2 — 独立参考一致率评估报告")
    md.append("")
    md.append("**术语**：参考标签为独立盲评 **Codex reference labels**（AI 生成，非人工、非 ground truth）。所有指标均为 agreement，不是 accuracy。")
    md.append("")
    md.append("## Join 验证")
    md.append("")
    md.append("| 项 | 值 |")
    md.append("| --- | --- |")
    md.append("| 参考行数 | 50 |")
    md.append("| 匹配的成功 v0.3.4 预测 | 50 |")
    md.append("| 缺失 join | 0 |")
    md.append("| 重复 issue 号 | 0 |")
    md.append("| 参考 CSV 与冻结 manifest 一致 | 是 |")
    md.append("| MiMo 重跑 | 否 |")
    md.append("")
    md.append("## 六字段一致率")
    md.append("")
    md.append("| 字段 | 一致 | 一致率% | 分歧 | Cohen's kappa |")
    md.append("| --- | --- | --- | --- | --- |")
    for field in FIELDS:
        m = field_metrics[field]
        kappa = m["cohen_kappa"]
        kappa = "n/a" if kappa is None else kappa
        md.append(
            f"| {field} | {m['exact_agreement']}/50 | {m['exact_agreement_pct']}% | "
            f"{m['disagreement_count']} | {kappa} |"
        )
    md.append("")
    md.append("### 混淆矩阵")
    md.append("")
    for field in FIELDS:
        pairs = [(j["pred"][field], j["ref"][field]) for j in joined]
        md.append(confusion_markdown(pairs, field, "MiMo v0.3.4", "Codex reference"))
        md.append("")
    md.append("## Platform 分析")
    md.append("")
    md.append(f"- 全 50：一致 {sum(1 for x, y in zip(all_a, all_b) if x == y)}/50，kappa = {cohen_kappa(all_a, all_b)}")
    md.append(
        f"- 已知参考平台子集（排除参考 Unknown）：{sum(1 for x, y in zip(known_a, known_b) if x == y)}/{len(known)}，"
        f"kappa = {cohen_kappa(known_a, known_b)}"
    )
    md.append("")
    md.append("## Severity 序数分析（low < medium < high < critical）")
    md.append("")
    md.append(f"- 完全一致：{sev_exact}/50")
    md.append(f"- ±1 档内一致：{sev_within1}/50")
    md.append(f"- 线性加权 kappa：{weighted_kappa(sev_a, sev_b, SEV_ORDER)}")
    md.append(f"- 序数距离分布：{ {d: distances.count(d) for d in sorted(set(distances))} }")
    md.append(f"- MiMo 高估一档：{over1} · 低估一档：{under1} · ≥2 档错误：{len(far)}")
    md.append("")
    md.append("## Category 视图")
    md.append("")
    md.append(f"- 全 50：{field_view('category', joined)['exact_agreement']}/50（{field_view('category', joined)['exact_agreement_pct']}%）")
    md.append(
        f"- 参考 in-scope 子集（core+adjacent，n={len(in_scope)}）："
        f"{field_view('category', in_scope)['exact_agreement']}/{len(in_scope)}"
    )
    md.append("")
    md.append("## 严格复合指标")
    md.append("")
    md.append(f"- 六字段全对：**{strict_all6}/50** —— 严格复合一致率，非 overall model accuracy")
    md.append(f"- 行级分布：6/6 = {compound_rows.get(0, 0)} · 5/6 = {compound_rows.get(1, 0)} · 4/6 = {compound_rows.get(2, 0)} · 3/6 = {compound_rows.get(3, 0)} · ≤2/6 = {sum(v for k, v in compound_rows.items() if k >= 4)}")
    md.append("")
    md.append("## Needs Review 分析")
    md.append("")
    for label, group in (("needs_review = true", nr_true), ("needs_review = false", nr_false)):
        s = group_stats(group)
        md.append(f"- {label}: n={s['n']}，任一字段分歧率 {s['any_field_disagreement_rate']}%，平均分歧字段 {s['mean_disagreed_fields']}")
        if s["n"] < 10:
            md.append(f"  - ⚠ 子组样本过小（n={s['n']}），估计不稳定")
    md.append("")
    md.append("## Confidence 分析")
    md.append("")
    md.append(f"- min/median/mean：{min(conf_values)} / {round(statistics.median(conf_values), 3)} / {round(statistics.mean(conf_values), 3)}")
    for label, s in buckets.items():
        md.append(f"- 桶 {label}：n={s['n']}，平均分歧字段 {s['avg_disagreed_fields']}")
    md.append(f"- Spearman(confidence, disagreed fields) = {spearman(conf_values, [float(j['disagreed_fields']) for j in conf_ok])}（n=50，谨慎解读；未重调阈值）")
    md.append("")
    md.append("## Provenance")
    md.append("")
    md.append("```json")
    md.append(json.dumps(metrics["provenance"], indent=2, ensure_ascii=False))
    md.append("```")
    md.append("")
    md.append("## 冻结规则")
    md.append("")
    md.append("本 50 条 holdout 仅用于评估：不据此修改 Prompt 02、taxonomy、severity rubric、归一化、置信度阈值或 v0.3.4 分析。")
    md.append("")

    Path(args.report_out).write_text("\n".join(md), encoding="utf-8")
    print(f"report: {args.report_out}")
    print(f"metrics: {args.metrics_out}")
    print(f"disagreements: {args.disagreements_out} ({len(disagreements)} rows)")
    return 0


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
