# Portfolio Metrics（作品集指标 — 仅实测值，全部可从数据库与评估工件复核）

> 定位声明（冻结）：50-item frozen holdout independently blind-labeled by Codex; metrics represent inter-model agreement, not human-ground-truth accuracy.
> 本页不包含任何商业影响、留存、收入或用户采用数据。

## 1. Dataset scale（数据集规模）

| 指标 | 实测值 |
| --- | --- |
| 数据集 | `codex-14d-2026-09-06`（openai/codex，14 个完整日历日，按 issue created_at 窗口定义，可复现） |
| 摄入 issue | 2,254（2,800 条 seen，403 PR 过滤，幂等重跑验证 2,254→2,254） |
| v0.3.4 分析覆盖 | **2,254 / 2,254**（0 缺失 · 0 重复 · 0 失败） |
| in-scope（分析后判定） | 2,096（core 1,962 + adjacent 134）· out_of_scope 158（保留不删除） |
| 生产聚类 | 197 簇 / 1,395 成员（覆盖 66.6%，配置 0.12/3/category-only，参数与版本落盘可复现） |
| 嵌入 | 2,096 / 2,096（384 维，单一模型戳 `local:intfloat/multilingual-e5-small`） |
| 周期体量 | previous 1,064 / current 1,190（raw）；in-scope 994 / 1,102 |

## 2. Pipeline reliability（管道可靠性）

| 验证 | 实测 |
| --- | --- |
| 摄入幂等 | 重跑后计数不变；`github_issue_number` 唯一约束 + 逐簇周期和校验通过 |
| 分析完成不变量 | 成功 2,254 · 缺失 0 · 重复 0 · 窗口外 0 |
| 嵌入不变量 | 缺失 0 · 维度全 384 · 模型戳 100% 一致 · 零重复 |
| 趋势不变量 | raw 1064+1190=2254 · in-scope 994+1102=2096 · clustered 666+729=1395 · 逐簇 prev+curr=size 全部成立 |
| 输入可审计 | 新分析 2,154/2,154 带 `analysis_input_hash`；100 条 dev 分析标记 legacy（源行被重摄入覆盖，无法保证精确重建） |
| 聚类跨进程确定性 | 修复行序不稳定后，跨进程指纹验证一致（`docs/CLUSTERING_CALIBRATION.md`） |
| 测试 | pytest 158 · vitest 12 · typecheck/lint/build 全绿 |

## 3. Evaluation agreement（独立参考一致率 — 非 accuracy）

> 评估集：50 条冻结 holdout（独立盲评 Codex reference labels，AI 生成；排除 dev100/pilot50/audit20，从未用于调优）

| 字段 | 一致 | 率 | Cohen's κ |
| --- | --- | --- | --- |
| platform | 48/50 | 96.0% | 0.946（已知平台子集 40/41，κ=0.964） |
| surface | 47/50 | 94.0% | 0.864 |
| product_scope | 47/50 | 94.0% | 0.725 |
| issue_type | 47/50 | 94.0% | 0.785 |
| category | 35/50 | 70.0% | 0.659 |
| severity（exact） | 32/50 | 64.0% | 0.429（线性加权 0.532） |
| severity（±1 档） | 48/50 | 96.0% | — |
| 六字段全对（严格复合） | 17/50 | 34.0% | — |

需求复核（Needs Review）子组 n=1，估计不稳定。置信度与分歧数 Spearman = −0.25（弱负相关，描述性）。

## 4. Processing efficiency（处理效率 — 实测吞吐，非人工对照）

| 指标 | 实测值 |
| --- | --- |
| 分类吞吐 | 有界并发 c=6 下 ~37 issues/分钟（100 条基准实测；c=4 为 29.3/分，零 429/5xx） |
| 全量历史批运行 | 2,104 条 ≈ 1.88 小时批内运行时长（串行对照 ≈ 5.8 小时投影） |
| 嵌入吞吐 | 2,005 条 ≈ 22 分钟（本地 e5-small CPU） |
| Token（全项目实测累计） | 5,723,607 in / 585,889 out |
| 效率基准（已执行） | 独立 Codex agent 双臂基准（15+15 匹配 issue）：审阅 Signal 输出 vs 无辅助分诊，**墙钟时间 -91.8%**、**吞吐 12.21×**；B 组 66.7% 零纠错。**计量为 Codex-agent 工作流时间，非人工效率；计时为批级别而非逐条**。详见证 `eval/codex_agent_benchmark_report.md` |

## 5. Known limitations（已知局限 — 详见 docs/DATA_PROVENANCE.md）

- 参考标签为 AI 生成（独立盲评 Codex reference labels），非人工 ground truth
- category 是最弱的语义字段（70%，κ=0.659；Reliability→App/UI/UX 边界分歧最常见）
- severity 存在系统性向上校准偏置（16 次高估一档 / 0 次低估），±1 档内 96%
- Needs Review 有效性未建立（holdout 子组 n=1，不稳定）
- confidence 与分歧数仅弱负相关（Spearman −0.25，描述性，n=50）
- 100 条开发集分析为 legacy（无 input hash，源行被重摄入覆盖）
- 趋势覆盖不足即 `insufficient_history`；零基线不显示增长率；低基线带警示
- Release Impact 仅报告相关性；覆盖不足即拒绝比较
