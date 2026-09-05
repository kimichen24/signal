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
1. Feedback Intelligence
2. Pain Point Discovery
3. Emerging Signals
4. Release Impact Analysis
5. Opportunity Prioritization
6. Evidence-backed Action Brief

## 技术栈
- Next.js + TypeScript
- Tailwind CSS + shadcn/ui
- Python data pipeline
- Supabase / PostgreSQL / pgvector
- OpenAI API Structured Outputs + Embeddings
- GitHub REST API
- Vercel

## 产品原则
- Real feedback only
- No insight without evidence
- AI interprets; data decides
- Correlation ≠ causation
- AI assists; human decides
- Every insight must be traceable

## 进度（Progress）
- [x] Phase 0 — Bootstrap：Next.js shell、typed env、Supabase server client、`/api/health`、pipeline 环境、lint/typecheck/test
- [ ] Phase 1 — 100 条真实 Issue（`prompts/01_DATA_INGESTION.md`）
- [ ] Phase 2 — AI 结构化抽取（`prompts/02_AI_EXTRACTION.md`）
- [ ] Phase 3 — Intelligence（`prompts/03_INTELLIGENCE.md`）
- [ ] Phase 4 — Release + Action（`prompts/04_RELEASES_ACTIONS.md`）
- [ ] Phase 5 — Eval + 作品集收尾（`prompts/05_EVAL_POLISH.md`）
