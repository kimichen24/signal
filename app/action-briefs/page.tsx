import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { getOpportunities } from "@/lib/supabase/queries";
import { getClusterDisplayName } from "@/lib/cluster-labels";
import { ACTION } from "@/lib/labels";
import type { Opportunity } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "行动简报" };

const ACTION_VARIANT: Record<
  string,
  "destructive" | "warning" | "secondary" | "outline"
> = {
  investigate_now: "destructive",
  validate: "warning",
  monitor: "secondary",
  low_priority: "outline",
};

/* ── Brief memo component ──────────────────────────────────────── */

function BriefMemo({ opportunity }: { opportunity: Opportunity }) {
  const brief = opportunity.brief!;
  const displayName = getClusterDisplayName({
    clusterKey: opportunity.clusterKey,
    name: opportunity.name,
  });
  const actionLabel = ACTION[opportunity.action] ?? opportunity.action;
  const actionVariant = ACTION_VARIANT[opportunity.action] ?? "outline";

  return (
    <article className="py-8 first:pt-0 last:pb-0">
      {/* Title row */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-foreground">
            {displayName}
          </h2>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <Badge variant={actionVariant}>{actionLabel}</Badge>
            <span className="text-xs tabular-nums text-primary">
              优先级 {Math.round(opportunity.priority * 100)}
            </span>
            <span className="text-xs text-muted-foreground">
              {opportunity.size} 条反馈
            </span>
          </div>
        </div>
      </div>

      {/* Core judgment */}
      <div className="mt-5">
        <h3 className="text-xs font-medium text-foreground/80">核心判断</h3>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          {brief.what_changed ?? "—"}
        </p>
      </div>

      {/* User impact */}
      {brief.evidence_summary ? (
        <div className="mt-4">
          <h3 className="text-xs font-medium text-foreground/80">用户影响</h3>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {brief.evidence_summary}
          </p>
        </div>
      ) : null}

      {/* Why now */}
      {brief.product_hypothesis ? (
        <div className="mt-4">
          <h3 className="text-xs font-medium text-foreground/80">
            为什么现在关注
          </h3>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {brief.product_hypothesis}
          </p>
        </div>
      ) : null}

      {/* Recommended actions */}
      {brief.recommended_investigation ? (
        <div className="mt-4">
          <h3 className="text-xs font-medium text-foreground/80">建议行动</h3>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {brief.recommended_investigation}
          </p>
        </div>
      ) : null}

      {/* Validation plan */}
      {brief.suggested_validation ? (
        <div className="mt-4">
          <h3 className="text-xs font-medium text-foreground/80">验证方案</h3>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {brief.suggested_validation}
          </p>
        </div>
      ) : null}

      {/* Success signals */}
      {brief.metrics_to_monitor?.length ? (
        <div className="mt-4">
          <h3 className="text-xs font-medium text-foreground/80">成功信号</h3>
          <ul className="mt-1 space-y-1 text-sm leading-6 text-muted-foreground">
            {brief.metrics_to_monitor.map((metric, i) => (
              <li key={i}>{metric}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* Affected scope */}
      {brief.affected_workflow || brief.affected_surface_platform ? (
        <div className="mt-4">
          <h3 className="text-xs font-medium text-foreground/80">
            影响范围
          </h3>
          <div className="mt-1 space-y-1 text-sm text-muted-foreground">
            {brief.affected_workflow ? (
              <p>
                <span className="text-xs text-foreground/60">场景：</span>
                {brief.affected_workflow}
              </p>
            ) : null}
            {brief.affected_surface_platform ? (
              <p>
                <span className="text-xs text-foreground/60">端/平台：</span>
                {brief.affected_surface_platform}
              </p>
            ) : null}
          </div>
        </div>
      ) : null}

      {/* Risks / caveats */}
      {opportunity.needsRefinement ? (
        <div className="mt-4 rounded-md border border-warning/30 bg-warning/5 px-3 py-2 text-xs text-muted-foreground">
          该问题簇覆盖范围较广，本简报建议进行簇级调查，而非指向某个具体修复。
        </div>
      ) : null}

      {/* Evidence */}
      {opportunity.representatives.length > 0 ? (
        <div className="mt-5">
          <h3 className="text-xs font-medium text-foreground/80">证据</h3>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
            {opportunity.representatives.slice(0, 4).map((ev) => (
              <a
                key={ev.issueNumber}
                href={ev.githubUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-primary underline-offset-4 hover:underline"
              >
                #{ev.issueNumber}
              </a>
            ))}
            {opportunity.representatives.length > 4 ? (
              <span className="text-xs text-muted-foreground">
                共 {opportunity.representatives.length} 条
              </span>
            ) : null}
            <a
              href={opportunity.representatives[0]?.githubUrl ?? "#"}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-primary underline-offset-4 hover:underline"
            >
              查看 GitHub 原始证据 →
            </a>
          </div>
        </div>
      ) : null}

      {/* Link to opportunity */}
      <div className="mt-4">
        <a
          href="/opportunities"
          className="text-xs text-primary underline-offset-4 hover:underline"
        >
          查看对应产品机会 →
        </a>
      </div>
    </article>
  );
}

/* ── Page ──────────────────────────────────────────────────────── */

export default async function ActionBriefsPage() {
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const { configured, error, rows } = await getOpportunities(version, 50);
  const briefed = rows.filter((r) => r.brief);

  const investigateNow = briefed.filter(
    (r) => r.action === "investigate_now"
  );
  const validate = briefed.filter((r) => r.action === "validate");
  const monitor = briefed.filter((r) => r.action === "monitor");
  const lowPriority = briefed.filter((r) => r.action === "low_priority");

  return (
    <div className="space-y-12">
      {/* Header */}
      <header className="space-y-3">
        <p className="text-xs font-medium tracking-wide text-muted-foreground">
          行动简报
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          行动简报
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          将高优先级用户问题转化为可执行的调查、验证与后续行动建议。
        </p>
        <p className="text-xs text-muted-foreground">
          行动建议基于公开反馈证据生成，用于支持进一步验证，不代表已确认根因或官方路线图。
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="数据库未配置"
          description="请配置 Supabase 连接以查看行动简报。"
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_ANON_KEY"
        />
      ) : error ? (
        <EmptyState
          title="数据库查询失败"
          description={`行动简报数据读取未成功，请检查配置后重试。(${error})`}
          hint="运行 python -m pipeline.opportunities"
        />
      ) : briefed.length === 0 ? (
        <EmptyState
          title="尚未生成行动简报"
          description="行动简报在确定性评分和状态固定后，基于存储证据生成。"
          hint="python -m pipeline.opportunities"
        />
      ) : (
        <>
          {/* Summary strip */}
          <section>
            <div className="flex flex-wrap items-baseline gap-x-8 gap-y-4 text-sm">
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-bold tabular-nums text-foreground">
                  {briefed.length}
                </span>
                <span className="text-xs text-muted-foreground">
                  行动简报
                </span>
              </div>
              {investigateNow.length > 0 ? (
                <>
                  <div className="hidden h-5 w-px bg-border sm:block" />
                  <div className="flex items-baseline gap-2">
                    <span className="text-lg font-bold tabular-nums text-destructive">
                      {investigateNow.length}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      立即调查
                    </span>
                  </div>
                </>
              ) : null}
              {validate.length > 0 ? (
                <>
                  <div className="hidden h-5 w-px bg-border sm:block" />
                  <div className="flex items-baseline gap-2">
                    <span className="text-lg font-bold tabular-nums text-foreground">
                      {validate.length}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      待验证
                    </span>
                  </div>
                </>
              ) : null}
            </div>
          </section>

          <hr className="border-border" />

          {/* Briefs grouped by status */}
          {investigateNow.length > 0 ? (
            <section>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                立即调查
              </h2>
              <div className="mt-4 divide-y divide-border">
                {investigateNow.map((opp) => (
                  <BriefMemo key={opp.id} opportunity={opp} />
                ))}
              </div>
            </section>
          ) : null}

          {validate.length > 0 ? (
            <section>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                待验证
              </h2>
              <div className="mt-4 divide-y divide-border">
                {validate.map((opp) => (
                  <BriefMemo key={opp.id} opportunity={opp} />
                ))}
              </div>
            </section>
          ) : null}

          {monitor.length > 0 ? (
            <section>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                持续观察
              </h2>
              <div className="mt-4 divide-y divide-border">
                {monitor.map((opp) => (
                  <BriefMemo key={opp.id} opportunity={opp} />
                ))}
              </div>
            </section>
          ) : null}

          {lowPriority.length > 0 ? (
            <section>
              <h2 className="text-lg font-semibold tracking-tight text-foreground">
                低优先级
              </h2>
              <div className="mt-4 divide-y divide-border">
                {lowPriority.map((opp) => (
                  <BriefMemo key={opp.id} opportunity={opp} />
                ))}
              </div>
            </section>
          ) : null}

          {/* Methodology disclosure */}
          <details className="text-xs text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">
              生成与证据说明
            </summary>
            <div className="mt-3 space-y-1 pl-4">
              <p>
                调查优先级与状态在简报生成前已确定，简报基于存储证据生成。
              </p>
              <p>简报不建立已确认的根因或版本因果关系。</p>
              <p>AI 辅助解读；证据与数据决定可追溯性。</p>
              <p>
                覆盖范围较广（needs_refinement）的簇携带明确的不确定性说明。
              </p>
            </div>
          </details>
        </>
      )}
    </div>
  );
}
