import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/stat-card";
import { getEntityCount } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "Releases" };

export default async function ReleasesPage() {
  const { configured, error, count } = await getEntityCount("releases");

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          Releases
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Releases</h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          Before/after comparison of feedback structure around product events
          (default window: ±7 days). Signal reports correlation —{" "}
          <em>related feedback increased after the release and is worth
          further investigation</em> — it never claims a release caused an
          issue.
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
          description={`The releases table could not be read. (${error})`}
          hint="Run supabase/schema.sql against your Supabase project"
        />
      ) : count ? (
        <section className="grid grid-cols-2 gap-4">
          <StatCard
            label="Release events recorded"
            value={count.toLocaleString("en-US")}
            hint="Release impact analysis arrives with Prompt 04"
          />
        </section>
      ) : (
        <EmptyState
          title="No release events recorded yet"
          description="Release and product-event dates are seeded manually from official public release notes, each with a source_url. The before/after impact analysis is delivered with Prompt 04."
          hint="prompts/04_RELEASES_ACTIONS.md"
        />
      )}
    </div>
  );
}
