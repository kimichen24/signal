import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Insight } from "@/lib/supabase/queries";

export function InsightCard({ insight }: { insight: Insight }) {
  const params = insight.clusteringParams as
    | { algorithm?: string; distance_threshold?: number }
    | null;
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-sm">{insight.name}</CardTitle>
          {insight.isEmerging ? (
            <Badge variant="destructive" className="ml-auto">
              新兴 · 增长 +
              {insight.growthRate !== null
                ? Math.round(insight.growthRate * 100)
                : "—"}
              % ({insight.currentPeriodCount} vs{" "}
              {insight.previousPeriodCount})
            </Badge>
          ) : null}
          {insight.needsRefinement ? (
            <Badge variant="warning" className={insight.isEmerging ? "" : "ml-auto"}>
              需进一步细化
            </Badge>
          ) : null}
          <Badge variant="secondary" className={insight.needsRefinement ? "" : "ml-auto"}>
            {insight.category}
          </Badge>
          <Badge variant="outline">{insight.issueCount} 条</Badge>
        </div>
        {insight.summary ? (
          <p className="text-sm leading-6 text-muted-foreground">
            {insight.summary}
          </p>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-3 text-xs text-muted-foreground">
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          <span>
            surface:{" "}
            <span className="text-foreground/80">
              {insight.primarySurface ?? "—"}
            </span>
          </span>
          <span>
            platform:{" "}
            <span className="text-foreground/80">
              {insight.primaryPlatform ?? "—"}
            </span>
          </span>
          <span>
            AI-estimated severity (avg score):{" "}
            <span className="text-foreground/80">
              {insight.avgSeverityScore ?? "—"}
            </span>
          </span>
        </div>
        {insight.problemStatement ? (
          <p className="text-foreground/80">
            <span className="font-medium">Problem: </span>
            {insight.problemStatement}
          </p>
        ) : null}
        <div>
          <p className="font-medium">代表性证据</p>
          <ul className="mt-1 space-y-1">
            {insight.representatives.map((evidence) => (
              <li key={evidence.issueNumber}>
                <a
                  href={evidence.githubUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline-offset-4 hover:underline"
                >
                  #{evidence.issueNumber} {evidence.title}
                </a>
              </li>
            ))}
          </ul>
        </div>
        {params ? (
          <p className="font-mono text-[10px] text-muted-foreground/70">
            {String(params.algorithm ?? "clustering")} · distance_threshold=
            {String(params.distance_threshold ?? "?")} · evidence-backed · no
            causal claims
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
