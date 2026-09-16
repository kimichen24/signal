import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { getOpportunitiesData } from "@/lib/data-adapter";
import { getClusterDisplayName } from "@/lib/cluster-labels";
import { CATEGORY, SEVERITY, ACTION } from "@/lib/labels";
import type { Opportunity } from "@/lib/supabase/queries";

export const metadata = { title: "机会" };

const ACTION_VARIANT: Record<
  string,
  "destructive" | "warning" | "secondary" | "outline"
> = {
  investigate_now: "destructive",
  validate: "warning",
  monitor: "secondary",
  low_priority: "outline",
};

function severityFromComponents(
  components: Record<string, number>
): string {
  const score = components.severity ?? 0;
  if (score >= 0.7) return SEVERITY.critical ?? "严重";
  if (score >= 0.5) return SEVERITY.high ?? "高";
  if (score >= 0.3) return SEVERITY.medium ?? "中";
  return SEVERITY.low ?? "低";
}

function ComponentBar({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-16 shrink-0 text-muted-foreground">{label}</span>
      <span className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-secondary">
        <span
          className="absolute inset-y-0 left-0 rounded-full bg-primary/40"
          style={{ width: `${Math.max(pct, 2)}%` }}
        />
      </span>
      <span className="w-8 shrink-0 text-right tabular-nums text-muted-foreground">
        {pct}
      </span>
    </div>
  );
}

function OpportunityRow({
  opportunity,
  rank,
}: {
  opportunity: Opportunity;
  rank?: number;
}) {
  const displayName = getClusterDisplayName({
    clusterKey: opportunity.clusterKey,
    name: opportunity.name,
  });
  const actionLabel = ACTION[opportunity.action] ?? opportunity.action;
  const actionVariant = ACTION_VARIANT[opportunity.action] ?? "outline";
  const category = CATEGORY[opportunity.category] ?? opportunity.category;
  const sev = severityFromComponents(opportunity.components);

  return (
    <div className="py-5 first:pt-0 last:pb-0">
      {/* Row 1: rank + name + status + score */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          {rank !== undefined ? (
            <span className="mt-0.5 shrink-0 text-sm font-semibold tabular-nums text-muted-foreground">
              {String(rank).padStart(2, "0")}
            </span>
          ) : null}
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground">
              {displayName}
            </p>
            <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
              <Badge variant={actionVariant}>{actionLabel}</Badge>
              {opportunity.isEmerging ? (
                <Badge variant="destructive">新兴</Badge>
              ) : null}
              {opportunity.needsRefinement ? (
                <Badge variant="warning">需细化</Badge>
              ) : null}
              <span className="text-xs text-muted-foreground">
                {category} · {opportunity.size} 条
              </span>
            </div>
          </div>
        </div>
        <span className="shrink-0 text-lg font-bold tabular-nums text-primary">
          {Math.round(opportunity.priority * 100)}
        </span>
      </div>

      {/* Row 2: problem statement */}
      {opportunity.brief?.what_changed ? (
        <p className="mt-2 pl-7 text-[13px] leading-6 text-muted-foreground">
          {opportunity.brief.what_changed}
        </p>
      ) : null}

      {/* Row 3: compact metadata */}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 pl-7 text-xs text-muted-foreground">
        <span className="tabular-nums">
          {opportunity.size} 条反馈
        </span>
        <span>AI 估算严重度：{sev}</span>
        {opportunity.trendState === "new_signal" ? (
          <span className="text-primary">新信号</span>
        ) : opportunity.trendState === "low_base_acceleration" ? (
          <span>低基数信号</span>
        ) : null}
        {!opportunity.engagementAvailable ? (
          <span>公开互动数据不足，已重新归一化</span>
        ) : null}
      </div>

      {/* Row 4: expandable priority explanation + evidence */}
      <div className="mt-3 pl-7">
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer hover:text-foreground">
            为什么得到这个优先级？
          </summary>
          <div className="mt-2 space-y-2">
            {Object.entries(opportunity.weights).map(([key]) => (
              <ComponentBar
                key={key}
                label={
                  key === "frequency"
                    ? "反馈频次"
                    : key === "severity"
                      ? "严重度"
                      : key === "signal"
                        ? "信号强度"
                        : key === "engagement"
                          ? "互动度"
                          : key
                }
                value={opportunity.components[key] ?? 0}
              />
            ))}
            {opportunity.trendState ? (
              <p className="text-muted-foreground">
                信号状态：{opportunity.trendState === "new_signal" ? "新信号" : opportunity.trendState === "low_base_acceleration" ? "低基数加速" : opportunity.trendState === "normal_growth" ? "正常增长" : opportunity.trendState}
                {opportunity.signalScore !== null
                  ? ` · 信号分 ${Math.round(opportunity.signalScore * 100)}%`
                  : ""}
              </p>
            ) : null}
            {opportunity.brief?.product_hypothesis ? (
              <p>
                <span className="font-medium text-foreground/80">
                  产品假设：{" "}
                </span>
                {opportunity.brief.product_hypothesis}
              </p>
            ) : null}
            {opportunity.brief?.recommended_investigation ? (
              <p>
                <span className="font-medium text-foreground/80">
                  建议调查：{" "}
                </span>
                {opportunity.brief.recommended_investigation}
              </p>
            ) : null}
          </div>
        </details>

        {/* Evidence + brief link */}
        <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
          {opportunity.representatives.slice(0, 3).map((ev) => (
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
          {opportunity.brief ? (
            <a
              href="/action-briefs"
              className="text-primary underline-offset-4 hover:underline"
            >
              查看行动简报 →
            </a>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/* ── Group by status ───────────────────────────────────────────── */

function StatusSection({
  title,
  opportunities,
  startRank,
}: {
  title: string;
  opportunities: Opportunity[];
  startRank: number;
}) {
  if (opportunities.length === 0) return null;
  return (
    <section>
      <h2 className="text-lg font-semibold tracking-tight text-foreground">
        {title}
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        {opportunities.length} 个机会
      </p>
      <div className="mt-4 divide-y divide-border">
        {opportunities.map((opp, i) => (
          <OpportunityRow
            key={opp.id}
            opportunity={opp}
            rank={startRank + i + 1}
          />
        ))}
      </div>
    </section>
  );
}

/* ── Page ──────────────────────────────────────────────────────── */

export default async function OpportunitiesPage() {
  const { configured, error, rows } = await getOpportunitiesData();

  /* Group by persisted action_type */
  const investigateNow = rows.filter((r) => r.action === "investigate_now");
  const validate = rows.filter((r) => r.action === "validate");
  const monitor = rows.filter((r) => r.action === "monitor");
  const lowPriority = rows.filter((r) => r.action === "low_priority");

  /* Top 3 by priority (first 3 from the query, already sorted) */
  const top3 = rows.slice(0, 3);

  return (
    <div className="space-y-12">
      {/* Header */}
      <header className="space-y-3">
        <p className="text-xs font-medium tracking-wide text-muted-foreground">
          机会
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          机会
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          结合反馈频次、AI 估算严重度、信号强度与公开互动度，识别当前最值得进一步调查的产品机会。
        </p>
        <p className="text-xs text-muted-foreground">
          调查优先级用于指导进一步验证，不代表官方产品路线图或 P0/P1。
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="数据库未配置"
          description="请配置 Supabase 连接以查看机会数据。"
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_ANON_KEY"
        />
      ) : error ? (
        <EmptyState
          title="数据库查询失败"
          description={`机会数据读取未成功，请检查配置后重试。(${error})`}
          hint="运行 python -m pipeline.opportunities 以填充本页"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="尚未计算机会"
          description="机会从生产问题簇计算得出，需先运行评分流水线。"
          hint="python -m pipeline.opportunities"
        />
      ) : (
        <>
          {/* Summary strip */}
          <section>
            <div className="flex flex-wrap items-baseline gap-x-8 gap-y-4 text-sm">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tabular-nums text-foreground">
                  {rows.length}
                </span>
                <span className="text-xs text-muted-foreground">产品机会</span>
              </div>
              <div className="hidden h-5 w-px bg-border sm:block" />
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tabular-nums text-destructive">
                  {investigateNow.length}
                </span>
                <span className="text-xs text-muted-foreground">立即调查</span>
              </div>
              <div className="hidden h-5 w-px bg-border sm:block" />
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tabular-nums text-foreground">
                  {validate.length}
                </span>
                <span className="text-xs text-muted-foreground">待验证</span>
              </div>
              <div className="hidden h-5 w-px bg-border sm:block" />
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tabular-nums text-foreground">
                  {monitor.length}
                </span>
                <span className="text-xs text-muted-foreground">持续观察</span>
              </div>
              <div className="hidden h-5 w-px bg-border sm:block" />
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tabular-nums text-muted-foreground">
                  {lowPriority.length}
                </span>
                <span className="text-xs text-muted-foreground">低优先级</span>
              </div>
            </div>
          </section>

          <hr className="border-border" />

          {/* Top 3 */}
          {top3.length > 0 ? (
            <section>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                最值得优先调查
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                按调查优先级排序的前三个产品机会。
              </p>
              <div className="mt-4 divide-y divide-border">
                {top3.map((opp, i) => (
                  <OpportunityRow key={opp.id} opportunity={opp} rank={i + 1} />
                ))}
              </div>
            </section>
          ) : null}

          <hr className="border-border" />

          {/* Status sections */}
          <StatusSection
            title="立即调查"
            opportunities={investigateNow}
            startRank={0}
          />
          <StatusSection
            title="待验证"
            opportunities={validate}
            startRank={investigateNow.length}
          />
          <StatusSection
            title="持续观察"
            opportunities={monitor}
            startRank={investigateNow.length + validate.length}
          />
          <StatusSection
            title="低优先级"
            opportunities={lowPriority}
            startRank={
              investigateNow.length +
              validate.length +
              monitor.length
            }
          />

          {/* Methodology disclosure */}
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">
              优先级计算说明
            </summary>
            <div className="mt-3 space-y-1 pl-4">
              <p>调查优先级权重：频次 30% · 严重度 25% · 信号强度 25% · 互动度 20%</p>
              <p>调查优先级 ≠ 官方路线图优先级</p>
              <p>公开互动数据不足时，按可用信号重新归一化。</p>
              <p>状态判定：确定性规则映射，非 AI 生成。</p>
              <p>
                数据集：codex-14d-2026-09-06 · 仅真实 GitHub Issues（PR 已过滤）。
              </p>
            </div>
          </details>
        </>
      )}
    </div>
  );
}
