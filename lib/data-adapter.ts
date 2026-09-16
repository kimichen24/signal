/**
 * Target-aware data adapter.
 * - Vercel: delegates to existing Supabase query functions (runtime).
 * - GitHub Pages: reads from build-time generated static JSON snapshots.
 *
 * Pages import from this module instead of directly from queries.ts.
 * Function signatures match the original Supabase queries.
 */

import { readFileSync } from "fs";
import { join } from "path";
import { connection } from "next/server";

const isStatic = process.env.DEPLOY_TARGET === "github-pages";

function readStaticJSON<T>(filename: string): T {
  const path = join(process.cwd(), "generated", "static-data", filename);
  return JSON.parse(readFileSync(path, "utf-8")) as T;
}

/* ── Overview ──────────────────────────────────────────────────── */

export async function getOverviewData() {
  if (isStatic) {
    return readStaticJSON<{
      summary: import("@/lib/supabase/queries").DataSummary;
      distributions: import("@/lib/supabase/queries").Distributions | null;
      topOpportunities: import("@/lib/supabase/queries").Opportunity[];
      clusterCount: number;
      opportunityCount: number;
    }>("overview.json");
  }

  await connection();

  const {
    getDataSummary,
    getDistributions,
    getEntityCount,
    getOpportunities,
  } = await import("@/lib/supabase/queries");

  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const summary = await getDataSummary(version);
  const hasData =
    summary.configured &&
    summary.error === null &&
    (summary.totalIssues ?? 0) > 0;

  const [distributions, opportunities, clusterCount, opportunityCount] =
    hasData
      ? await Promise.all([
          getDistributions(version),
          getOpportunities(version, 50),
          getEntityCount("clusters", version),
          getEntityCount("opportunities"),
        ])
      : [null, null, null, null];

  return {
    summary,
    distributions: distributions?.data ?? null,
    topOpportunities: opportunities?.rows ?? [],
    clusterCount: clusterCount?.count ?? null,
    opportunityCount: opportunityCount?.count ?? null,
  };
}

/* ── Feedback ──────────────────────────────────────────────────── */

export async function getFeedbackData() {
  if (isStatic) {
    return readStaticJSON<{
      configured: boolean;
      error: string | null;
      rows: import("@/lib/supabase/queries").FeedbackInboxItem[];
    }>("feedback.json");
  }

  await connection();

  const { getFeedbackInbox } = await import("@/lib/supabase/queries");
  return getFeedbackInbox(20);
}

/* ── Insights ──────────────────────────────────────────────────── */

export async function getInsightsData(): Promise<{
  insights: import("@/lib/supabase/queries").Insight[];
  counts: import("@/lib/supabase/queries").ClusterInsightCounts;
  configured: boolean;
  error: string | null;
}> {
  if (isStatic) {
    const data = readStaticJSON<{
      insights: import("@/lib/supabase/queries").Insight[];
      counts: import("@/lib/supabase/queries").ClusterInsightCounts;
      configured: boolean;
      error: string | null;
    }>("insights.json");
    return data;
  }

  await connection();

  const { getInsights, getClusterInsightCounts } = await import(
    "@/lib/supabase/queries"
  );
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  const { configured, error, rows } = await getInsights(version, 50);
  const countsResult = configured
    ? await getClusterInsightCounts(version)
    : null;

  return {
    insights: rows,
    counts: countsResult?.counts ?? { total: 0, emerging: 0, needsRefinement: 0 },
    configured,
    error,
  };
}

/* ── Releases ──────────────────────────────────────────────────── */

export async function getReleasesData() {
  if (isStatic) {
    return readStaticJSON<{
      configured: boolean;
      error: string | null;
      rows: import("@/lib/supabase/queries").ReleaseTimelineEntry[];
    }>("releases.json");
  }

  await connection();

  const { getReleaseTimeline } = await import("@/lib/supabase/queries");
  return getReleaseTimeline();
}

/* ── Opportunities ─────────────────────────────────────────────── */

export async function getOpportunitiesData() {
  if (isStatic) {
    return readStaticJSON<{
      configured: boolean;
      error: string | null;
      rows: import("@/lib/supabase/queries").Opportunity[];
    }>("opportunities.json");
  }

  await connection();

  const { getOpportunities } = await import("@/lib/supabase/queries");
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  return getOpportunities(version, 50);
}

/* ── Action Briefs ─────────────────────────────────────────────── */

export async function getActionBriefsData() {
  if (isStatic) {
    return readStaticJSON<{
      configured: boolean;
      error: string | null;
      rows: import("@/lib/supabase/queries").Opportunity[];
    }>("action-briefs.json");
  }

  await connection();

  const { getOpportunities } = await import("@/lib/supabase/queries");
  const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";
  return getOpportunities(version, 50);
}
