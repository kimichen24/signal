import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/stat-card";
import { getEntityCount } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "Insights" };

export default async function InsightsPage() {
  const { configured, error, count } = await getEntityCount("clusters");

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          Insights
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Insights</h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          Problem clusters derived from semantic grouping of analyzed feedback.
          No insight without evidence: every insight links back to the
          underlying issues, and issue counts and growth are computed by
          deterministic code — never by the model.
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
          hint="Run supabase/schema.sql against your Supabase project"
        />
      ) : count ? (
        <section className="grid grid-cols-2 gap-4">
          <StatCard
            label="Clusters computed"
            value={count.toLocaleString("en-US")}
            hint="Cluster detail views arrive with Prompt 03"
          />
        </section>
      ) : (
        <EmptyState
          title="No insights computed yet"
          description="Insights require analyzed feedback (structured extraction) and semantic clustering. Run prompts 02–03 to populate this page."
          hint="prompts/02_AI_EXTRACTION.md · prompts/03_INTELLIGENCE.md"
        />
      )}
    </div>
  );
}
