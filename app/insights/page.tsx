import { EmptyState } from "@/components/empty-state";
import {
  getInsights,
  getClusterInsightCounts,
} from "@/lib/supabase/queries";
import { CATEGORY, SEVERITY } from "@/lib/labels";
import type { Insight } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "洞察" };

function severityLabel(score: number | null): string {
  if (score === null) return "—";
  if (score >= 3.5) return SEVERITY.critical ?? "严重";
  if (score >= 2.5) return SEVERITY.high ?? "高";
  if (score >= 1.5) return SEVERITY.medium ?? "中";
  return SEVERITY.low ?? "低";
}

/* ── Chinese presentation copy for known top clusters ──────────── */
const CLUSTER_CN: Record<string, { name: string; statement: string }> = {
  "Windows desktop app crashes and unexpected exits": {
    name: "Windows 桌面端崩溃与意外退出",
    statement:
      "Windows 桌面应用在常见使用场景中频繁发生不可预测的崩溃或退出，打断用户工作流。",
  },
  "Paginated thread history projection inconsistencies": {
    name: "分页会话历史记录显示异常",
    statement:
      "分页会话历史无法持久、正确地展示所有已完成对话轮次，导致用户看到不完整或过时的记录。",
  },
  "MCP extension lifecycle and server management issues": {
    name: "MCP 扩展生命周期与服务管理问题",
    statement:
      "MCP 扩展在启动、连接和关闭过程中存在稳定性问题，影响工具集成和扩展功能的正常使用。",
  },
  "CLI tool execution timeouts and exit code inconsistencies": {
    name: "CLI 工具执行超时与退出码异常",
    statement:
      "CLI 执行命令时频繁超时，且退出码不一致，导致自动化脚本和 CI/CD 流程可靠性下降。",
  },
};

/* ── Insight row component ─────────────────────────────────────── */

function InsightRow({ insight, rank }: { insight: Insight; rank: number }) {
  const cn = CLUSTER_CN[insight.name];
  const category = CATEGORY[insight.category] ?? insight.category;
  const sev = severityLabel(insight.avgSeverityScore);

  /* Display persisted growth_rate with explicit label.
     growth_rate is stored as a decimal (e.g. 0.35 = 35%). */
  const growthPct =
    insight.growthRate !== null
      ? Math.round(insight.growthRate * 100)
      : null;
  const growthColor =
    growthPct !== null && growthPct > 5
      ? "text-primary"
      : growthPct !== null && growthPct < -5
        ? "text-destructive"
        : "text-muted-foreground";

  return (
    <div className="py-5 first:pt-0 last:pb-0">
      {/* Row 1: rank + name + badges + growth */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <span className="mt-0.5 shrink-0 text-sm font-semibold tabular-nums text-muted-foreground">
            {String(rank).padStart(2, "0")}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground">
              {cn?.name ?? insight.name}
            </p>
            <span className="mt-0.5 text-xs text-muted-foreground">
              {category} · {insight.issueCount} 条反馈
            </span>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {insight.isEmerging ? (
            <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[11px] font-medium text-primary">
              新兴
            </span>
          ) : null}
          {insight.needsRefinement ? (
            <span className="rounded bg-warning/15 px-1.5 py-0.5 text-[11px] font-medium text-warning">
              需细化
            </span>
          ) : null}
          {growthPct !== null ? (
            <span className={`text-sm font-medium tabular-nums ${growthColor}`}>
              {growthPct > 0 ? "↑" : growthPct < 0 ? "↓" : "→"}{" "}
              {growthPct > 0 ? "+" : ""}
              {growthPct}%
            </span>
          ) : null}
        </div>
      </div>

      {/* Row 2: problem statement */}
      <p className="mt-2 pl-7 text-[13px] leading-6 text-muted-foreground">
        {cn?.statement ?? insight.problemStatement ?? insight.summary ?? ""}
      </p>

      {/* Row 3: metadata */}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 pl-7 text-xs text-muted-foreground">
        {insight.previousPeriodCount !== null ||
        insight.currentPeriodCount !== null ? (
          <span className="tabular-nums">
            上一周期 {insight.previousPeriodCount ?? 0} · 当前周期{" "}
            {insight.currentPeriodCount ?? 0}
          </span>
        ) : null}
        <span>AI 估算严重度：{sev}</span>
        {growthPct !== null ? (
          <span>增长率 {growthPct}%</span>
        ) : null}
      </div>

      {/* Row 4: evidence */}
      {insight.representatives.length > 0 ? (
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 pl-7 text-xs">
          {insight.representatives.slice(0, 3).map((ev) => (
            <a
              key={ev.issueNumber}
              href={ev.githubUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary underline-offset-4 hover:underline"
            >
              #{ev.issueNumber}
            </a>
          ))}
          {insight.representatives.length > 3 ? (
            <span className="text-muted-foreground">
              共 {insight.representatives.length} 条证据
            </span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

/* ── Page ───────────────────────────────────────────────────────── */

export default async function InsightsPage() {
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const { configured, error, rows } = await getInsights(version, 50);
  const counts = configured ? await getClusterInsightCounts(version) : null;

  /* Grouping by existing stored states:
     1. 新兴信号: isEmerging, sorted by emergingScore desc (frozen Prompt 04 ranking)
     2. 需进一步细化: needsRefinement && !isEmerging, sorted by issueCount desc
     3. 其他问题簇: remaining, sorted by issueCount desc */
  const emerging = rows
    .filter((r) => r.isEmerging)
    .sort((a, b) => (b.emergingScore ?? 0) - (a.emergingScore ?? 0));
  const needsRefinement = rows
    .filter((r) => r.needsRefinement && !r.isEmerging)
    .sort((a, b) => b.issueCount - a.issueCount);
  const other = rows
    .filter((r) => !r.isEmerging && !r.needsRefinement)
    .sort((a, b) => b.issueCount - a.issueCount);

  const totalClusters = counts?.counts?.total ?? null;
  const emergingCount = counts?.counts?.emerging ?? null;
  const refinementCount = counts?.counts?.needsRefinement ?? null;

  return (
    <div className="space-y-12">
      {/* Header */}
      <header className="space-y-3">
        <p className="text-xs font-medium tracking-wide text-muted-foreground">
          洞察
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          洞察
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          从重复反馈中识别正在形成的问题模式、变化信号与代表性证据。
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="数据库未配置"
          description="请配置 Supabase 连接以查看洞察数据。"
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_ANON_KEY"
        />
      ) : error ? (
        <EmptyState
          title="数据库查询失败"
          description={`洞察数据读取未成功，请检查配置后重试。(${error})`}
          hint="在 Supabase 项目中执行 supabase/schema.sql"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="尚未生成洞察"
          description="问题簇由确定性语义聚类在已完成结构化分析的有效反馈上构建。请先运行聚类流水线。"
          hint="python -m pipeline.cluster_issues"
        />
      ) : (
        <>
          {/* Metric strip — full-production counts, not page-limited */}
          <section>
            <div className="flex flex-wrap items-baseline gap-x-8 gap-y-4 text-sm sm:gap-x-12">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tabular-nums text-primary">
                  {emergingCount ?? "—"}
                </span>
                <span className="text-xs text-muted-foreground">新兴信号</span>
              </div>
              <div className="hidden h-5 w-px bg-border sm:block" />
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tabular-nums text-foreground">
                  {totalClusters ?? "—"}
                </span>
                <span className="text-xs text-muted-foreground">问题簇</span>
              </div>
              <div className="hidden h-5 w-px bg-border sm:block" />
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tabular-nums text-foreground">
                  {refinementCount ?? "—"}
                </span>
                <span className="text-xs text-muted-foreground">
                  需进一步细化
                </span>
              </div>
            </div>
          </section>

          <hr className="border-border" />

          {/* 新兴信号 — sorted by frozen emergingScore (Prompt 04) */}
          {emerging.length > 0 ? (
            <section>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                新兴信号
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                按 Emerging 评分排序的新兴问题簇。
              </p>
              <div className="mt-4 divide-y divide-border">
                {emerging.map((insight, i) => (
                  <InsightRow key={insight.id} insight={insight} rank={i + 1} />
                ))}
              </div>
            </section>
          ) : null}

          {/* 需进一步细化 — existing stored needs_refinement state */}
          {needsRefinement.length > 0 ? (
            <section>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                需进一步细化
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                覆盖范围较广、建议进一步细化的问题簇。
              </p>
              <div className="mt-4 divide-y divide-border">
                {needsRefinement.map((insight, i) => (
                  <InsightRow key={insight.id} insight={insight} rank={i + 1} />
                ))}
              </div>
            </section>
          ) : null}

          {/* 其他问题簇 */}
          {other.length > 0 ? (
            <section>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                其他问题簇
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                按反馈量排序的其余问题簇。
              </p>
              <div className="mt-4 divide-y divide-border">
                {other.map((insight, i) => (
                  <InsightRow key={insight.id} insight={insight} rank={i + 1} />
                ))}
              </div>
            </section>
          ) : null}

          {/* Methodology disclosure */}
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">
              方法说明
            </summary>
            <div className="mt-3 space-y-1 pl-4">
              <p>分析版本：{version}</p>
              <p>
                聚类算法：确定性语义聚类 · distance_threshold=0.45
              </p>
              <p>
                新兴信号判定：Emerging 评分框架（7天窗口增长率 ≥ 50% 且最小观测量 5
                条）
              </p>
              <p>增长率为存储的持久化值，非 UI 计算。</p>
              <p>
                数据集：codex-14d-2026-09-06 · 仅真实 GitHub Issues（PR 已过滤）
              </p>
            </div>
          </details>
        </>
      )}
    </div>
  );
}
