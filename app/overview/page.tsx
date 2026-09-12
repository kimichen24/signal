import Link from "next/link";
import {
  getDataSummary,
  getDistributions,
  getEntityCount,
  getInsights,
} from "@/lib/supabase/queries";
import { CATEGORY, SURFACE } from "@/lib/labels";

export const dynamic = "force-dynamic";

export const metadata = { title: "总览" };

function formatNumber(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("zh-CN");
}

function trendDirection(
  current: number,
  previous: number
): { arrow: string; pct: string; color: string } {
  if (previous === 0 && current === 0)
    return { arrow: "—", pct: "0%", color: "text-muted-foreground" };
  if (previous === 0)
    return { arrow: "↑", pct: "新增", color: "text-foreground" };
  const change = Math.round(((current - previous) / previous) * 100);
  if (change > 5)
    return { arrow: "↑", pct: `+${change}%`, color: "text-foreground" };
  if (change < -5)
    return { arrow: "↓", pct: `${change}%`, color: "text-destructive" };
  return { arrow: "→", pct: `${change > 0 ? "+" : ""}${change}%`, color: "text-muted-foreground" };
}

function severityInfo(score: number | null): { label: string; color: string } {
  if (score === null) return { label: "—", color: "text-muted-foreground" };
  if (score >= 3.5) return { label: "严重", color: "text-destructive" };
  if (score >= 2.5) return { label: "高", color: "text-foreground" };
  if (score >= 1.5) return { label: "中", color: "text-muted-foreground" };
  return { label: "低", color: "text-muted-foreground" };
}

export default async function OverviewPage() {
  const caseStudy = process.env.NEXT_PUBLIC_CASE_STUDY ?? "OpenAI Codex";
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";

  const summary = await getDataSummary(version);
  const hasData =
    summary.configured &&
    summary.error === null &&
    (summary.totalIssues ?? 0) > 0;

  const distributions = hasData ? await getDistributions(version) : null;
  const topClusters = hasData ? await getInsights(version, 20) : null;
  const clusterCount = hasData ? await getEntityCount("clusters", version) : null;
  const opportunityCount = hasData ? await getEntityCount("opportunities") : null;

  const top3 = (topClusters?.rows ?? [])
    .slice(0, 3)
    .map((c) => ({
      id: c.id,
      name: c.name,
      category: c.category,
      issueCount: c.issueCount,
      problemStatement: c.problemStatement,
      isEmerging: c.isEmerging,
      growthRate: c.growthRate,
      currentPeriodCount: c.currentPeriodCount,
      previousPeriodCount: c.previousPeriodCount,
      avgSeverityScore: c.avgSeverityScore,
    }));

  const topSurfaces = (distributions?.data?.surface ?? []).slice(0, 5);
  const topCategories = (distributions?.data?.category ?? []).slice(0, 5);

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section className="max-w-2xl">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {caseStudy === "OpenAI Codex" ? "Signal" : "Signal"} · AI
          产品运营智能系统
        </h1>
        <p className="mt-4 text-[15px] leading-7 text-muted-foreground">
          从 {formatNumber(summary.totalIssues)} 条真实 {caseStudy}{" "}
          用户反馈中，发现正在出现的问题、识别变化信号，并将证据转化为可执行的产品运营机会。
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Link
            href="/insights"
            className="inline-flex h-9 items-center rounded-md bg-foreground px-4 text-sm font-medium text-background transition-colors hover:bg-foreground/90"
          >
            查看关键洞察
          </Link>
          <Link
            href="/opportunities"
            className="inline-flex h-9 items-center rounded-md border border-border px-4 text-sm font-medium text-foreground transition-colors hover:bg-secondary"
          >
            查看产品机会
          </Link>
        </div>
        <p className="mt-4 text-xs text-muted-foreground">
          14 个完整日历日 · 真实 GitHub Issues
        </p>
      </section>

      {/* Metric Strip */}
      {hasData ? (
        <section>
          <div className="flex flex-wrap gap-x-10 gap-y-4 text-sm">
            <div>
              <span className="font-semibold tabular-nums text-foreground">
                {formatNumber(summary.totalIssues)}
              </span>
              <span className="ml-1.5 text-muted-foreground">真实反馈</span>
            </div>
            <div>
              <span className="font-semibold tabular-nums text-foreground">
                {formatNumber(distributions?.data?.inScopeTotal ?? null)}
              </span>
              <span className="ml-1.5 text-muted-foreground">有效反馈</span>
            </div>
            <div>
              <span className="font-semibold tabular-nums text-foreground">
                {formatNumber(clusterCount?.count ?? null)}
              </span>
              <span className="ml-1.5 text-muted-foreground">问题簇</span>
            </div>
            <div>
              <span className="font-semibold tabular-nums text-foreground">
                {formatNumber(opportunityCount?.count ?? null)}
              </span>
              <span className="ml-1.5 text-muted-foreground">产品机会</span>
            </div>
          </div>
        </section>
      ) : null}

      {/* Divider */}
      <hr className="border-border" />

      {/* Top Signals */}
      {top3.length > 0 ? (
        <section>
          <h2 className="text-lg font-semibold tracking-tight text-foreground">
            现在最值得关注什么？
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            基于反馈频次、严重度和趋势信号，当前最值得优先调查的问题簇。
          </p>
          <div className="mt-6 space-y-1">
            {top3.map((signal, index) => {
              const trend = trendDirection(
                signal.currentPeriodCount ?? 0,
                signal.previousPeriodCount ?? 0
              );
              const sev = severityInfo(signal.avgSeverityScore);
              return (
                <div
                  key={signal.id}
                  className="flex flex-col gap-3 rounded-lg border border-border px-5 py-4 sm:flex-row sm:items-start sm:justify-between"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs tabular-nums text-muted-foreground">
                        {index + 1}.
                      </span>
                      <span className="text-sm font-medium text-foreground">
                        {signal.name}
                      </span>
                      <span className="rounded bg-secondary px-1.5 py-0.5 text-[11px] text-muted-foreground">
                        {CATEGORY[signal.category] ?? signal.category}
                      </span>
                      {signal.isEmerging ? (
                        <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[11px] font-medium text-primary">
                          新兴
                        </span>
                      ) : null}
                    </div>
                    {signal.problemStatement ? (
                      <p className="mt-1.5 text-[13px] leading-6 text-muted-foreground">
                        {signal.problemStatement}
                      </p>
                    ) : null}
                    <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                      <span>
                        {signal.issueCount} 条反馈
                      </span>
                      <span className={sev.color}>
                        严重度 {sev.label}
                      </span>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2 text-sm sm:flex-col sm:items-end sm:gap-1">
                    <span className={`font-medium tabular-nums ${trend.color}`}>
                      {trend.arrow} {trend.pct}
                    </span>
                    <span className="text-xs tabular-nums text-muted-foreground">
                      {signal.currentPeriodCount ?? 0} vs{" "}
                      {signal.previousPeriodCount ?? 0}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4">
            <Link
              href="/insights"
              className="text-sm text-primary underline-offset-4 hover:underline"
            >
              查看全部 {topClusters?.rows.length ?? 0} 个洞察 →
            </Link>
          </div>
        </section>
      ) : null}

      {/* Feedback Structure */}
      {distributions?.data ? (
        <section>
          <h2 className="text-lg font-semibold tracking-tight text-foreground">
            反馈结构
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {formatNumber(distributions.data.inScopeTotal)} 条有效反馈的分布。
          </p>
          <div className="mt-6 grid gap-8 md:grid-cols-2">
            <div>
              <p className="mb-3 text-xs font-medium tracking-wide text-muted-foreground">
                使用端
              </p>
              <div className="space-y-2">
                {topSurfaces.map((slice) => (
                  <div
                    key={slice.label}
                    className="flex items-center gap-3 text-sm"
                  >
                    <span className="w-20 shrink-0 truncate text-muted-foreground">
                      {SURFACE[slice.label] ?? slice.label}
                    </span>
                    <span className="relative h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                      <span
                        className="absolute inset-y-0 left-0 rounded-full bg-foreground/20"
                        style={{ width: `${Math.max(slice.pct, 2)}%` }}
                      />
                    </span>
                    <span className="w-16 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                      {slice.count}（{slice.pct}%）
                    </span>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <p className="mb-3 text-xs font-medium tracking-wide text-muted-foreground">
                问题类别
              </p>
              <div className="space-y-2">
                {topCategories.map((slice) => (
                  <div
                    key={slice.label}
                    className="flex items-center gap-3 text-sm"
                  >
                    <span className="w-24 shrink-0 truncate text-muted-foreground">
                      {CATEGORY[slice.label] ?? slice.label}
                    </span>
                    <span className="relative h-2 flex-1 overflow-hidden rounded-full bg-secondary">
                      <span
                        className="absolute inset-y-0 left-0 rounded-full bg-foreground/20"
                        style={{ width: `${Math.max(slice.pct, 2)}%` }}
                      />
                    </span>
                    <span className="w-16 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
                      {slice.count}（{slice.pct}%）
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      ) : null}

      {/* How It Works */}
      <section>
        <h2 className="text-lg font-semibold tracking-tight text-foreground">
          Signal 如何工作
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          从原始反馈到可执行建议的四步流程。
        </p>
        <div className="mt-6 flex flex-wrap items-start gap-3 text-sm">
          <div className="rounded-lg border border-border px-4 py-3">
            <p className="font-medium text-foreground">发现</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              从 GitHub Issues 采集真实用户反馈
            </p>
          </div>
          <span className="self-center text-muted-foreground">→</span>
          <div className="rounded-lg border border-border px-4 py-3">
            <p className="font-medium text-foreground">解释</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              AI 结构化分析类别、严重度、场景
            </p>
          </div>
          <span className="self-center text-muted-foreground">→</span>
          <div className="rounded-lg border border-border px-4 py-3">
            <p className="font-medium text-foreground">排序</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              确定性评分计算调查优先级
            </p>
          </div>
          <span className="self-center text-muted-foreground">→</span>
          <div className="rounded-lg border border-border px-4 py-3">
            <p className="font-medium text-foreground">行动</p>
            <p className="mt-0.5 text-xs text-muted-foreground">
              生成基于证据的行动简报
            </p>
          </div>
        </div>
      </section>

      {/* Methodology Disclosure */}
      {hasData ? (
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
              机会评分权重：频次 30% · 严重度 25% · 信号强度 25% · 互动度 20%
            </p>
            <p>
              趋势窗口：最近 7 天 vs 前 7 天 · 最小观测量 10 条
            </p>
            <p>
              数据集：codex-14d-2026-09-06 · 14 个完整日历日 · 仅真实 GitHub
              Issues（PR 已过滤）
            </p>
          </div>
        </details>
      ) : null}

      {/* Empty state */}
      {!hasData ? (
        <div className="rounded-lg border border-dashed border-border p-10 text-center">
          <h2 className="text-sm font-medium text-foreground">
            数据库未配置
          </h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted-foreground">
            请配置 Supabase 连接以查看数据。
          </p>
        </div>
      ) : null}
    </div>
  );
}
