# Data Provenance & Limitations（数据来源与局限）

Signal 的产品价值建立在"可解释、可验证"之上。本页是系统的诚实性清单：
每一项都是刻意的设计决策或已知局限，而非缺陷。

## 数据来源与可复现性

| 层 | 机制 |
| --- | --- |
| 数据集成员 | `datasets` 注册表：同一 `dataset_id` 永远解析到同一 `[start_at, snapshot_at)` 创建时间窗口（GitHub `created_at`，非 updated_at） |
| 原始内容 | `body_raw` / `source_payload` 在摄入时永久保存；清洗只产生 `body_clean` |
| 分析输入 | `analysis_input_hash`（sha256）= 发送给分类器的精确规范化 payload；上游 GitHub 编辑无法悄悄改变旧分析对应的输入 |
| 聚类成员 | 确定性（输入序固定 + BLAS 单线程）；`clustering_params` 记录算法/阈值/最小值，同配置重跑即复现 |
| 趋势窗口 | `analysis_runs` 记录每次运行的 `start_date`/`snapshot_at`；显示一律锚定数据集定义而非墙钟 |

## 已声明的局限

1. **100 条开发集分析无 input hash（legacy）**
   这批分析早于 hash 列存在，且其源行在 14 天重摄入时被上游现状覆盖——
   无法保证精确重建当时的分类输入。原行保留，标记 legacy，不做回填。
2. **趋势覆盖守卫**
   周期数据量 < 阈值（每期 10 条）或窗口未覆盖周期时，系统返回
   `insufficient_history` 而非编造 "+100%"。零基线（previous=0） growth
   恒为 null，永不显示 "+∞%"。
3. **低基线增长**
   previous ∈ {1,2} 的簇可计算数学增长率，但必须带低基线警示，且不得以
   原始增长率作为主要排序驱动。
4. **Emerging score 未含货币成本**
   不假设 MiMo/OpenAI 定价，审计只报告真实 token 计数。
5. **Engagement 仅限公开 GitHub 字段**
   `comments_count + reactions_count`。无内部浏览/会话/收入数据——系统
   不会假装存在。稀疏时透明重归一化权重并展示局限说明。
6. **相关性 ≠ 因果**
   Release Impact 措辞固定为"X 相关反馈在 Y 发布后增加，值得调查"。
   覆盖不足（任一侧 < 5 天）即 `insufficient_history`。
7. **needs_refinement 宽簇**
   ≥15 成员的簇被标记为宽问题族：简报推荐 family 级调查并显式保留不确
   定性，不伪装成单一精确痛点。
8. **scope/严格排除**
   out_of_scope（158/2254）永久保留于数据库，但默认排除于聚类、趋势、
   优先级之外（DECISIONS #16）。
9. **分类 = AI-estimated**
   所有 severity/scope/category 均为 AI 估计并标注；20 条人工盲评校准
   severity 后（严格一致率 55%→75%）rubric 冻结；Eval 扩展至更多样本
   属于 Prompt 05。
