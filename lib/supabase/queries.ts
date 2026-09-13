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

export async function getDataSummary(
  version?: string
): Promise<DataSummary> {
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
    // issues table is version-independent (raw ingestion).
    const issuesQuery = client
      .from("issues")
      .select("id", { count: "exact", head: true });

    // issue_analysis and clusters are scoped to a specific analysis version
    // when a version is provided. Without a version filter, counts sum across
    // all versions and can exceed the issue count (UNIQUE(issue_id, version)).
    const analyzedBase = client
      .from("issue_analysis")
      .select("issue_id", { count: "exact", head: true });
    const analyzedFinal = version
      ? analyzedBase.eq("analysis_version", version)
      : analyzedBase;

    const emergingBase = client
      .from("clusters")
      .select("id", { count: "exact", head: true })
      .eq("is_emerging", true);
    const emergingFinal = version
      ? emergingBase.eq("analysis_version", version)
      : emergingBase;

    const highSeverityBase = client
      .from("issue_analysis")
      .select("issue_id", { count: "exact", head: true })
      .in("severity", ["high", "critical"]);
    const highSeverityFinal = version
      ? highSeverityBase.eq("analysis_version", version)
      : highSeverityBase;

    const latestQuery = client
      .from("issues")
      .select("github_created_at")
      .order("github_created_at", { ascending: false })
      .limit(1);

    const [issues, analyzed, emerging, highSeverity, latest] =
      await Promise.all([
        issuesQuery,
        analyzedFinal,
        emergingFinal,
        highSeverityFinal,
        latestQuery,
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
  parsed_platform: string | null;
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
        "id, github_issue_number, title, github_url, state, parsed_platform, github_created_at"
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

export interface RecentAnalysis {
  issueNumber: number;
  title: string;
  githubUrl: string;
  issueType: string;
  surface: string;
  platform: string;
  category: string;
  subtopic: string;
  severity: string;
  confidence: number;
  needsReview: boolean;
  summary: string;
  userScenario: string | null;
  userImpact: string | null;
  productScope: string;
  scopeReason: string | null;
  analysisVersion: string;
  analyzedAt: string;
}

export interface RecentAnalysesResult {
  configured: boolean;
  error: string | null;
  rows: RecentAnalysis[];
}

export async function getRecentAnalyses(
  limit = 10
): Promise<RecentAnalysesResult> {
  if (!isSupabaseConfigured()) {
    return { configured: false, error: null, rows: [] };
  }
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, rows: [] };

  try {
    const { data, error } = await client
      .from("issue_analysis")
      .select(
        `issue_type, surface, platform, category, subtopic, severity,
         confidence, needs_review, summary, user_scenario, user_impact,
         product_scope, scope_reason, analysis_version, analyzed_at,
         issues(github_issue_number, title, github_url)`
      )
      .order("analyzed_at", { ascending: false })
      .limit(limit);
    if (error) return { configured: true, error: error.message, rows: [] };
    const rows = (data ?? []).map((row: Record<string, unknown>) => {
      const issue = row.issues as
        | { github_issue_number: number; title: string; github_url: string }
        | null;
      return {
        issueNumber: issue?.github_issue_number ?? 0,
        title: issue?.title ?? "(deleted issue)",
        githubUrl: issue?.github_url ?? "",
        issueType: row.issue_type as string,
        surface: row.surface as string,
        platform: row.platform as string,
        category: row.category as string,
        subtopic: row.subtopic as string,
        severity: row.severity as string,
        confidence: Number(row.confidence),
        needsReview: Boolean(row.needs_review),
        summary: row.summary as string,
        userScenario: (row.user_scenario as string | null) ?? null,
        userImpact: (row.user_impact as string | null) ?? null,
        productScope: (row.product_scope as string) ?? "codex_core",
        scopeReason: (row.scope_reason as string | null) ?? null,
        analysisVersion: row.analysis_version as string,
        analyzedAt: row.analyzed_at as string,
      };
    });
    return { configured: true, error: null, rows };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      rows: [],
    };
  }
}

/* ── Feedback Inbox ──────────────────────────────────────────────── */

export interface FeedbackInboxItem {
  id: string;
  issueNumber: number;
  title: string;
  githubUrl: string;
  state: string | null;
  platform: string | null;
  createdAt: string;
  analysis: RecentAnalysis | null;
}

export interface FeedbackInboxResult {
  configured: boolean;
  error: string | null;
  rows: FeedbackInboxItem[];
}

export async function getFeedbackInbox(
  limit = 20
): Promise<FeedbackInboxResult> {
  if (!isSupabaseConfigured())
    return { configured: false, error: null, rows: [] };
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, rows: [] };

  try {
    const { data: issues, error: issueErr } = await client
      .from("issues")
      .select(
        "id, github_issue_number, title, github_url, state, parsed_platform, github_created_at"
      )
      .order("github_created_at", { ascending: false })
      .limit(limit);
    if (issueErr)
      return { configured: true, error: issueErr.message, rows: [] };

    const issueIds = (issues ?? []).map((i) => i.id as string);
    const version = process.env.SIGNAL_ANALYSIS_VERSION ?? "v0.3.4";

    const { data: analyses } = await client
      .from("issue_analysis")
      .select(
        `issue_id, issue_type, surface, platform, category, subtopic, severity,
         confidence, needs_review, summary, user_scenario, user_impact,
         product_scope, scope_reason, analysis_version, analyzed_at,
         issues(github_issue_number, title, github_url)`
      )
      .eq("analysis_version", version)
      .in("issue_id", issueIds);

    const analysisMap = new Map<string, RecentAnalysis>();
    for (const row of analyses ?? []) {
      const r = row as Record<string, unknown>;
      const issue = r.issues as
        | { github_issue_number: number; title: string; github_url: string }
        | null;
      analysisMap.set(r.issue_id as string, {
        issueNumber: issue?.github_issue_number ?? 0,
        title: issue?.title ?? "",
        githubUrl: issue?.github_url ?? "",
        issueType: r.issue_type as string,
        surface: r.surface as string,
        platform: r.platform as string,
        category: r.category as string,
        subtopic: r.subtopic as string,
        severity: r.severity as string,
        confidence: Number(r.confidence),
        needsReview: Boolean(r.needs_review),
        summary: r.summary as string,
        userScenario: (r.user_scenario as string | null) ?? null,
        userImpact: (r.user_impact as string | null) ?? null,
        productScope: (r.product_scope as string) ?? "codex_core",
        scopeReason: (r.scope_reason as string | null) ?? null,
        analysisVersion: r.analysis_version as string,
        analyzedAt: r.analyzed_at as string,
      });
    }

    const rows: FeedbackInboxItem[] = (issues ?? []).map((issue) => ({
      id: issue.id as string,
      issueNumber: issue.github_issue_number as number,
      title: issue.title as string,
      githubUrl: issue.github_url as string,
      state: (issue.state as string) ?? null,
      platform: (issue.parsed_platform as string | null) ?? null,
      createdAt: (issue.github_created_at as string) ?? "",
      analysis: analysisMap.get(issue.id as string) ?? null,
    }));

    return { configured: true, error: null, rows };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      rows: [],
    };
  }
}

export interface InsightEvidence {
  issueNumber: number;
  title: string;
  githubUrl: string;
  state: string | null;
}

export interface Insight {
  id: string;
  clusterKey: string;
  name: string;
  category: string;
  summary: string | null;
  problemStatement: string | null;
  issueCount: number;
  primarySurface: string | null;
  primaryPlatform: string | null;
  avgSeverityScore: number | null;
  needsRefinement: boolean;
  isEmerging: boolean;
  emergingScore: number | null;
  growthRate: number | null;
  currentPeriodCount: number | null;
  previousPeriodCount: number | null;
  clusteringParams: Record<string, unknown> | null;
  representatives: InsightEvidence[];
}

export interface InsightsResult {
  configured: boolean;
  error: string | null;
  rows: Insight[];
}

export async function getInsights(
  version: string,
  limit = 20
): Promise<InsightsResult> {
  if (!isSupabaseConfigured()) {
    return { configured: false, error: null, rows: [] };
  }
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, rows: [] };

  try {
    const clusters = await client
      .from("clusters")
      .select(
        "id,cluster_key,cluster_name,category,summary,problem_statement,issue_count,primary_surface,primary_platform,avg_severity_score,is_emerging,emerging_score,growth_rate,current_period_count,previous_period_count,clustering_params"
      )
      .eq("analysis_version", version)
      .order("issue_count", { ascending: false })
      .limit(limit);
    if (clusters.error) return { configured: true, error: clusters.error.message, rows: [] };

    const ids = (clusters.data ?? []).map((c) => c.id as string);
    const evidenceByCluster = new Map<string, InsightEvidence[]>();
    if (ids.length > 0) {
      const members = await client
        .from("cluster_members")
        .select(
          "cluster_id,issues(github_issue_number,title,github_url,state)"
        )
        .eq("is_representative", true)
        .in("cluster_id", ids);
      if (members.error)
        return { configured: true, error: members.error.message, rows: [] };
      for (const member of members.data ?? []) {
        const issue = member.issues as unknown as
          | {
              github_issue_number: number;
              title: string;
              github_url: string;
              state: string | null;
            }
          | null;
        if (!issue) continue;
        const list = evidenceByCluster.get(member.cluster_id) ?? [];
        list.push({
          issueNumber: issue.github_issue_number,
          title: issue.title,
          githubUrl: issue.github_url,
          state: issue.state,
        });
        evidenceByCluster.set(member.cluster_id, list);
      }
    }

    const rows: Insight[] = (clusters.data ?? []).map((c) => {
      const params =
        (c.clustering_params as Record<string, unknown> | null) ?? null;
      return {
        id: c.id as string,
        clusterKey: c.cluster_key as string,
        name: (c.cluster_name as string) ?? (c.cluster_key as string),
        category: c.category as string,
        summary: (c.summary as string | null) ?? null,
        problemStatement: (c.problem_statement as string | null) ?? null,
        issueCount: Number(c.issue_count),
        primarySurface: (c.primary_surface as string | null) ?? null,
        primaryPlatform: (c.primary_platform as string | null) ?? null,
        avgSeverityScore:
          c.avg_severity_score === null
            ? null
            : Number(c.avg_severity_score),
        needsRefinement: Boolean(params?.needs_refinement),
        isEmerging: Boolean(c.is_emerging),
        emergingScore:
          c.emerging_score === null ? null : Number(c.emerging_score),
        growthRate: c.growth_rate === null ? null : Number(c.growth_rate),
        currentPeriodCount:
          c.current_period_count === null
            ? null
            : Number(c.current_period_count),
        previousPeriodCount:
          c.previous_period_count === null
            ? null
            : Number(c.previous_period_count),
        clusteringParams: params,
        representatives: evidenceByCluster.get(c.id as string) ?? [],
      };
    });
    return { configured: true, error: null, rows };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      rows: [],
    };
  }
}

export interface DistributionSlice {
  label: string;
  count: number;
  pct: number;
}

export interface Distributions {
  surface: DistributionSlice[];
  platform: DistributionSlice[];
  category: DistributionSlice[];
  inScopeTotal: number;
}

function toSlices(counter: Map<string, number>, total: number): DistributionSlice[] {
  return [...counter.entries()]
    .map(([label, count]) => ({
      label,
      count,
      pct: total ? Math.round((100 * count) / total) : 0,
    }))
    .sort((a, b) => b.count - a.count);
}

export async function getDistributions(
  version: string
): Promise<{ configured: boolean; error: string | null; data: Distributions | null }> {
  if (!isSupabaseConfigured()) return { configured: false, error: null, data: null };
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, data: null };
  try {
    // Paginated fetch — PostgREST defaults to 1000 rows per request.
    type DistRow = { surface: string; platform: string; category: string };
    const allRows: DistRow[] = [];
    for (let offset = 0; ; ) {
      const { data: batch, error } = await client
        .from("issue_analysis")
        .select("surface,platform,category")
        .eq("analysis_version", version)
        .neq("product_scope", "out_of_scope")
        .range(offset, offset + 999);
      if (error) return { configured: true, error: error.message, data: null };
      const rows = (batch ?? []) as DistRow[];
      allRows.push(...rows);
      if (rows.length < 1000) break;
      offset += 1000;
    }
    const surface = new Map<string, number>();
    const platform = new Map<string, number>();
    const category = new Map<string, number>();
    for (const row of allRows) {
      surface.set(row.surface, (surface.get(row.surface) ?? 0) + 1);
      platform.set(row.platform, (platform.get(row.platform) ?? 0) + 1);
      category.set(row.category, (category.get(row.category) ?? 0) + 1);
    }
    const inScopeTotal = allRows.length;
    return {
      configured: true,
      error: null,
      data: {
        surface: toSlices(surface, inScopeTotal),
        platform: toSlices(platform, inScopeTotal),
        category: toSlices(category, inScopeTotal),
        inScopeTotal,
      },
    };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      data: null,
    };
  }
}

export interface TrendStatus {
  state: "ok" | "insufficient_history";
  reason: string | null;
  earliestObservation: string | null;
  currentPeriod: { start: string; end: string; count: number };
  previousPeriod: { start: string; end: string; count: number };
}

function utcDayStart(date: Date): Date {
  return new Date(
    Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate())
  );
}

/** Mirrors pipeline/compute_trends.py: complete UTC days, half-open periods. */
export async function getTrendStatus(
  version: string,
  minPeriodVolume = Number(process.env.SIGNAL_TREND_MIN_PERIOD_VOLUME ?? 10)
): Promise<{ configured: boolean; error: string | null; status: TrendStatus | null }> {
  if (!isSupabaseConfigured())
    return { configured: false, error: null, status: null };
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, status: null };
  try {
    // Paged fetch: a single request silently truncates (default 1000 rows).
    type CreatedRow = {
      issues: { github_created_at?: string } | { github_created_at?: string }[] | null;
    };
    const data: CreatedRow[] = [];
    let offset = 0;
    for (;;) {
      const { data: batch, error } = await client
        .from("issue_analysis")
        .select("issues(github_created_at)")
        .eq("analysis_version", version)
        .neq("product_scope", "out_of_scope")
        .range(offset, offset + 999);
      if (error) return { configured: true, error: error.message, status: null };
      const rows = (batch ?? []) as CreatedRow[];
      data.push(...rows);
      if (rows.length < 1000) break;
      offset += 1000;
    }

    const todayStart = utcDayStart(new Date());
    const currentStart = new Date(todayStart);
    currentStart.setUTCDate(currentStart.getUTCDate() - 7);
    const previousStart = new Date(currentStart);
    previousStart.setUTCDate(previousStart.getUTCDate() - 7);

    let current = 0;
    let previous = 0;
    let earliest: Date | null = null;
    for (const row of data ?? []) {
      // supabase-js cannot infer relation cardinality without generated
      // types — `issues` may be typed as an object or a 1-element array.
      const issue = row.issues as
        | { github_created_at?: string }
        | { github_created_at?: string }[]
        | null;
      const raw = Array.isArray(issue)
        ? issue[0]?.github_created_at
        : issue?.github_created_at;
      if (!raw) continue;
      const ts = new Date(raw);
      if (!earliest || ts < earliest) earliest = ts;
      if (ts >= currentStart && ts < todayStart) current += 1;
      else if (ts >= previousStart && ts < currentStart) previous += 1;
    }

    let state: TrendStatus["state"] = "ok";
    let reason: string | null = null;
    if (!earliest || earliest >= previousStart) {
      state = "insufficient_history";
      reason = "dataset does not cover the previous comparison period";
    } else if (previous < minPeriodVolume || current < minPeriodVolume) {
      state = "insufficient_history";
      reason = `a comparison period has fewer than ${minPeriodVolume} observations`;
    }

    return {
      configured: true,
      error: null,
      status: {
        state,
        reason,
        earliestObservation: earliest ? earliest.toISOString() : null,
        currentPeriod: {
          start: currentStart.toISOString(),
          end: todayStart.toISOString(),
          count: current,
        },
        previousPeriod: {
          start: previousStart.toISOString(),
          end: currentStart.toISOString(),
          count: previous,
        },
      },
    };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      status: null,
    };
  }
}

/* ── Cluster Insight Counts (full-production aggregates) ────────── */

export interface ClusterInsightCounts {
  total: number;
  emerging: number;
  needsRefinement: number;
}

export async function getClusterInsightCounts(
  version: string
): Promise<{ configured: boolean; error: string | null; counts: ClusterInsightCounts | null }> {
  if (!isSupabaseConfigured())
    return { configured: false, error: null, counts: null };
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, counts: null };

  try {
    const { data, error } = await client
      .from("clusters")
      .select("is_emerging,clustering_params")
      .eq("analysis_version", version);
    if (error)
      return { configured: true, error: error.message, counts: null };

    const rows = data ?? [];
    const emerging = rows.filter((r) => r.is_emerging).length;
    const needsRefinement = rows.filter((r) => {
      const params = r.clustering_params as Record<string, unknown> | null;
      return Boolean(params?.needs_refinement);
    }).length;

    return {
      configured: true,
      error: null,
      counts: { total: rows.length, emerging, needsRefinement },
    };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      counts: null,
    };
  }
}

export interface EntityCount {
  configured: boolean;
  error: string | null;
  count: number | null;
}

export async function getEntityCount(
  table: "clusters" | "releases" | "opportunities",
  version?: string
): Promise<EntityCount> {
  if (!isSupabaseConfigured()) {
    return { configured: false, error: null, count: null };
  }
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, count: null };

  try {
    let query = client
      .from(table)
      .select("id", { count: "exact", head: true });
    // Scope to analysis_version where the column exists on the table.
    // clusters and releases have analysis_version directly.
    // opportunities is linked via cluster_id — version scoping happens
    // at the page level through getOpportunities(version).
    if (version && table !== "opportunities") {
      query = query.eq("analysis_version", version);
    }
    const { count, error } = await query;
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

export interface Brief {
  what_changed?: string;
  affected_workflow?: string;
  affected_surface_platform?: string;
  evidence_summary?: string;
  product_hypothesis?: string;
  recommended_investigation?: string;
  suggested_validation?: string;
  metrics_to_monitor?: string[];
}

export interface OpportunityBase {
  clusterKey: string;
  name: string;
  category: string;
  size: number;
  current: number;
  previous: number;
  priority: number;
  components: Record<string, number>;
  weights: Record<string, number>;
  action: string;
  trendState: string | null;
  signalScore: number | null;
  isEmerging: boolean;
  growthRate: number | null;
  shareDeltaPp: number | null;
  needsRefinement: boolean;
  engagement: number;
  engagementAvailable: boolean;
  brief: Brief | null;
  representatives: InsightEvidence[];
}

export interface Opportunity
  extends OpportunityBase {
  id: string;
  name: string;
  category: string;
  size: number;
  current: number;
  previous: number;
  priority: number;
  components: Record<string, number>;
  weights: Record<string, number>;
  action: string;
  trendState: string | null;
  signalScore: number | null;
  isEmerging: boolean;
  growthRate: number | null;
  shareDeltaPp: number | null;
  needsRefinement: boolean;
  engagement: number;
  engagementAvailable: boolean;
  brief: Brief | null;
  representatives: InsightEvidence[];
}

export interface Opportunity
  extends Omit<OpportunityBase, never> {
  clusterId: string;
}

export async function getOpportunities(
  version: string,
  limit = 50
): Promise<{ configured: boolean; error: string | null; rows: Opportunity[] }> {
  if (!isSupabaseConfigured())
    return { configured: false, error: null, rows: [] };
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, rows: [] };
  try {
    const { data, error } = await client
      .from("opportunities")
      .select(
        `id,action_type,priority_score,frequency_score,severity_score,growth_score,engagement_score,priority_reason,product_hypothesis,action_brief,
         clusters!inner(id,cluster_key,cluster_name,category,issue_count,current_period_count,previous_period_count,growth_rate,is_emerging,clustering_params,analysis_version)`
      )
      .eq("clusters.analysis_version", version)
      .order("priority_score", { ascending: false })
      .limit(limit);
    if (error) return { configured: true, error: error.message, rows: [] };

    type RawRow = {
      id: string;
      action_type: string;
      priority_score: number;
      priority_reason: string | null;
      product_hypothesis: string | null;
      action_brief: Brief | null;
      engagement_score: number | null;
      clusters: {
        id: string;
        cluster_key: string;
        cluster_name: string;
        category: string;
        issue_count: number;
        current_period_count: number;
        previous_period_count: number;
        growth_rate: number | null;
        is_emerging: boolean;
        clustering_params: Record<string, unknown> | null;
      } | null;
    };

    const evidenceByCluster = new Map<string, InsightEvidence[]>();
    const clusterIds = (data ?? [])
      .map((r) => (r as unknown as RawRow).clusters?.id)
      .filter((v): v is string => Boolean(v));
    if (clusterIds.length) {
      for (let offset = 0; ; offset += 999) {
        const { data: members, error: mErr } = await client
          .from("cluster_members")
          .select(
            "cluster_id,is_representative,issues(github_issue_number,title,github_url,state)"
          )
          .eq("is_representative", true)
          .in("cluster_id", clusterIds)
          .range(offset, offset + 999);
        if (mErr) break;
        const list = (members ?? []) as unknown as {
          cluster_id: string;
          issues: {
            github_issue_number: number;
            title: string;
            github_url: string;
            state: string | null;
          } | null;
        }[];
        for (const m of list) {
          if (!m.issues) continue;
          const arr = evidenceByCluster.get(m.cluster_id) ?? [];
          arr.push({
            issueNumber: m.issues.github_issue_number,
            title: m.issues.title,
            githubUrl: m.issues.github_url,
            state: m.issues.state,
          });
          evidenceByCluster.set(m.cluster_id, arr);
        }
        if ((members ?? []).length < 1000) break;
        offset += 1000;
      }
    }

    const rows: Opportunity[] = ((data ?? []) as unknown[]).map(
      (raw): Opportunity => {
      const r = raw as unknown as RawRow;
      const cluster = r.clusters;
      const params =
        (cluster?.clustering_params as Record<string, unknown> | null) ?? {};
      const trend = (params.trend as Record<string, number | string> | null) ?? {};
      const reason = (() => {
        try {
          return JSON.parse(r.priority_reason || "{}");
        } catch {
          return {};
        }
      })();
      return {
        id: r.id,
        clusterId: cluster?.id ?? "",
        clusterKey: cluster?.cluster_key ?? "",
        name: cluster?.cluster_name ?? "",
        category: cluster?.category ?? "",
        size: Number(cluster?.issue_count ?? 0),
        current: Number(cluster?.current_period_count ?? 0),
        previous: Number(cluster?.previous_period_count ?? 0),
        priority: Number(r.priority_score),
        components: (reason.components ?? {}) as Record<string, number>,
        weights: (reason.weights ?? {}) as Record<string, number>,
        action: r.action_type,
        trendState: (reason.signal_state as string) ?? null,
        signalScore:
          reason.signal_score === null || reason.signal_score === undefined
            ? null
            : Number(reason.signal_score),
        isEmerging: Boolean(cluster?.is_emerging),
        growthRate:
          cluster?.growth_rate === null || cluster?.growth_rate === undefined
            ? null
            : Number(cluster.growth_rate),
        shareDeltaPp:
          trend.share_delta_pp === null || trend.share_delta_pp === undefined
            ? null
            : Number(trend.share_delta_pp),
        needsRefinement: Boolean(params.needs_refinement),
        engagement: Number(r.engagement_score ?? 0),
        engagementAvailable: Boolean(reason.engagement_available),
        brief: (r.action_brief as Brief | null) ?? null,
        representatives: evidenceByCluster.get(cluster?.id ?? "") ?? [],
      };
      },
    );
    return { configured: true, error: null, rows };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      rows: [],
    };
  }
}

export interface ReleaseRow {
  id: string;
  name: string;
  releaseDate: string;
  sourceUrl: string;
  beforeTotal: number;
  afterTotal: number;
  clustersImpacted: number;
  hasImpact: boolean;
}

export async function getReleases(): Promise<{
  configured: boolean;
  error: string | null;
  rows: ReleaseRow[];
}> {
  if (!isSupabaseConfigured())
    return { configured: false, error: null, rows: [] };
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, rows: [] };
  try {
    const { data: releases, error } = await client
      .from("releases")
      .select("id,name,release_date,source_url,description")
      .order("release_date", { ascending: false });
    if (error) return { configured: true, error: error.message, rows: [] };
    const { data: impacts, error: impErr } = await client
      .from("release_impacts")
      .select("release_id,before_count,after_count");
    if (impErr) return { configured: true, error: impErr.message, rows: [] };
    const agg = new Map<string, { before: number; after: number; clusters: number }>();
    for (const r of impacts ?? []) {
      const cur = agg.get(r.release_id) ?? { before: 0, after: 0, clusters: 0 };
      cur.before += Number(r.before_count);
      cur.after += Number(r.after_count);
      cur.clusters += 1;
      agg.set(r.release_id, cur);
    }
    const rows: ReleaseRow[] = (releases ?? []).map((r) => {
      const a = agg.get(r.id) ?? { before: 0, after: 0, clusters: 0 };
      return {
        id: r.id,
        name: r.name,
        releaseDate: r.release_date,
        sourceUrl: r.source_url,
        beforeTotal: a.before,
        afterTotal: a.after,
        clustersImpacted: a.clusters,
        hasImpact: a.clusters > 0,
      };
    });
    return { configured: true, error: null, rows };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      rows: [],
    };
  }
}

/* ── Release Timeline ───────────────────────────────────────────── */

export interface ReleaseTimelineCluster {
  clusterId: string;
  clusterKey: string;
  clusterName: string;
  beforeCount: number;
  afterCount: number;
  signalType: string;
}

export interface ReleaseTimelineEntry {
  id: string;
  name: string;
  releaseDate: string;
  sourceUrl: string;
  description: string | null;
  hasImpact: boolean;
  totalBefore: number;
  totalAfter: number;
  impactedClusters: number;
  topClusters: ReleaseTimelineCluster[];
}

export async function getReleaseTimeline(): Promise<{
  configured: boolean;
  error: string | null;
  rows: ReleaseTimelineEntry[];
}> {
  if (!isSupabaseConfigured())
    return { configured: false, error: null, rows: [] };
  const client = getSupabaseAdmin();
  if (!client) return { configured: false, error: null, rows: [] };

  try {
    const { data: releases, error } = await client
      .from("releases")
      .select("id,name,release_date,source_url,description")
      .order("release_date", { ascending: false });
    if (error) return { configured: true, error: error.message, rows: [] };

    type ImpactRow = {
      release_id: string;
      cluster_id: string;
      before_count: number;
      after_count: number;
      signal_type: string;
      clusters: { cluster_key: string; cluster_name: string } | null;
    };
    const allImpacts: ImpactRow[] = [];
    for (let offset = 0; ; ) {
      const { data: batch, error: impErr } = await client
        .from("release_impacts")
        .select(
          "release_id,cluster_id,before_count,after_count,signal_type,clusters(cluster_key,cluster_name)"
        )
        .order("after_count", { ascending: false })
        .range(offset, offset + 999);
      if (impErr)
        return { configured: true, error: impErr.message, rows: [] };
      const rows = (batch ?? []) as unknown as ImpactRow[];
      allImpacts.push(...rows);
      if (rows.length < 1000) break;
      offset += 1000;
    }

    const byRelease = new Map<string, ImpactRow[]>();
    for (const imp of allImpacts) {
      const list = byRelease.get(imp.release_id) ?? [];
      list.push(imp);
      byRelease.set(imp.release_id, list);
    }

    const timeline: ReleaseTimelineEntry[] = (releases ?? []).map((r) => {
      const impacts = byRelease.get(r.id) ?? [];
      let totalBefore = 0;
      let totalAfter = 0;
      const clusters: ReleaseTimelineCluster[] = impacts.map((imp) => {
        totalBefore += imp.before_count;
        totalAfter += imp.after_count;
        return {
          clusterId: imp.cluster_id,
          clusterKey: imp.clusters?.cluster_key ?? "",
          clusterName: imp.clusters?.cluster_name ?? "",
          beforeCount: imp.before_count,
          afterCount: imp.after_count,
          signalType: imp.signal_type,
        };
      });

      return {
        id: r.id,
        name: r.name,
        releaseDate: r.release_date,
        sourceUrl: r.source_url,
        description: r.description as string | null,
        hasImpact: impacts.length > 0,
        totalBefore,
        totalAfter,
        impactedClusters: impacts.length,
        topClusters: clusters.slice(0, 5),
      };
    });

    return { configured: true, error: null, rows: timeline };
  } catch (e) {
    return {
      configured: true,
      error: e instanceof Error ? e.message : "Unknown database error",
      rows: [],
    };
  }
}