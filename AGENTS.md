# AGENTS.md — Signal Engineering Contract

你正在开发 Signal，一个用于作品集展示的 AI Product Ops Intelligence System。

## 1. 首要目标
构建一个真实、可解释、可验证的产品，而不是一个“AI Dashboard Demo”。

核心链路：
GitHub Issues → 清洗 → 结构化抽取 → 分类 → 语义聚类 → 趋势检测 → Release Impact → Priority → Action Brief → Evidence

## 2. 不可违反的产品约束
1. 不得生成 synthetic feedback 并伪装成真实用户反馈。
2. 不得硬编码“Top Issues”结果；所有指标必须由真实导入数据计算。
3. 不得声称某 Release “导致”某问题；只能报告 release 前后相关性变化。
4. 不得把 AI-estimated severity 写成官方 severity。
5. 不得把 Signal Priority 写成 OpenAI 的 P0/P1；命名为 `Investigation Priority`。
6. 每个 Insight 必须至少关联真实 Issue evidence。
7. 每个 Action Brief 必须能够解释为什么给出该建议。
8. AI 只负责语义理解、抽取、摘要、subtopic、hypothesis；计数、增长率、趋势与评分必须用确定性代码计算。
9. 任何展示数字必须来自数据库查询，不允许 placeholder 冒充真实结果。
10. 低置信度结果要支持 Needs Review，而不是强行给确定答案。

## 3. MVP Scope
只实现：
- Overview
- Feedback
- Insights
- Releases
- Opportunities
- 100 条人工 Eval
- 100 条开发样本 → 全量扩展

不要实现：
- Reddit / Discord / App Store
- 登录/多租户
- Agent chat
- 自动 PRD/roadmap
- 实时 streaming ingestion
- 企业权限
- 完整 Eval SaaS

## 4. 数据源
Repository: `openai/codex`
使用 GitHub REST API。
只收 Issue，不收 PR。
保留原始 body，并额外保存清洗后的 `body_clean`。

## 5. AI 规则
- 使用 OpenAI Responses API。
- 结构化抽取必须使用 JSON Schema / Structured Outputs，而不是自由文本后再正则解析。
- 模型名通过环境变量配置，不要写死在业务逻辑。
- Embedding 模型也通过环境变量配置。
- 所有 AI 输出写入 `analysis_version`，便于重跑比较。
- 失败要可重试并记录 error，不要静默吞掉。

## 6. 数据质量
- Raw issue 永久保留。
- 大日志、Doctor Report、代码块可以从 LLM 输入中裁剪，但不能从 raw 数据中删除。
- PR 必须过滤。
- Duplicate 不直接删除；重复本身是需求强度信号。可标记 duplicate_group_id。
- Feature Request 与 Bug 分开。

## 7. UI 原则
风格：Linear / Vercel / modern AI SaaS。
- 极简
- 强 Typography
- 大留白
- 少量状态色
- 数据层级清晰
- 不做花哨渐变/玻璃拟态
- 不要塞 Chatbot
首页第一问题必须是：`What changed?`

## 8. Definition of Done
一次完整 Demo 必须可以：
1. 看到真实分析 Issue 数量。
2. 看到 What Changed / Emerging Signals。
3. 点击一个 Signal 查看趋势与 segment。
4. 点击 Evidence 返回原始 GitHub Issue。
5. 查看 Release 前后变化。
6. 查看 Investigation Priority。
7. 查看 Action Brief。
8. 查看 AI Eval 结果与限制说明。

## 9. 开发方式
每轮开发前：
- 先读取 PRD/Architecture/Schema。
- 写一个 5-10 行 implementation plan。
- 小步提交。
- 不擅自扩 Scope。
- 若 Schema 必须改变，先更新文档和 migration。
- 每完成一阶段，运行 lint/typecheck/tests，并在 README 的进度部分更新。
