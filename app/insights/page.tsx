import { EmptyState } from "@/components/empty-state";
import { InsightCard } from "@/components/insight-card";
import { getInsights } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "Insights" };

export default async function InsightsPage() {
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const { configured, error, rows } = await getInsights(version, 20);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          Insights
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Insights</h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          Problem clusters derived from semantic grouping of analyzed feedback.
          No insight without evidence: every cluster links back to the
          underlying GitHub issues, membership is computed deterministically
          from embeddings, and counts come from the database — never from the
          model. Analysis version {version}.
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="Database not configured"
          description="Create .env.local from .env.example and set the Supabase URL and service-role key, then run supabase/schema.sql."
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY"
        />
      ) : error ? (
        <EmptyState
          title="Database query failed"
          description={`The clusters table could not be read. (${error})`}
          hint="Run supabase/schema.sql and migration 0005 against your Supabase project"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No insights computed yet"
          description="Clusters are built by deterministic semantic clustering over analyzed, in-scope feedback with embeddings. Run the clustering pipeline to populate this page."
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
