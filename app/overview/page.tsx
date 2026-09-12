import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/stat-card";
import {
  getDataSummary,
  getDistributions,
  getInsights,
  getTrendStatus,
} from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "总览" };

function formatNumber(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("zh-CN");
}

function DistributionList({
  title,
  slices,
}: {
  title: string;
  slices: { label: string; count: number; pct: number }[];
}) {
  const top = slices.slice(0, 6);
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <ul className="mt-2 space-y-1 text-xs">
        {top.map((slice) => (
          <li key={slice.label} className="flex items-center gap-2">
            <span className="w-40 truncate">{slice.label}</span>
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
              <span
                className="block h-full rounded-full bg-foreground/60"
                style={{ width: `${slice.pct}%` }}
              />
            </span>
            <span className="w-16 text-right tabular-nums text-muted-foreground">
              {slice.count}（{slice.pct}%）
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default async function OverviewPage() {
  const caseStudy = process.env.NEXT_PUBLIC_CASE_STUDY ?? "OpenAI Codex";
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const summary = await getDataSummary();
  const hasData =
    summary.configured &&
    summary.error === null &&
    (summary.totalIssues ?? 0) > 0;

  const distributions = hasData ? await getDistributions(version) : null;
  const topClusters = hasData ? await getInsights(version, 5) : null;
  const trend = hasData ? await getTrendStatus(version) : null;

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          总览
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          最近发生了什么？
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          {caseStudy} 案例的用户反馈最新变化趋势。本页所有数字均来自真实采集
          的 GitHub Issues，Signal 不生成或模拟任何反馈数据。
        </p>
      </header>

      {!summary.configured ? (
        <EmptyState
          title="数据库未配置"
          description="Signal 从 Supabase 读取全部数据。请从 .env.example 创建 .env.local，填入 Supabase URL 和 anon key，然后在项目中执行 supabase/schema.sql。"
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_ANON_KEY"
        />
      ) : summary.error ? (
        <EmptyState
          title="数据库查询失败"
          description={`已尝试读取数据库但查询未成功。请检查配置或 Schema 后重试。(${summary.error})`}
          hint="在 Supabase 项目中执行 supabase/schema.sql"
        />
      ) : !hasData ? (
        <EmptyState
          title="尚未导入反馈数据"
          description="管道尚未采集任何 GitHub Issues。完成数据采集和 AI 分析（Prompts 01–02）后，本页将展示基于真实数据的反馈量、新兴信号和高严重度条目。"
          hint="prompts/01_DATA_INGESTION.md"
        />
      ) : (
        <>
          <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              label="已采集 Issues"
              value={formatNumber(summary.totalIssues)}
              hint="真实 GitHub Issues（已过滤 PR）"
            />
            <StatCard
              label="结构化分析"
              value={formatNumber(summary.analyzedIssues)}
              hint={`分析版本 ${version}`}
            />
            <StatCard
              label="有效反馈"
              value={formatNumber(distributions?.data?.inScopeTotal ?? null)}
              hint="核心 + 邻接"
            />
            <StatCard
              label="高严重度条目"
              value={formatNumber(summary.highSeverityIssues)}
              hint="AI 估算严重度：高 / 严重"
            />
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-medium">本周变化</h2>
            {trend?.status &&
            trend.status.state === "insufficient_history" ? (
              <div className="rounded-lg border border-dashed p-5">
                <p className="text-sm font-medium">
                  历史数据不足，暂无法计算可靠的周环比变化。
                </p>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">
                  当前开发数据集最早覆盖{" "}
                  {trend.status.earliestObservation?.slice(0, 10) ?? "—"}，
                  上一周期仅有 {trend.status.previousPeriod.count} 条观测
                  （最少需要 10 条）。Signal 不会基于缺失基线编造增长百分比。
                </p>
              </div>
            ) : trend?.status ? (
              <p className="text-sm text-muted-foreground">
                当前周期 {trend.status.currentPeriod.count} 条观测；上一周期{" "}
                {trend.status.previousPeriod.count} 条。符合新兴信号阈值
                的条目已在洞察页标注。
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">
                趋势状态不可用。
              </p>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-medium">核心痛点问题簇</h2>
            {topClusters && topClusters.rows.length > 0 ? (
              <ul className="space-y-2">
                {topClusters.rows.map((cluster) => (
                  <li
                    key={cluster.id}
                    className="flex items-center justify-between gap-4 rounded-lg border px-4 py-3 text-sm"
                  >
                    <span className="min-w-0 truncate">
                      {cluster.name}
                      <span className="ml-2 text-xs text-muted-foreground">
                        {cluster.category}
                      </span>
                    </span>
                    <span className="shrink-0 tabular-nums text-muted-foreground">
                      {cluster.issueCount} 条
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                尚未生成问题簇——请运行{" "}
                <code className="font-mono text-xs">
                  python -m pipeline.cluster_issues
                </code>
                。
              </p>
            )}
          </section>

          {distributions?.data ? (
            <section className="space-y-4">
              <h2 className="text-sm font-medium">有效反馈分布</h2>
              <div className="grid gap-6 md:grid-cols-3">
                <DistributionList
                  title="使用端"
                  slices={distributions.data.surface}
                />
                <DistributionList
                  title="平台"
                  slices={distributions.data.platform}
                />
                <DistributionList
                  title="问题类别"
                  slices={distributions.data.category}
                />
              </div>
            </section>
          ) : null}

          {summary.latestIssueAt ? (
            <p className="text-xs text-muted-foreground">
              最新采集 Issue：{summary.latestIssueAt.slice(0, 10)}
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}
