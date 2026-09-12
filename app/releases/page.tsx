import { EmptyState } from "@/components/empty-state";
import { getReleases } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "Releases" };

export default async function ReleasesPage() {
  const { configured, error, rows } = await getReleases();

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          Releases
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Releases</h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          Public Codex releases (authoritative GitHub source URLs) compared
          against in-scope feedback volume before and after each release.
          Signal reports <strong>correlation</strong> — related feedback
          increasing after a release warrants investigation; it never
          establishes causation. Windows are ±7 days clipped to the dataset
          bounds (2026-08-23 → 2026-09-06); comparisons below 5 days of
          coverage on either side are marked insufficient.
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
          description={`The releases table could not be read. (${error})`}
          hint="Run python -m pipeline.releases to seed real public releases"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No release events recorded yet"
          description="Release events are seeded from official public release notes, each with a source_url."
          hint="python -m pipeline.releases"
        />
      ) : (
        <section className="space-y-3">
          {rows.map((release) => (
            <div
              key={release.id}
              className="rounded-lg border px-4 py-3 text-sm"
            >
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <a
                  href={release.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium underline-offset-4 hover:underline"
                >
                  {release.name}
                </a>
                <span className="tabular-nums text-xs text-muted-foreground">
                  {release.releaseDate.slice(0, 10)}
                </span>
                {release.hasImpact ? (
                  <span className="text-xs text-muted-foreground">
                    in-scope feedback: {release.beforeTotal} before →{" "}
                    {release.afterTotal} after · {release.clustersImpacted}{" "}
                    clusters compared
                  </span>
                ) : (
                  <span className="text-xs text-warning">
                    insufficient_history — temporal coverage in this dataset
                    is incomplete for a ±7 day comparison
                  </span>
                )}
              </div>
              {release.hasImpact ? (
                <p className="mt-1 text-xs text-muted-foreground">
                  Where related feedback increased after this release, it
                  warrants investigation — this is a correlation observation,
                  not a causal claim.
                </p>
              ) : null}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
