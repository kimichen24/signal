import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { RecentAnalysis } from "@/lib/supabase/queries";
import {
  ISSUE_TYPE,
  CATEGORY,
  SURFACE,
  PLATFORM,
} from "@/lib/labels";

const label = (map: Record<string, string>, value: string) => map[value] ?? value;

const SEVERITY_VARIANT: Record<string, "destructive" | "warning" | "secondary" | "outline"> = {
  critical: "destructive",
  high: "warning",
  medium: "secondary",
  low: "outline",
};

const SEVERITY_LABEL: Record<string, string> = {
  critical: "严重", high: "高", medium: "中", low: "低",
};

const SCOPE_LABEL: Record<string, string> = {
  codex_core: "Codex 核心",
  codex_adjacent: "Codex 邻接",
  out_of_scope: "范围外",
};

export function AnalysisCard({ analysis }: { analysis: RecentAnalysis }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-sm">
            <a
              href={analysis.githubUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="underline-offset-4 hover:underline"
            >
              #{analysis.issueNumber} · {analysis.title}
            </a>
          </CardTitle>
          <Badge
            variant={SEVERITY_VARIANT[analysis.severity] ?? "outline"}
            className="ml-auto"
          >
            AI 估算严重度：{SEVERITY_LABEL[analysis.severity] ?? analysis.severity}
          </Badge>
          {analysis.needsReview ? (
            <Badge variant="warning">建议人工复核</Badge>
          ) : null}
          <Badge
            variant={
              analysis.productScope === "out_of_scope" ? "outline" : "secondary"
            }
          >
            {SCOPE_LABEL[analysis.productScope] ?? analysis.productScope}
          </Badge>
        </div>
        <CardDescription className="leading-6">
          {analysis.summary}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-xs text-muted-foreground">
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          <span>
            <span className="text-foreground/80">{label(ISSUE_TYPE, analysis.issueType)}</span> ·{" "}
            {label(SURFACE, analysis.surface)} / {label(PLATFORM, analysis.platform)}
          </span>
          <span>
            {label(CATEGORY, analysis.category)} › {analysis.subtopic}
          </span>
          <span>置信度 {Math.round(analysis.confidence * 100)}%</span>
          <span>
            {analysis.analysisVersion} ·{" "}
            {analysis.analyzedAt.slice(0, 10)}
          </span>
        </div>
        {analysis.userScenario ? (
          <p>
            <span className="font-medium text-foreground/80">场景： </span>
            {analysis.userScenario}
          </p>
        ) : null}
        {analysis.userImpact ? (
          <p>
            <span className="font-medium text-foreground/80">影响： </span>
            {analysis.userImpact}
          </p>
        ) : null}
        {analysis.scopeReason ? (
          <p>
            <span className="font-medium text-foreground/80">范围：</span>
            {analysis.scopeReason}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
