import Link from "next/link";
import {
  getDataSummary,
  getDistributions,
  getEntityCount,
  getOpportunities,
} from "@/lib/supabase/queries";
import { CATEGORY, SURFACE, SEVERITY, ACTION } from "@/lib/labels";
import { getClusterDisplayName } from "@/lib/cluster-labels";

export const dynamic = "force-dynamic";

export const metadata = { title: "总览" };

function formatNumber(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("zh-CN");
}

function trendArrow(
  current: number,
  previous: number
): { arrow: string; pct: string; color: string } {
  if (previous === 0 && current === 0)
    return { arrow: "—", pct: "0%", color: "text-muted-foreground" };
  if (previous === 0)
    return { arrow: "↑", pct: "新增", color: "text-primary" };
  const change = Math.round(((current - previous) / previous) * 100);
  if (change > 5)
    return { arrow: "↑", pct: `+${change}%`, color: "text-primary" };
  if (change < -5)
    return { arrow: "↓", pct: `${change}%`, color: "text-destructive" };
  return {
    arrow: "→",
    pct: `${change > 0 ? "+" : ""}${change}%`,
    color: "text-muted-foreground",
  };
}

function severityLabel(score: number | null): string {
  if (score === null) return "—";
  if (score >= 3.5) return SEVERITY.critical ?? "严重";
  if (score >= 2.5) return SEVERITY.high ?? "高";
  if (score >= 1.5) return SEVERITY.medium ?? "中";
  return SEVERITY.low ?? "低";
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
  const opportunities = hasData ? await getOpportunities(version, 50) : null;
  const clusterCount = hasData
    ? await getEntityCount("clusters", version)
    : null;
  const opportunityCount = hasData
    ? await getEntityCount("opportunities")
    : null;

  const top3 = (opportunities?.rows ?? []).slice(0, 3);

  const topSurfaces = (distributions?.data?.surface ?? []).slice(0, 5);
  const topCategories = (distributions?.data?.category ?? []).slice(0, 5);

  return (
    <div className="space-y-16">
      {/* ── Hero ──────────────────────────────────────────────────── */}
      <section className="max-w-2xl">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Signal
        </h1>
        <p className="mt-1 text-lg font-medium text-muted-foreground">
          AI 产品运营智能系统
        </p>
        <p className="mt-4 text-[15px] leading-7 text-muted-foreground">
          从真实 {caseStudy} 用户反馈中发现正在出现的问题、识别变化信号，并将证据转化为可执行的产品运营机会。
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Link
            href="/insights"
            className="inline-flex h-9 items-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
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
          14 个完整日历日 · {caseStudy} · 真实 GitHub Issues
        </p>
      </section>

      {/* ── Metric Strip ──────────────────────────────────────────── */}
      {hasData ? (
        <section>
          <div className="flex flex-wrap items-baseline gap-x-8 gap-y-4 text-sm sm:gap-x-12">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular-nums text-foreground">
                {formatNumber(summary.totalIssues)}
              </span>
              <span className="text-xs text-muted-foreground">真实反馈</span>
            </div>
            <div className="hidden h-5 w-px bg-border sm:block" />
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular-nums text-foreground">
                {formatNumber(distributions?.data?.inScopeTotal ?? null)}
              </span>
              <span className="text-xs text-muted-foreground">有效反馈</span>
            </div>
            <div className="hidden h-5 w-px bg-border sm:block" />
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular-nums text-foreground">
                {formatNumber(clusterCount?.count ?? null)}
              </span>
              <span className="text-xs text-muted-foreground">问题簇</span>
            </div>
            <div className="hidden h-5 w-px bg-border sm:block" />
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular-nums text-foreground">
                {formatNumber(opportunityCount?.count ?? null)}
              </span>
              <span className="text-xs text-muted-foreground">产品机会</span>
            </div>
          </div>
        </section>
      ) : null}

      {/* ── Divider ───────────────────────────────────────────────── */}
      <hr className="border-border" />

      {/* ── Top 3 Signals ─────────────────────────────────────────── */}
      {top3.length > 0 ? (
        <section>
          <h2 className="text-lg font-semibold tracking-tight text-foreground">
            现在最值得关注什么？
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            按调查优先级排序的前三个产品机会。
          </p>
          <div className="mt-6 divide-y divide-border">
            {top3.map((opp, index) => {
              const displayName = getClusterDisplayName({ clusterKey: opp.clusterKey, name: opp.name });
              const trend = trendArrow(opp.current, opp.previous);
              const displayCategory =
                CATEGORY[opp.category] ?? opp.category;
              const actionLabel = ACTION[opp.action] ?? opp.action;

              return (
                <div key={opp.id} className="py-5 first:pt-0 last:pb-0">
                  {/* Row 1: rank + name + priority + trend */}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex min-w-0 items-start gap-3">
                      <span className="mt-0.5 shrink-0 text-sm font-semibold tabular-nums text-muted-foreground">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-foreground">
                          {displayName}
                        </p>
                        <span className="mt-0.5 inline-block rounded bg-secondary px-1.5 py-0.5 text-[11px] text-muted-foreground">
                          {displayCategory} · {opp.size} 条 · {actionLabel}
                        </span>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className="text-sm font-semibold tabular-nums text-foreground">
                        {Math.round(opp.priority * 100)}
                      </span>
                      <span className={`text-sm font-medium tabular-nums ${trend.color}`}>
                        {trend.arrow} {trend.pct}
                      </span>
                    </div>
                  </div>

                  {/* Row 2: problem statement */}
                  <p className="mt-2 pl-7 text-[13px] leading-6 text-muted-foreground">
                    {opp.brief?.what_changed ?? ""}
                  </p>

                  {/* Row 3: metadata + evidence link */}
                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 pl-7 text-xs text-muted-foreground">
                    <span className="tabular-nums">
                      上一周期 {opp.previous} · 当前周期 {opp.current}
                    </span>
                    {opp.components.severity !== undefined ? (
                      <span>
                        AI 估算严重度：
                        {severityLabel(opp.components.severity)}
                      </span>
                    ) : null}
                    {opp.representatives.length > 0 ? (
                      <Link
                        href={opp.representatives[0].githubUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary underline-offset-4 hover:underline"
                      >
                        查看原始证据 →
                      </Link>
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4">
            <Link
              href="/opportunities"
              className="text-sm text-primary underline-offset-4 hover:underline"
            >
              查看全部 {opportunityCount?.count ?? 0} 个产品机会 →
            </Link>
          </div>
        </section>
      ) : null}

      {/* ── Feedback Structure ────────────────────────────────────── */}
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

      {/* ── How It Works ──────────────────────────────────────────── */}
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

      {/* ── Methodology Disclosure ────────────────────────────────── */}
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

      {/* ── Empty state ───────────────────────────────────────────── */}
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
