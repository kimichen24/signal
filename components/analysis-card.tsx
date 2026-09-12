import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { RecentAnalysis } from "@/lib/supabase/queries";

const SEVERITY_VARIANT: Record<string, "destructive" | "warning" | "secondary" | "outline"> = {
  critical: "destructive",
  high: "warning",
  medium: "secondary",
  low: "outline",
};

const SCOPE_LABEL: Record<string, string> = {
  codex_core: "Codex core",
  codex_adjacent: "Codex adjacent",
  out_of_scope: "Out of scope",
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
            AI-estimated severity: {analysis.severity}
          </Badge>
          {analysis.needsReview ? (
            <Badge variant="warning">Needs review</Badge>
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
            <span className="text-foreground/80">{analysis.issueType}</span> ·{" "}
            {analysis.surface} / {analysis.platform}
          </span>
          <span>
            {analysis.category} › {analysis.subtopic}
          </span>
          <span>confidence {Math.round(analysis.confidence * 100)}%</span>
          <span>
            {analysis.analysisVersion} ·{" "}
            {analysis.analyzedAt.slice(0, 10)}
          </span>
        </div>
        {analysis.userScenario ? (
          <p>
            <span className="font-medium text-foreground/80">Scenario: </span>
            {analysis.userScenario}
          </p>
        ) : null}
        {analysis.userImpact ? (
          <p>
            <span className="font-medium text-foreground/80">Impact: </span>
            {analysis.userImpact}
          </p>
        ) : null}
        {analysis.scopeReason ? (
          <p>
            <span className="font-medium text-foreground/80">Scope: </span>
            {analysis.scopeReason}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
