import { EmptyState } from "@/components/empty-state";
import { InsightCard } from "@/components/insight-card";
import { getInsights } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "洞察" };

export default async function InsightsPage() {
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const { configured, error, rows } = await getInsights(version, 20);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          洞察
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">洞察</h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          基于已分析反馈的语义聚类生成的产品问题簇。
          没有证据就没有洞察: every cluster links back to the
          underlying GitHub issues, membership is computed deterministically
          from embeddings, and counts come from the database — never from the
          model. Analysis version {version}.
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="数据库未配置"
          description="请从 .env.example 创建 .env.local，填入 Supabase URL 和 anon key，然后在项目中执行 supabase/schema.sql。"
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY"
        />
      ) : error ? (
        <EmptyState
          title="数据库查询失败"
          description={`The clusters table could not be read. (${error})`}
          hint="在 Supabase 项目中执行 supabase/schema.sql 和 migration 0005"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="尚未生成洞察"
          description="问题簇由确定性语义聚类在已完成结构化分析的有效反馈上构建。请先运行聚类流水线以填充本页。"
          hint="python -m pipeline.cluster_issues"
        />
      ) : (
        <section className="space-y-4">
          {rows.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </section>
      )}
    </div>
  );
}
