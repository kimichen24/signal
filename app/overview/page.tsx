import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/stat-card";
import { getDataSummary } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "Overview" };

function formatNumber(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("en-US");
}

export default async function OverviewPage() {
  const caseStudy = process.env.NEXT_PUBLIC_CASE_STUDY ?? "OpenAI Codex";
  const summary = await getDataSummary();
  const hasData =
    summary.configured &&
    summary.error === null &&
    (summary.totalIssues ?? 0) > 0;

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          Overview
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">
          What changed?
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          Recent shifts in user feedback for the {caseStudy} case study. Every
          number on this page is computed from real, ingested GitHub issues —
          Signal never generates or simulates feedback.
        </p>
      </header>

      {!summary.configured ? (
        <EmptyState
          title="Database not configured"
          description="Signal reads all data from Supabase. Create .env.local from .env.example, set the Supabase URL and service-role key, then run supabase/schema.sql against the project."
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY"
        />
      ) : summary.error ? (
        <EmptyState
          title="Database query failed"
          description={`Signal reached for the database but the query did not succeed. Fix the configuration or schema before continuing. (${summary.error})`}
          hint="Run supabase/schema.sql against your Supabase project"
        />
      ) : !hasData ? (
        <EmptyState
          title="No feedback imported yet"
          description="The pipeline has not ingested any GitHub issues yet. After ingestion and AI analysis (prompts 01–02), this page shows analyzed feedback volume, emerging signals and high-severity items — all computed from real data."
          hint="prompts/01_DATA_INGESTION.md"
        />
      ) : (
        <>
          <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard
              label="Issues ingested"
              value={formatNumber(summary.totalIssues)}
              hint="Real GitHub issues, PRs excluded"
            />
            <StatCard
              label="Feedback analyzed"
              value={formatNumber(summary.analyzedIssues)}
              hint="Structured AI analysis rows"
            />
            <StatCard
              label="Emerging signals"
              value={formatNumber(summary.emergingClusters)}
              hint="Deterministic trend detection"
            />
            <StatCard
              label="High-severity items"
              value={formatNumber(summary.highSeverityIssues)}
              hint="AI-estimated severity: high / critical"
            />
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-medium">What changed this week</h2>
            {summary.emergingClusters ? (
              <p className="text-sm leading-6 text-muted-foreground">
                {formatNumber(summary.emergingClusters)} emerging signal
                {summary.emergingClusters === 1 ? "" : "s"} detected. Signal
                drill-downs with trends and evidence arrive with the
                intelligence pipeline (prompts 02–03).
              </p>
            ) : (
              <p className="text-sm leading-6 text-muted-foreground">
                No emerging signals recorded yet. They are computed
                deterministically from analyzed feedback once the clustering
                and trends pipeline has run (prompts 02–03).
              </p>
            )}
          </section>

          {summary.latestIssueAt ? (
            <p className="text-xs text-muted-foreground">
              Latest ingested issue: {summary.latestIssueAt.slice(0, 10)}
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}
