import { EmptyState } from "@/components/empty-state";
import { getOpportunities } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "行动简报" };

export default async function ActionBriefsPage() {
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const { configured, error, rows } = await getOpportunities(version, 50);
  const briefed = rows.filter((r) => r.brief);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          行动简报
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          行动简报
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          Generated only after deterministic scores and statuses were fixed,
          and grounded strictly in stored evidence. Briefs never claim proven
          root cause, release causality, or internal impact. Broad clusters
          flagged needs_refinement carry explicit uncertainty. Analysis
          version {version}.
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="数据库未配置"
          description="请从 .env.example 创建 .env.local，填入 Supabase URL 和 anon key。"
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY"
        />
      ) : error ? (
        <EmptyState
          title="数据库查询失败"
          description={`Opportunities could not be read. (${error})`}
          hint="运行 python -m pipeline.opportunities"
        />
      ) : briefed.length === 0 ? (
        <EmptyState
          title="尚未生成行动简报"
          description="行动简报由 MiMo 针对满足机会门槛的问题簇生成，生成前会先计算调查优先级。"
          hint="python -m pipeline.opportunities"
        />
      ) : (
        <section className="space-y-4">
          {briefed.map((opportunity) => {
            const brief = opportunity.brief!;
            return (
              <div
                key={opportunity.id}
                className="space-y-3 rounded-lg border p-5 text-sm"
              >
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="font-medium">{opportunity.name}</h2>
                  <span className="text-xs text-muted-foreground">
                    {opportunity.category} · {opportunity.size} issues
                  </span>
                  <span className="ml-auto rounded-md border px-2 py-0.5 text-xs">
                    {opportunity.action}
                  </span>
                </div>
                <p className="leading-6 text-muted-foreground">
                  {brief.what_changed}
                </p>
                <dl className="space-y-2 text-xs leading-5">
                  {brief.affected_workflow ? (
                    <div>
                      <dt className="font-medium text-foreground/80">
                        Affected workflow
                      </dt>
                      <dd>{brief.affected_workflow}</dd>
                    </div>
                  ) : null}
                  {brief.affected_surface_platform ? (
                    <div>
                      <dt className="font-medium text-foreground/80">
                        Affected surface / platform
                      </dt>
                      <dd>{brief.affected_surface_platform}</dd>
                    </div>
                  ) : null}
                  {brief.evidence_summary ? (
                    <div>
                      <dt className="font-medium text-foreground/80">
                        证据 summary
                      </dt>
                      <dd>{brief.evidence_summary}</dd>
                    </div>
                  ) : null}
                  {brief.product_hypothesis ? (
                    <div>
                      <dt className="font-medium text-foreground/80">
                        产品假设（未验证）
                      </dt>
                      <dd>{brief.product_hypothesis}</dd>
                    </div>
                  ) : null}
                  {brief.recommended_investigation ? (
                    <div>
                      <dt className="font-medium text-foreground/80">
                        建议调查
                      </dt>
                      <dd>{brief.recommended_investigation}</dd>
                    </div>
                  ) : null}
                  {brief.suggested_validation ? (
                    <div>
                      <dt className="font-medium text-foreground/80">
                        建议验证
                      </dt>
                      <dd>{brief.suggested_validation}</dd>
                    </div>
                  ) : null}
                  {brief.metrics_to_monitor?.length ? (
                    <div>
                      <dt className="font-medium text-foreground/80">
                        建议监控指标
                      </dt>
                      <dd>{brief.metrics_to_monitor.join(" · ")}</dd>
                    </div>
                  ) : null}
                </dl>
                {opportunity.representatives.length ? (
                  <div className="text-xs">
                    <p className="font-medium text-foreground/80">
                      证据
                    </p>
                    <ul className="mt-1 space-y-1">
                      {opportunity.representatives.map((evidence) => (
                        <li key={evidence.issueNumber}>
                          <a
                            href={evidence.githubUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="underline-offset-4 hover:underline"
                          >
                            #{evidence.issueNumber} {evidence.title}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            );
          })}
        </section>
      )}
    </div>
  );
}
