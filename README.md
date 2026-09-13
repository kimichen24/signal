# Signal — AI Product Ops Intelligence System

> Detect → Explain → Prioritize → Act

Signal 是一个面向 AI 产品运营/产品团队的用户反馈智能系统。它把大量非结构化用户反馈转换为可追溯的产品信号：问题聚类、趋势变化、Release Impact、调查优先级与 Action Brief。

## 第一案例
- Case Study: OpenAI Codex
- Initial source: `openai/codex` GitHub Issues
- Target window: 最近 30 天
- 开发阶段：先使用 100 条 Issue 跑通 Pipeline，再扩大到全量
- 禁止：生成/伪造用户反馈，伪造指标或把相关性描述为因果

## 快速开始（Bootstrap 已完成）

### 1. Web App（Next.js + TypeScript）
```bash
npm install
cp .env.example .env.local   # Bootstrap 阶段可全部留空，应用以“未配置”状态诚实启动
npm run dev                  # http://localhost:3000 → 跳转到 /overview
```
- 健康检查：`GET /api/health`（真实探测 Supabase：ok / degraded / error）
- Supabase / OpenAI / GitHub 密钥仅用于服务端代码，不会进入浏览器包
- 未配置数据库时页面显示诚实的"Not configured"状态，不伪造指标

### 2. 数据库
在 Supabase SQL Editor 中执行 `supabase/schema.sql`（含 pgvector 扩展与 HNSW 索引）。

### 3. Python Pipeline
```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash（macOS/Linux: source .venv/bin/activate）
pip install -r pipeline/requirements.txt
python -m pytest tests -q       # 配置一致性测试
```
详见 `pipeline/README.md`。

### 4. 脚本
| 命令 | 说明 |
| --- | --- |
| `npm run dev` | 本地开发 |
| `npm run build` | 生产构建 |
| `npm run lint` | ESLint |
| `npm run typecheck` | TypeScript 严格检查 |
| `npm run test` | Vitest 单元测试 |
| `npm run test:python` | Python 配置测试（需先激活 venv） |

### 5. 开发流程
1. 阅读 `AGENTS.md`、`docs/PRD.md`、`docs/ARCHITECTURE.md`
2. 把 `prompts/00_BOOTSTRAP.md` 交给 Codex（已完成）
3. 按 `prompts/01` → `05` 逐轮执行，每轮先读文档、写 plan、小步提交

## MVP 页面
- Overview — What Changed?
- Feedback
- Insights
- Releases
- Opportunities

## MVP 核心能力
1. 反馈智能（Feedback Intelligence）
2. 痛点发现（Pain Point Discovery）
3. 新兴信号（Emerging Signals）
4. 版本影响分析（Release Impact Analysis）
5. 机会优先级（Opportunity Prioritization）
6. 证据支撑的行动简报（Evidence-backed Action Brief）

## 技术栈
- Next.js + TypeScript
- Tailwind CSS + shadcn/ui
- Python data pipeline
- Supabase / PostgreSQL / pgvector
- OpenAI API Structured Outputs + Embeddings
- GitHub REST API
- Vercel

## 评估结果（实测摘要）

独立参考一致率评估（50 条新鲜 holdout，盲评参考标签，v0.3.4 冻结版）：

| 字段 | 严格一致率 | Cohen's Kappa |
| --- | --- | --- |
| platform | 96% | — |
| product_scope | 94% | 0.725 |
| issue_type | 94% | 0.785 |
| surface | 94% | — |
| category | 70% | 0.659 |
| severity | 64%（±1 档内 96%） | — |

- 参考标签为独立盲评生成（AI 生成，非人工 ground truth），已在报告中声明
- 评估仅用于测量，未据此修改任何冻结产物
- 完整报告：`eval/holdout_v0.3.4_evaluation_report.md`；效率基准：`eval/codex_agent_benchmark_report.md`

## 产品原则
- 只用真实反馈（Real feedback only）
- 没有证据就没有洞察（No insight without evidence）
- AI 负责理解，数据负责决策（AI interprets; data decides）
- 相关性 ≠ 因果（Correlation ≠ causation）
- AI 辅助，人来决策（AI assists; human decides）
- 每条洞察必须可溯源（Every insight must be traceable）

## Portfolio 指标（实测）
数据规模、管道可靠性、评估一致率、处理效率与已知局限的全部实测值见
`docs/PORTFOLIO_METRICS.md`（不包含任何商业影响/收入/采用数据）。

## 数据诚实性（Limitations）
完整清单见 `docs/DATA_PROVENANCE.md`。要点：
- 数据集成员按创建时间窗口可复现；分析输入按 sha256 可审计
- 历史不足即 `insufficient_history`，零基线不显示增长百分比
- 低基线增长带警示，不作主要排序驱动
- Engagement 仅用公开 GitHub 字段，稀疏时透明重归一化
- Release Impact 只报告相关性，覆盖不足即拒绝比较
- 100 条开发集分析为 legacy（无 input hash），已保留并声明
- needs_refinement 宽簇不伪装成单一精确痛点

## 进度（Progress）
- [x] Phase 0 — Bootstrap：Next.js shell、typed env、Supabase server client、`/api/health`、pipeline 环境、lint/typecheck/test
- [x] Phase 1 — 100 条真实 Issue 已入库：`ingest_github` CLI（幂等 upsert、PR 过滤、created-at 窗口）、确定性 parser + `body_clean`、Feedback 页真实数据（`prompts/01_DATA_INGESTION.md`）
- [x] Phase 2 — AI 结构化抽取已跑通：MiMo provider（OpenAI 兼容 + 本地 schema 校验重试）、确定性元数据优先规范化、scope 三分类（工作流原则锁定）、severity rubric 人工盲评校准（20 条开发诊断集：严格一致率 55%→75%）。**冻结版本 v0.3.4：100/100 条分析完成，0 失败 0 重试**（`prompts/02_AI_EXTRACTION.md`）
- [x] Phase 3 — Intelligence：按 category 内确定性语义聚类（凝聚聚类 + cosine 阈值，参数/版本可复现，LLM 仅命名）、medoid 代表证据、Insights 页证据链、趋势历史充分性守卫（`insufficient_history` 诚实状态，绝不编造增长）（`prompts/03_INTELLIGENCE.md`）
- [x] Historical Expansion Phase 1 — 14 天确定性摄入：数据集 `codex-14d-2026-09-06`（8/23 → 9/6，窗口可复现），2254 条真实 issue 入库（403 PR 过滤、幂等验证通过），previous/current 周期数据充足，趋势验证解锁（AI 分析未跑，见工作量估算）
- [x] Historical Expansion Phase 2 — 全量 v0.3.4 分析完成：**2254/2254（0 缺失 0 重复 0 失败）**，有界并发（基准选优 c=6，37 条/分）、429/5xx 指数退避重试、逐条 `analysis_input_hash` 可审计、分块幂等提交。实测 5.72M in / 586k out tokens（对比 50 条试点投影 -4.5%/-9.4%）。Embedding/聚类/趋势待下一阶段
- [x] Historical Expansion Phase 3 — 全量嵌入（2,096 in-scope / 384 维 / 单一模型戳）+ 全量聚类重校准（跨进程确定性修复，0.12/3 → 197 簇）+ **首次真实 WoW 趋势**（previous 476 / current 729 → 不变量全 PASS，状态化 Emerging 资格）
- [x] Prompt 04 — Release Impact + Opportunities + Action Briefs：12 个真实 release（authoritative URL）、覆盖判定（**1 充分/11 insufficient_history**，v0.2 修正窗口 bug 后重算）、44 个 Opportunities（证据门 + Investigation Priority + 确定性状态）、43 份 MiMo Action Brief（1 个 LLM 生成失败："Desktop pet interactivity and interaction failures"，brief 为空，未伪造）。**未扩 30 天数据集**。Release Impact v0.1 存在 before/after 窗口相同 bug（`clipped_window()` 参数相同），v0.2 使用非重叠窗口修正
- [x] Prompt 05 Phase 1 — 新鲜 50 条 holdout 集生成（排除全部旧样本，seed=42 冻结 manifest）+ 真盲标注 CSV（零 AI 字段泄漏）。**等待人工标注**（human_* 7 列），标注完成后计算 6 字段一致率；开发诊断集（20 条）已封存，不再用于调优
- [x] Prompt 05 Phase 2 — 独立参考一致率评估完成：50/50 join 零缺失，六字段 exact agreement（platform 96%/surface 94%/scope 94%/issue_type 94%/category 70%/severity 64%），severity ±1 档内 96%，严格复合 17/50。**参考标签为独立盲评 Codex reference labels（AI 生成，非 ground truth）**。评估仅用 holdout，未据此修改任何冻结产物（见 eval/holdout_v0.3.4_evaluation_report.md）
- [ ] Phase 4 — Release + Action（`prompts/04_RELEASES_ACTIONS.md`）
- [ ] Phase 5 — Eval + 作品集收尾（`prompts/05_EVAL_POLISH.md`）
