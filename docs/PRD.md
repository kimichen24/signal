# Signal — MVP PRD v0.2

## 1. 产品定位
Signal 是一个通用 AI Product Ops Intelligence System。Codex 只是第一个 Case Study，不是产品本身。

一句话：
> 将大规模非结构化用户反馈转换为 evidence-backed 的产品信号、调查优先级和下一步行动建议。

核心框架：
**Detect → Explain → Prioritize → Act**

## 2. 目标用户
第一 Persona：AI 产品运营 / 产品经理。

JTBD：
> 当我面对大量 AI 产品反馈时，我希望快速知道最近发生了什么变化、谁受到影响、哪些问题值得优先调查，并能追溯到原始证据。

## 3. 数据策略
第一数据源：`openai/codex` GitHub Issues。
开发样本：100 条。
正式 Demo：最近 30 天数千条公开真实 Issue。

不使用 AI 生成的“假反馈”。

## 4. MVP 页面

### 4.1 Overview — What Changed?
首页第一屏回答：**最近发生了什么变化？**

核心模块：
- Feedback analyzed
- Emerging Signals
- High-severity items
- Product areas
- What Changed This Week
- Emerging Signals
- Top Pain Points
- Platform / Surface distribution

Weekly Brief 只能基于底层统计结果生成，不允许模型自行编数字。

### 4.2 Feedback
字段：
- title
- created_at
- surface
- platform
- issue_type
- category
- subtopic
- severity
- state
- original URL

过滤：
- 7/14/30 days
- platform
- surface
- category
- severity
- issue_type

详情 Drawer：
- Original evidence
- AI summary
- surface/platform
- category/subtopic
- user scenario
- user impact
- AI-estimated severity
- confidence
- GitHub link

### 4.3 Insights
每个 Insight 必须包括：
- problem statement
- issue_count
- growth
- affected platform/surface
- user impact
- severity
- confidence
- representative evidence
- traceability to underlying issues

产品原则：
**No insight without evidence.**

### 4.4 Releases
目标：分析某次产品事件前后反馈结构变化。

比较窗口默认：
- Before: release_date - 7 days
- After: release_date + 7 days

输出：
- total feedback change
- new topics
- increased topics
- decreased topics
- affected platform/surface
- representative evidence

只允许表述：
> “X-related feedback increased after the release and is worth further investigation.”

不允许：
> “Release X caused the issue.”

### 4.5 Opportunities
定位：Investigation Priority，不是 Roadmap Priority。

每个 Opportunity：
- problem
- evidence_count
- growth
- segment
- AI-estimated severity
- transparent priority score
- reason
- recommended action
- product hypothesis
- suggested metrics

Action 类型：
- Investigate Now
- Validate
- Monitor
- Low Priority

## 5. Taxonomy
一级分类固定，二级 subtopic AI 动态发现：
- Reliability
- Performance
- Context & Memory
- Model Quality
- Tool Execution
- Git & Workspace
- App / UI / UX
- CLI
- IDE Integration
- Authentication & Account
- Usage & Credits
- MCP & Integrations
- Safety & Permissions
- Installation & Updates
- Onboarding & Documentation
- Other

## 6. Severity
必须显示 `AI-estimated Severity`。

- Critical: 系统/核心功能完全不可用、严重数据或安全风险
- High: 核心任务无法完成
- Medium: 明显影响体验但有 workaround
- Low: 轻微 UX / 非核心问题

## 7. Emerging Signal
基础逻辑：
`growth_rate = (current - previous) / max(previous, 1)`

必须有 minimum volume threshold，例如 current >= 5。

建议综合：
- volume
- growth
- severity

公式必须透明，可配置，不由 LLM 决定。

## 8. Investigation Priority
第一版建议：
- 30% Frequency
- 25% Severity
- 25% Growth
- 20% Engagement

每一项归一化到 0-100。
最终 score 0-100。
公式代码化、可测试、可解释。

## 9. Action Brief
高优先级 Signal 输出：
- Why it matters
- Investigate
- Validate
- Segment
- Monitor
- Suggested metrics

AI 可以写解释，但所引用数字必须来自数据库。

## 10. Traceability
必须实现：
Insight → Cluster → Cluster members → Original issue → GitHub URL

## 11. Eval
随机抽 100 条人工标注：
- category
- surface
- platform
- severity

目标（非硬上线门槛）：
- category accuracy ≥ 80%
- surface accuracy ≥ 90%
- platform accuracy ≥ 90%
- severity 用 Human-AI Agreement

同时做人工效率 baseline：
同样 100 条，比较人工整理 vs Signal pipeline。

禁止预设结果，必须真实记录。

## 12. MVP 非目标
- 多数据源
- 多租户
- 用户登录
- Agent chat
- 自动 roadmap
- 自动产品决策
- 实时监控
- 完整企业功能

## 13. Demo 成功标准
招聘方可以在 3-5 分钟内看懂：
1. Signal 不是 Codex 调研报告，而是可复用系统。
2. 数据是真实的。
3. AI 用在语义理解，不用在“编指标”。
4. 最近变化可被自动检测。
5. Release 影响只做相关性分析。
6. 每个结论有 Evidence。
7. 有人工 Eval 验证 AI。
