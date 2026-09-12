import { EmptyState } from "@/components/empty-state";
import { StatCard } from "@/components/stat-card";
import {
  getDataSummary,
  getDistributions,
  getInsights,
  getTrendStatus,
} from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "Overview" };

function formatNumber(value: number | null): string {
  return value === null ? "—" : value.toLocaleString("en-US");
}

function DistributionList({
  title,
  slices,
}: {
  title: string;
  slices: { label: string; count: number; pct: number }[];
}) {
  const top = slices.slice(0, 6);
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      <ul className="mt-2 space-y-1 text-xs">
        {top.map((slice) => (
          <li key={slice.label} className="flex items-center gap-2">
            <span className="w-40 truncate">{slice.label}</span>
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
              <span
                className="block h-full rounded-full bg-foreground/60"
                style={{ width: `${slice.pct}%` }}
              />
            </span>
            <span className="w-16 text-right tabular-nums text-muted-foreground">
              {slice.count} ({slice.pct}%)
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default async function OverviewPage() {
  const caseStudy = process.env.NEXT_PUBLIC_CASE_STUDY ?? "OpenAI Codex";
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const summary = await getDataSummary();
  const hasData =
    summary.configured &&
    summary.error === null &&
    (summary.totalIssues ?? 0) > 0;

  const distributions = hasData ? await getDistributions(version) : null;
  const topClusters = hasData ? await getInsights(version, 5) : null;
  const trend = hasData ? await getTrendStatus(version) : null;

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
              hint={`analysis version ${version}`}
            />
            <StatCard
              label="In-scope feedback"
              value={formatNumber(distributions?.data?.inScopeTotal ?? null)}
              hint="codex_core + codex_adjacent"
            />
            <StatCard
              label="High-severity items"
              value={formatNumber(summary.highSeverityIssues)}
              hint="AI-estimated severity: high / critical"
            />
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-medium">What changed this week</h2>
            {trend?.status &&
            trend.status.state === "insufficient_history" ? (
              <div className="rounded-lg border border-dashed p-5">
                <p className="text-sm font-medium">
                  More historical feedback is required to calculate reliable
                  week-over-week changes.
                </p>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">
                  This development dataset covers feedback starting{" "}
                  {trend.status.earliestObservation?.slice(0, 10) ?? "—"} — the
                  previous 7-day period has{" "}
                  {trend.status.previousPeriod.count} observations (minimum 10
                  required). Signal does not fabricate growth percentages from
                  a missing baseline.
                </p>
              </div>
            ) : trend?.status ? (
              <div className="space-y-2 text-sm text-muted-foreground">
                <p>
                  Current period: {trend.status.currentPeriod.count}{" "}
                  observations; previous period:{" "}
                  {trend.status.previousPeriod.count}. Emerging signals
                  (deterministic growth ≥ 50% with volume ≥ 5) are flagged on
                  the Insights page.
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Trend status unavailable.
              </p>
            )}
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-medium">Top pain-point clusters</h2>
            {topClusters && topClusters.rows.length > 0 ? (
              <ul className="space-y-2">
                {topClusters.rows.map((cluster) => (
                  <li
                    key={cluster.id}
                    className="flex items-center justify-between gap-4 rounded-lg border px-4 py-3 text-sm"
                  >
                    <span className="min-w-0 truncate">
                      {cluster.name}
                      <span className="ml-2 text-xs text-muted-foreground">
                        {cluster.category}
                      </span>
                    </span>
                    <span className="shrink-0 tabular-nums text-muted-foreground">
                      {cluster.issueCount} issues
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted-foreground">
                No clusters computed yet — run{" "}
                <code className="font-mono text-xs">
                  python -m pipeline.cluster_issues
                </code>
                .
              </p>
            )}
          </section>

          {distributions?.data ? (
            <section className="space-y-4">
              <h2 className="text-sm font-medium">
                In-scope feedback distribution
              </h2>
              <div className="grid gap-6 md:grid-cols-3">
                <DistributionList
                  title="Surface"
                  slices={distributions.data.surface}
                />
                <DistributionList
                  title="Platform"
                  slices={distributions.data.platform}
                />
                <DistributionList
                  title="Category"
                  slices={distributions.data.category}
                />
              </div>
            </section>
          ) : null}

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
