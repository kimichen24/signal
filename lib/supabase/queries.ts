import { getSupabaseAdmin } from "@/lib/supabase/server";
import { isSupabaseConfigured } from "@/lib/env";

/**
 * Server-side data access. Every function returns honest nulls/errors —
 * the frontend never fabricates fallback data (docs/ARCHITECTURE.md §4).
 */

export interface DataSummary {
  configured: boolean;
  error: string | null;
  totalIssues: number | null;
  analyzedIssues: number | null;
  emergingClusters: number | null;
  highSeverityIssues: number | null;
  latestIssueAt: string | null;
}

export async function getDataSummary(): Promise<DataSummary> {
  const base: DataSummary = {
    configured: isSupabaseConfigured(),
    error: null,
    totalIssues: null,
    analyzedIssues: null,
    emergingClusters: null,
    highSeverityIssues: null,
    latestIssueAt: null,
  };
  if (!base.configured) return base;

  const client = getSupabaseAdmin();
  if (!client) return base;

  try {
    const [issues, analyzed, emerging, highSeverity, latest] =
      await Promise.all([
        client.from("issues").select("id", { count: "exact", head: true }),
        client
          .from("issue_analysis")
          .select("issue_id", { count: "exact", head: true }),
        client
          .from("clusters")
          .select("id", { count: "exact", head: true })
          .eq("is_emerging", true),
        client
          .from("issue_analysis")
          .select("issue_id", { count: "exact", head: true })
          .in("severity", ["high", "critical"]),
        client
          .from("issues")
          .select("github_created_at")
          .order("github_created_at", { ascending: false })
          .limit(1),
      ]);

    const firstError =
      issues.error ??
      analyzed.error ??
      emerging.error ??
      highSeverity.error ??
      latest.error;
    if (firstError) return { ...base, error: firstError.message };

    return {
      ...base,
      totalIssues: issues.count ?? 0,
      analyzedIssues: analyzed.count ?? 0,
      emergingClusters: emerging.count ?? 0,
      highSeverityIssues: highSeverity.count ?? 0,
      latestIssueAt: latest.data?.[0]?.github_created_at ?? null,
    };
  } catch (e) {
    return {
      ...base,
      error: e instanceof Error ? e.message : "Unknown database error",
    };
  }
}

export interface RecentIssue {
  id: string;
  github_issue_number: number;
  title: string;
  github_url: string;
  state: string | null;
  github_created_at: string;
}

export interface RecentIssuesResult {
  configured: boolean;
  error: string | null;
  rows: RecentIssue[];
}

export async function getRecentIssues(limit = 10): Promise<RecentIssuesResult> {
  if (!isSupabaseConfigured()) {
    return { configured: false, error: null, rows: [] };
  }
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, rows: [] };

  try {
    const { data, error } = await client
      .from("issues")
      .select(
        "id, github_issue_number, title, github_url, state, github_created_at"
      )
      .order("github_created_at", { ascending: false })
      .limit(limit);
    if (error) return { configured: true, error: error.message, rows: [] };
    return { configured: true, error: null, rows: data ?? [] };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      rows: [],
    };
  }
}

export interface EntityCount {
  configured: boolean;
  error: string | null;
  count: number | null;
}

export async function getEntityCount(
  table: "clusters" | "releases" | "opportunities"
): Promise<EntityCount> {
  if (!isSupabaseConfigured()) {
    return { configured: false, error: null, count: null };
  }
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, count: null };

  try {
    const { count, error } = await client
      .from(table)
      .select("id", { count: "exact", head: true });
    if (error) return { configured: true, error: error.message, count: null };
    return { configured: true, error: null, count: count ?? 0 };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      count: null,
    };
  }
}
