// Mirror of config/taxonomy.json (kept in sync by lib/types/taxonomy.test.ts).
// The stable top-level taxonomy is locked (docs/DECISIONS.md #7);
// subtopics are discovered dynamically by the AI extraction step.

export const TAXONOMY_VERSION = "0.3.0";

export const ISSUE_TYPES = [
  "bug",
  "feature_request",
  "ux_issue",
  "documentation",
  "other",
] as const;

export const PRODUCT_SCOPES = [
  "codex_core",
  "codex_adjacent",
  "out_of_scope",
] as const;

export const CATEGORIES = [
  "Reliability",
  "Performance",
  "Context & Memory",
  "Model Quality",
  "Tool Execution",
  "Git & Workspace",
  "App / UI / UX",
  "CLI",
  "IDE Integration",
  "Authentication & Account",
  "Usage & Credits",
  "MCP & Integrations",
  "Safety & Permissions",
  "Installation & Updates",
  "Onboarding & Documentation",
  "Other",
] as const;

export const SURFACES = [
  "Codex App",
  "CLI",
  "IDE Extension",
  "Web",
  "Unknown",
] as const;

export const PLATFORMS = [
  "Windows",
  "macOS",
  "Linux",
  "Android",
  "iOS",
  "Other",
  "Unknown",
] as const;

export const SEVERITIES = ["critical", "high", "medium", "low"] as const;

export const ACTION_TYPES = [
  "investigate_now",
  "validate",
  "monitor",
  "low_priority",
] as const;

export type IssueType = (typeof ISSUE_TYPES)[number];
export type ProductScope = (typeof PRODUCT_SCOPES)[number];
export type Category = (typeof CATEGORIES)[number];
export type Surface = (typeof SURFACES)[number];
export type Platform = (typeof PLATFORMS)[number];
export type Severity = (typeof SEVERITIES)[number];
export type ActionType = (typeof ACTION_TYPES)[number];
