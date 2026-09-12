# Prompt 05 Phase 2 — 独立参考一致率评估报告

**术语**：参考标签为独立盲评 **Codex reference labels**（AI 生成，非人工、非 ground truth）。所有指标均为 agreement，不是 accuracy。

## 评估定位（冻结措辞）

> 50-item frozen holdout independently blind-labeled by Codex; metrics represent inter-model agreement, not human-ground-truth accuracy.

## 关键发现（修正后数字）

- platform agreement 96%
- surface agreement 94%
- product_scope agreement 94%（分歧 = 3）
- issue_type agreement 94%（分歧 = 3）
- category agreement 70%
- severity exact agreement 64%
- severity within ±1 level 96%
- strict all-six agreement 34%

以上均非 accuracy。

## Join 验证

| 项 | 值 |
| --- | --- |
| 参考行数 | 50 |
| 匹配的成功 v0.3.4 预测 | 50 |
| 缺失 join | 0 |
| 重复 issue 号 | 0 |
| 参考 CSV 与冻结 manifest 一致 | 是 |
| MiMo 重跑 | 否 |

## 六字段一致率

| 字段 | 一致 | 一致率% | 分歧 | Cohen's kappa |
| --- | --- | --- | --- | --- |
| product_scope | 47/50 | 94.0% | 3 | 0.725 |
| issue_type | 47/50 | 94.0% | 3 | 0.785 |
| category | 35/50 | 70.0% | 15 | 0.659 |
| surface | 47/50 | 94.0% | 3 | 0.864 |
| platform | 48/50 | 96.0% | 2 | 0.946 |
| severity | 32/50 | 64.0% | 18 | 0.429 |

### 混淆矩阵

**product_scope**（行 = MiMo v0.3.4，列 = Codex reference）

| MiMo v0.3.4 \ Codex reference | codex_adjacent | codex_core | out_of_scope |
|---|---|---|---|
| **codex_adjacent** | 3 | 1 | 1 |
| **codex_core** | 0 | 43 | 0 |
| **out_of_scope** | 0 | 1 | 1 |

**issue_type**（行 = MiMo v0.3.4，列 = Codex reference）

| MiMo v0.3.4 \ Codex reference | bug | documentation | feature_request | other |
|---|---|---|---|---|
| **bug** | 41 | 0 | 1 | 0 |
| **documentation** | 0 | 1 | 0 | 0 |
| **feature_request** | 0 | 0 | 5 | 1 |
| **other** | 1 | 0 | 0 | 0 |

**category**（行 = MiMo v0.3.4，列 = Codex reference）

| MiMo v0.3.4 \ Codex reference | App / UI / UX | Authentication & Account | CLI | Context & Memory | IDE Integration | Installation & Updates | MCP & Integrations | Model Quality | Onboarding & Documentation | Other | Performance | Reliability | Safety & Permissions | Tool Execution | Usage & Credits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **App / UI / UX** | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Authentication & Account** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **CLI** | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Context & Memory** | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **IDE Integration** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Installation & Updates** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **MCP & Integrations** | 0 | 1 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Model Quality** | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Onboarding & Documentation** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| **Other** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |
| **Performance** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 | 1 |
| **Reliability** | 3 | 1 | 0 | 0 | 1 | 2 | 0 | 0 | 0 | 0 | 1 | 6 | 0 | 1 | 0 |
| **Safety & Permissions** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| **Tool Execution** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 8 | 0 |
| **Usage & Credits** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |

**surface**（行 = MiMo v0.3.4，列 = Codex reference）

| MiMo v0.3.4 \ Codex reference | CLI | Codex App | IDE Extension | Unknown | Web |
|---|---|---|---|---|---|
| **CLI** | 9 | 0 | 0 | 0 | 0 |
| **Codex App** | 0 | 35 | 0 | 0 | 1 |
| **IDE Extension** | 0 | 0 | 1 | 0 | 0 |
| **Unknown** | 0 | 0 | 0 | 2 | 0 |
| **Web** | 1 | 1 | 0 | 0 | 0 |

**platform**（行 = MiMo v0.3.4，列 = Codex reference）

| MiMo v0.3.4 \ Codex reference | Android | Linux | Unknown | Windows | iOS | macOS |
|---|---|---|---|---|---|---|
| **Android** | 1 | 0 | 0 | 0 | 0 | 0 |
| **Linux** | 0 | 6 | 0 | 0 | 0 | 0 |
| **Unknown** | 0 | 0 | 8 | 0 | 0 | 0 |
| **Windows** | 0 | 0 | 0 | 17 | 1 | 0 |
| **iOS** | 0 | 0 | 0 | 0 | 2 | 0 |
| **macOS** | 0 | 0 | 1 | 0 | 0 | 14 |

**severity**（行 = MiMo v0.3.4，列 = Codex reference）

| MiMo v0.3.4 \ Codex reference | critical | high | low | medium |
|---|---|---|---|---|
| **critical** | 1 | 1 | 0 | 1 |
| **high** | 0 | 22 | 1 | 7 |
| **low** | 0 | 0 | 3 | 0 |
| **medium** | 0 | 0 | 8 | 6 |

## Platform 分析

- 全 50：一致 48/50，kappa = 0.946
- 已知参考平台子集（排除参考 Unknown）：40/41，kappa = 0.964

## Severity 序数分析（low < medium < high < critical）

- 完全一致：32/50
- ±1 档内一致：48/50
- 线性加权 kappa：0.532
- 序数距离分布：{0: 32, 1: 16, 2: 2}
- MiMo 高估一档：16 · 低估一档：0 · ≥2 档错误：2

## Category 视图

- 全 50：35/50（70.0%）
- 参考 in-scope 子集（core+adjacent，n=48）：33/48

## 严格复合指标

- 六字段全对：**17/50** —— 严格复合一致率，非 overall model accuracy
- 行级分布：6/6 = 17 · 5/6 = 23 · 4/6 = 9 · 3/6 = 1 · ≤2/6 = 0

## Needs Review 分析

- needs_review = true: n=1，任一字段分歧率 100.0%，平均分歧字段 2.0
  - ⚠ 子组样本过小（n=1），估计不稳定
- needs_review = false: n=49，任一字段分歧率 65.3%，平均分歧字段 0.86

## Confidence 分析

- min/median/mean：0.6 / 0.88 / 0.876
- 桶 <0.80：n=1，平均分歧字段 2.0
- 桶 0.80-0.90：n=25，平均分歧字段 1.04
- 桶 >=0.90：n=24，平均分歧字段 0.67
- Spearman(confidence, disagreed fields) = -0.25（n=50，谨慎解读；未重调阈值）

## Provenance

```json
{
  "evaluation_set": "holdout_v0.3.4",
  "sample_size": 50,
  "analysis_version": "v0.3.4",
  "reference_label_source": "independent_codex",
  "reference_labeling_mode": "blind",
  "holdout_used_for_model_tuning": false,
  "notes": "The 50-item holdout was excluded from model tuning (dev 100, workload pilot 50 and dev diagnostic audit 20 were all excluded). Codex produced the reference labels blind, with no access to MiMo predictions. Reference labels are AI-generated and therefore are NOT human ground truth."
}
```

## 冻结规则

本 50 条 holdout 仅用于评估：不据此修改 Prompt 02、taxonomy、severity rubric、归一化、置信度阈值或 v0.3.4 分析。
