// Hand-written mirrors of supabase/schema.sql rows the UI renders.
// Extend when prompts 01–04 introduce new columns or generated types.

import type {
  Category,
  IssueType,
  Platform,
  Severity,
  Surface,
} from "./taxonomy";

export type Sentiment = "negative" | "neutral" | "positive" | "mixed";

export interface GitHubLabel {
  name?: string;
}

export interface IssueRow {
  id: string;
  github_issue_number: number;
  title: string;
  body_raw: string | null;
  body_clean: string | null;
  github_url: string;
  state: string | null;
  github_labels: GitHubLabel[];
  comments_count: number;
  reactions_count: number;
  github_created_at: string;
  github_updated_at: string | null;
  github_closed_at: string | null;
  parsed_version: string | null;
  parsed_subscription: string | null;
  parsed_platform: string | null;
  duplicate_group_id: string | null;
  ingested_at: string;
}

export interface IssueAnalysisRow {
  id: string;
  issue_id: string;
  issue_type: IssueType;
  surface: Surface;
  platform: Platform;
  category: Category;
  subtopic: string;
  user_scenario: string | null;
  user_impact: string | null;
  severity: Severity;
  sentiment: Sentiment;
  summary: string;
  confidence: number;
  needs_review: boolean;
  analysis_version: string;
  model_name: string | null;
  analysis_error: string | null;
  analyzed_at: string;
}

export interface ClusterRow {
  id: string;
  analysis_version: string;
  cluster_key: string;
  cluster_name: string;
  category: Category;
  summary: string | null;
  issue_count: number;
  current_period_count: number;
  previous_period_count: number;
  growth_rate: number | null;
  avg_severity_score: number | null;
  primary_platform: string | null;
  primary_surface: string | null;
  emerging_score: number | null;
  is_emerging: boolean;
  representative_issue_ids: string[];
  generated_at: string;
}
