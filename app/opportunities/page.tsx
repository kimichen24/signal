import { EmptyState } from "@/components/empty-state";
import { OpportunityCard } from "@/components/opportunity-card";
import { getOpportunities } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "机会" };

export default async function OpportunitiesPage() {
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const { configured, error, rows } = await getOpportunities(version, 50);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          机会
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          机会
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          调查优先级 — not roadmap priority and not a P0/P1
          scale. Transparent components: 30% 反馈频次 · 25% AI-estimated
          严重度 · 25% growth/信号强度 strength · 20% 互动度 (real
          GitHub comments + reactions). Statuses are mapped
          deterministically before any generated prose. Analysis version{" "}
          {version}.
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
          description={`The opportunities table could not be read. (${error})`}
          hint="运行 python -m pipeline.opportunities 以填充本页"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="尚未计算机会"
          description="机会 are scored from production clusters after the trend engine has run. Execute the scoring pipeline to populate this page."
          hint="python -m pipeline.opportunities"
        />
      ) : (
        <section className="space-y-4">
          {rows.map((opportunity) => (
            <OpportunityCard
              key={opportunity.id}
              opportunity={opportunity}
            />
          ))}
        </section>
      )}
    </div>
  );
}
