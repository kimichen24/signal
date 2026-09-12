import { EmptyState } from "@/components/empty-state";
import { OpportunityCard } from "@/components/opportunity-card";
import { getOpportunities } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "Opportunities" };

export default async function OpportunitiesPage() {
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const { configured, error, rows } = await getOpportunities(version, 50);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          Opportunities
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          Opportunities
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          Investigation Priority — not roadmap priority and not a P0/P1
          scale. Transparent components: 30% frequency · 25% AI-estimated
          severity · 25% growth/signal strength · 20% engagement (real
          GitHub comments + reactions). Statuses are mapped
          deterministically before any generated prose. Analysis version{" "}
          {version}.
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="Database not configured"
          description="Create .env.local from .env.example and set the Supabase URL and service-role key."
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY"
        />
      ) : error ? (
        <EmptyState
          title="Database query failed"
          description={`The opportunities table could not be read. (${error})`}
          hint="Run python -m pipeline.opportunities to populate this page"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No opportunities computed yet"
          description="Opportunities are scored from production clusters after the trend engine has run. Execute the scoring pipeline to populate this page."
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
