"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  ISSUE_TYPE,
  CATEGORY,
  SURFACE,
  PLATFORM,
  SEVERITY,
  SCOPE,
} from "@/lib/labels";
import type { FeedbackInboxItem } from "@/lib/supabase/queries";
import { cn } from "@/lib/utils";

/* ── Severity variant mapping ─────────────────────────────────── */
const SEV_VARIANT: Record<
  string,
  "destructive" | "warning" | "secondary" | "outline"
> = {
  critical: "destructive",
  high: "warning",
  medium: "secondary",
  low: "outline",
};

/* ── Detail pane ──────────────────────────────────────────────── */

function FeedbackDetail({
  item,
  onBack,
}: {
  item: FeedbackInboxItem;
  onBack?: () => void;
}) {
  const a = item.analysis;

  return (
    <div className="space-y-8">
      {/* Back button — mobile only */}
      {onBack ? (
        <button
          onClick={onBack}
          className="text-sm text-muted-foreground hover:text-foreground md:hidden"
        >
          ← 返回列表
        </button>
      ) : null}

      {/* Issue header */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm tabular-nums text-muted-foreground">
            #{item.issueNumber}
          </span>
          <a
            href={item.githubUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-primary underline-offset-4 hover:underline"
          >
            查看 GitHub 原始证据 →
          </a>
        </div>
        <h2 className="text-base font-medium leading-6 text-foreground">
          {item.title}
        </h2>
      </div>

      {/* Structured understanding */}
      {a ? (
        <>
          <div>
            <h3 className="mb-4 text-xs font-medium tracking-wide text-muted-foreground">
              Signal 结构化理解
            </h3>
            <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
              <LabelCell
                label="问题类型"
                value={ISSUE_TYPE[a.issueType] ?? a.issueType}
              />
              <LabelCell
                label="问题类别"
                value={CATEGORY[a.category] ?? a.category}
              />
              <LabelCell
                label="使用端"
                value={SURFACE[a.surface] ?? a.surface}
              />
              <LabelCell
                label="平台"
                value={PLATFORM[a.platform] ?? a.platform}
              />
              <LabelCell
                label="AI 估算严重度"
                value={SEVERITY[a.severity] ?? a.severity}
                badge
                variant={SEV_VARIANT[a.severity] ?? "outline"}
              />
              <LabelCell
                label="产品范围"
                value={SCOPE[a.productScope] ?? a.productScope}
              />
            </div>
          </div>

          {/* Analysis summary */}
          {a.summary ? (
            <p className="text-sm leading-6 text-muted-foreground">
              {a.summary}
            </p>
          ) : null}

          {/* Narrative fields */}
          <div className="space-y-4">
            {a.userScenario ? (
              <div>
                <p className="text-xs font-medium text-foreground/80">
                  用户场景
                </p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {a.userScenario}
                </p>
              </div>
            ) : null}
            {a.userImpact ? (
              <div>
                <p className="text-xs font-medium text-foreground/80">
                  用户影响
                </p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {a.userImpact}
                </p>
              </div>
            ) : null}
            {a.scopeReason ? (
              <div>
                <p className="text-xs font-medium text-foreground/80">
                  范围判断
                </p>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">
                  {a.scopeReason}
                </p>
              </div>
            ) : null}
          </div>

          {/* Quiet metadata */}
          <div className="flex flex-wrap gap-x-4 text-[11px] text-muted-foreground">
            <span>模型置信度 {Math.round(a.confidence * 100)}%</span>
            {a.needsReview ? <span className="text-warning">建议人工复核</span> : null}
            <span>{a.analyzedAt.slice(0, 10)}</span>
          </div>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">
          该反馈尚无结构化分析。
        </p>
      )}
    </div>
  );
}

/* ── Label cell ────────────────────────────────────────────────── */

function LabelCell({
  label,
  value,
  badge,
  variant,
}: {
  label: string;
  value: string;
  badge?: boolean;
  variant?: "destructive" | "warning" | "secondary" | "outline";
}) {
  return (
    <div>
      <p className="text-[11px] text-muted-foreground">{label}</p>
      {badge ? (
        <Badge variant={variant ?? "outline"} className="mt-0.5">
          {value}
        </Badge>
      ) : (
        <p className="mt-0.5 text-sm text-foreground">{value}</p>
      )}
    </div>
  );
}

/* ── Inbox component ──────────────────────────────────────────── */

export function FeedbackInbox({ items }: { items: FeedbackInboxItem[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(
    items[0]?.id ?? null
  );
  const [mobileShowDetail, setMobileShowDetail] = useState(false);

  const selectedItem = items.find((i) => i.id === selectedId) ?? null;

  function selectItem(id: string) {
    setSelectedId(id);
    setMobileShowDetail(true);
  }

  function backToList() {
    setMobileShowDetail(false);
  }

  return (
    <div className="flex h-[calc(100vh-8rem)] flex-col md:flex-row md:gap-0">
      {/* ── Left pane: inbox list ──────────────────────────────── */}
      <div
        className={cn(
          "w-full shrink-0 overflow-y-auto border-r border-border md:w-80 lg:w-96",
          mobileShowDetail ? "hidden md:block" : "block"
        )}
      >
        <div className="divide-y divide-border">
          {items.map((item) => {
            const isSelected = item.id === selectedId;
            return (
              <button
                key={item.id}
                onClick={() => selectItem(item.id)}
                className={cn(
                  "flex w-full flex-col gap-1 px-4 py-3 text-left transition-colors",
                  isSelected
                    ? "bg-primary/5"
                    : "hover:bg-secondary/50"
                )}
              >
                <div className="flex items-center gap-2">
                  <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                    #{item.issueNumber}
                  </span>
                  {item.analysis ? (
                    <Badge
                      variant={
                        SEV_VARIANT[item.analysis.severity] ?? "outline"
                      }
                      className="shrink-0"
                    >
                      {SEVERITY[item.analysis.severity] ??
                        item.analysis.severity}
                    </Badge>
                  ) : null}
                </div>
                <p className="line-clamp-2 text-sm leading-5 text-foreground">
                  {item.title}
                </p>
                <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
                  {item.platform ? (
                    <span>{PLATFORM[item.platform] ?? item.platform}</span>
                  ) : null}
                  {item.analysis ? (
                    <span>
                      {CATEGORY[item.analysis.category] ??
                        item.analysis.category}
                    </span>
                  ) : null}
                  <span className="ml-auto">
                    {item.createdAt.slice(0, 10)}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Right pane: detail ─────────────────────────────────── */}
      <div
        className={cn(
          "min-w-0 flex-1 overflow-y-auto border-l-2 border-l-primary/20 px-6 py-6 md:block lg:px-10",
          mobileShowDetail ? "block" : "hidden md:block"
        )}
      >
        {selectedItem ? (
          <FeedbackDetail
            item={selectedItem}
            onBack={mobileShowDetail ? backToList : undefined}
          />
        ) : (
          <p className="text-sm text-muted-foreground">
            请从左侧选择一条反馈。
          </p>
        )}
      </div>
    </div>
  );
}
