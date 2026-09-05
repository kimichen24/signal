import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/stat-card";
import { getEntityCount } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "Opportunities" };

export default async function OpportunitiesPage() {
  const { configured, error, count } = await getEntityCount("opportunities");

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
          Investigation Priority — not roadmap priority and not a P0/P1 scale.
          Each opportunity combines frequency (30%), severity (25%), growth
          (25%) and engagement (20%) into a transparent score computed by
          deterministic, testable code, with a reason and recommended action.
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
          description={`The opportunities table could not be read. (${error})`}
          hint="Run supabase/schema.sql against your Supabase project"
        />
      ) : count ? (
        <section className="grid grid-cols-2 gap-4">
          <StatCard
            label="Opportunities scored"
            value={count.toLocaleString("en-US")}
            hint="Priority detail and action briefs arrive with Prompt 04"
          />
        </section>
      ) : (
        <EmptyState
          title="Investigation Priority not computed yet"
          description="Opportunities are scored from clusters once insights exist. The deterministic priority formula and grounded action briefs are delivered with Prompt 04."
          hint="prompts/04_RELEASES_ACTIONS.md"
        />
      )}
    </div>
  );
}
