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
  investigate_now: { label: "立即调查", variant: "destructive" },
  validate: { label: "待验证", variant: "warning" },
  monitor: { label: "持续观察", variant: "secondary" },
  low_priority: { label: "低优先级", variant: "outline" },
};

const STATE_WARNING: Record<string, string> = {
  new_signal: "新信号——无历史基线，增长率不适用",
  low_base_acceleration:
    "低基数（前期仅 1–2 条观测）——原始增长率仅作参考信息展示",
};

const WEIGHT_LABEL: Record<string, string> = {
  frequency: "反馈频次",
  severity: "严重度",
  signal: "信号强度",
  engagement: "互动度",
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
            <Badge variant="destructive">新兴</Badge>
          ) : null}
          {opportunity.needsRefinement ? (
            <Badge variant="warning">需进一步细化</Badge>
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
            {opportunity.category} · {opportunity.size} 条 ·{" "}
            {opportunity.current} 当前周期
          </span>
          <span>
            Investigation Priority:{" "}
            <span className="font-medium text-foreground/80">
              {Math.round(opportunity.priority * 100)}
            </span>
          </span>
        </div>

        <div className="rounded-md border p-3">
          <p className="font-medium text-foreground/80">为什么得到这个优先级？</p>
          <div className="mt-1 grid gap-x-6 gap-y-0.5 sm:grid-cols-2">
            {Object.entries(opportunity.weights).map(([key, weight]) => (
              <span key={key}>
                {WEIGHT_LABEL[key] ?? key}: {Pct(opportunity.components[key] ?? null)} ×{" "}
                {Math.round((weight as number) * 100)}%
              </span>
            ))}
          </div>
          {opportunity.trendState ? (
            <p className="mt-1">
              信号状态：{opportunity.trendState}
              {opportunity.signalScore !== null
                ? ` （信号分 ${opportunity.signalScore}）`
                : ""}
            </p>
          ) : null}
          {!opportunity.engagementAvailable ? (
            <p className="mt-1 text-warning">
              互动数据过少，评分已在去除互动度后重新归一化
            </p>
          ) : null}
        </div>

        {warning ? (
          <p className="text-warning">⚠ 低基数警告：{warning}</p>
        ) : null}
        {opportunity.needsRefinement ? (
          <p className="text-warning">
            ⚠ 宽泛问题族——简报建议进行族级调查，而非指向某个具体修复
          </p>
        ) : null}

        {brief ? (
          <div className="space-y-2">
            {brief.product_hypothesis ? (
              <p>
                <span className="font-medium text-foreground/80">
                  产品假设（未验证）：{" "}
                </span>
                {brief.product_hypothesis}
              </p>
            ) : null}
            {brief.recommended_investigation ? (
              <p>
                <span className="font-medium text-foreground/80">
                  建议调查：{" "}
                </span>
                {brief.recommended_investigation}
              </p>
            ) : null}
            {brief.suggested_validation ? (
              <p>
                <span className="font-medium text-foreground/80">
                  待验证:{" "}
                </span>
                {brief.suggested_validation}
              </p>
            ) : null}
            {brief.metrics_to_monitor?.length ? (
              <p>
                <span className="font-medium text-foreground/80">
                  持续观察:{" "}
                </span>
                {brief.metrics_to_monitor.join(" · ")}
              </p>
            ) : null}
          </div>
        ) : null}

        {opportunity.representatives.length ? (
          <div>
            <p className="font-medium text-foreground/80">
              代表性证据
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
