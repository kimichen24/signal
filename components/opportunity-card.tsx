import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { Opportunity } from "@/lib/supabase/queries";

const ACTION_LABEL: Record<string, { label: string; variant: "destructive" | "warning" | "secondary" | "outline" }> = {
  investigate_now: { label: "Investigate Now", variant: "destructive" },
  validate: { label: "Validate", variant: "warning" },
  monitor: { label: "Monitor", variant: "secondary" },
  low_priority: { label: "Low Priority", variant: "outline" },
};

const STATE_WARNING: Record<string, string> = {
  new_signal: "new signal — no baseline, growth % not applicable",
  low_base_acceleration:
    "low baseline (1–2 previous) — raw growth shown as metadata only",
};

function Pct(value: number | null): string {
  return value === null ? "—" : `${Math.round(value * 100)}%`;
}

export function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  const action = ACTION_LABEL[opportunity.action] ?? {
    label: opportunity.action,
    variant: "outline" as const,
  };
  const brief = opportunity.brief;
  const warning = STATE_WARNING[opportunity.trendState ?? ""];

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <CardTitle className="text-sm">{opportunity.name}</CardTitle>
          <Badge variant={action.variant} className="ml-auto">
            {action.label}
          </Badge>
          {opportunity.isEmerging ? (
            <Badge variant="destructive">Emerging</Badge>
          ) : null}
          {opportunity.needsRefinement ? (
            <Badge variant="warning">needs refinement</Badge>
          ) : null}
        </div>
        {brief?.what_changed ? (
          <CardDescription className="leading-6">
            {brief.what_changed}
          </CardDescription>
        ) : null}
      </CardHeader>
      <CardContent className="space-y-3 text-xs text-muted-foreground">
        <div className="flex flex-wrap gap-x-6 gap-y-1">
          <span>
            {opportunity.category} · {opportunity.size} issues ·{" "}
            {opportunity.current} in current period
          </span>
          <span>
            Investigation Priority:{" "}
            <span className="font-medium text-foreground/80">
              {Math.round(opportunity.priority * 100)}
            </span>
          </span>
        </div>

        <div className="rounded-md border p-3">
          <p className="font-medium text-foreground/80">Why this score?</p>
          <div className="mt-1 grid gap-x-6 gap-y-0.5 sm:grid-cols-2">
            {Object.entries(opportunity.weights).map(([key, weight]) => (
              <span key={key}>
                {key}: {Pct(opportunity.components[key] ?? null)} ×{" "}
                {Math.round((weight as number) * 100)}%
              </span>
            ))}
          </div>
          {opportunity.trendState ? (
            <p className="mt-1">
              signal state: {opportunity.trendState}
              {opportunity.signalScore !== null
                ? ` (score ${opportunity.signalScore})`
                : ""}
            </p>
          ) : null}
          {!opportunity.engagementAvailable ? (
            <p className="mt-1 text-warning">
              engagement too sparse — renormalized without it
            </p>
          ) : null}
        </div>

        {warning ? (
          <p className="text-warning">⚠ low baseline: {warning}</p>
        ) : null}
        {opportunity.needsRefinement ? (
          <p className="text-warning">
            ⚠ broad problem family — brief recommends family-level
            investigation, not a specific fix
          </p>
        ) : null}

        {brief ? (
          <div className="space-y-2">
            {brief.product_hypothesis ? (
              <p>
                <span className="font-medium text-foreground/80">
                  Hypothesis (unvalidated):{" "}
                </span>
                {brief.product_hypothesis}
              </p>
            ) : null}
            {brief.recommended_investigation ? (
              <p>
                <span className="font-medium text-foreground/80">
                  Investigate:{" "}
                </span>
                {brief.recommended_investigation}
              </p>
            ) : null}
            {brief.suggested_validation ? (
              <p>
                <span className="font-medium text-foreground/80">
                  Validate:{" "}
                </span>
                {brief.suggested_validation}
              </p>
            ) : null}
            {brief.metrics_to_monitor?.length ? (
              <p>
                <span className="font-medium text-foreground/80">
                  Monitor:{" "}
                </span>
                {brief.metrics_to_monitor.join(" · ")}
              </p>
            ) : null}
          </div>
        ) : null}

        {opportunity.representatives.length ? (
          <div>
            <p className="font-medium text-foreground/80">
              Representative evidence
            </p>
            <ul className="mt-1 space-y-1">
              {opportunity.representatives.map((evidence) => (
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
        ) : null}
      </CardContent>
    </Card>
  );
}
