import { getClusterDisplayName } from "@/lib/cluster-labels";
import type { Brief, Insight, Opportunity } from "@/lib/supabase/queries";

/**
 * Presentation-only Chinese copy for Signal-generated narratives.
 * Persisted model output remains available in the database and snapshots.
 */

function clusterLabel({ clusterKey, name }: Pick<Opportunity, "clusterKey" | "name">): string {
  return getClusterDisplayName({ clusterKey, name });
}

type TrendDirection = "new" | "increase" | "decrease" | "stable";

function recommendationFor(
  action: string | null | undefined,
  direction: TrendDirection
): string {
  switch (action) {
    case "investigate_now":
      return "仍值得优先调查。";
    case "validate":
      return "建议优先验证影响与复现条件。";
    case "monitor":
      return "建议持续观察后续趋势。";
    case "low_priority":
      return "当前优先级较低，可在后续资源允许时留意。";
    default:
      if (direction === "increase") return "该增长将作为后续优先级判断的参考。";
      if (direction === "decrease") return "该回落将作为后续优先级判断的参考。";
      if (direction === "new") return "该新增信号将作为后续优先级判断的参考。";
      return "该变化将作为后续优先级判断的参考。";
  }
}

function investigationRecommendation(opportunity: Opportunity): string {
  const scope = `${opportunity.size} 条反馈按版本、平台和触发场景拆分`;
  switch (opportunity.action) {
    case "investigate_now":
      return `建议优先将 ${scope}，复核代表性 Issue，再定位是否存在共同失败模式。`;
    case "validate":
      return `建议先将 ${scope}，复核代表性 Issue，验证影响范围与复现条件。`;
    case "monitor":
      return `建议持续跟踪这 ${opportunity.size} 条反馈，待趋势变化时再按版本、平台和触发场景拆分核查。`;
    case "low_priority":
      return `当前优先级较低，可在后续资源允许时将 ${scope}，用于持续观察。`;
    default:
      return `建议将 ${scope}，复核代表性 Issue，再定位是否存在共同失败模式。`;
  }
}

function changeNarrative({
  clusterKey,
  name,
  size,
  current,
  previous,
  action,
}: Pick<Opportunity, "clusterKey" | "name" | "size" | "current" | "previous"> & {
  action?: string | null;
}): string {
  const label = clusterLabel({ clusterKey, name });
  if (previous === 0 && current > 0) {
    return `问题簇“${label}”在当前周期出现 ${current} 条反馈，上一周期未观察到相关记录，${recommendationFor(action, "new")}`;
  }
  if (current > previous) {
    return `问题簇“${label}”的反馈量从上一周期的 ${previous} 条增加到当前周期的 ${current} 条，${recommendationFor(action, "increase")}`;
  }
  if (current < previous) {
    return `问题簇“${label}”的反馈量从上一周期的 ${previous} 条降至当前周期的 ${current} 条，但累计已有 ${size} 条反馈，${recommendationFor(action, "decrease")}`;
  }
  return `问题簇“${label}”在前后两个周期均有 ${current} 条反馈，暂未观察到明显变化，${recommendationFor(action, "stable")}`;
}

export function getChineseInsightNarrative(insight: Insight): string {
  return changeNarrative({
    clusterKey: insight.clusterKey,
    name: insight.name,
    size: insight.issueCount,
    current: insight.currentPeriodCount ?? insight.issueCount,
    previous: insight.previousPeriodCount ?? 0,
  });
}

function chineseBriefCopy(opportunity: Opportunity): Brief {
  const original = opportunity.brief;
  if (!original || Object.keys(original).length === 0) return {};

  const copy: Brief = {};
  if (original.what_changed !== undefined) {
    copy.what_changed = changeNarrative(opportunity);
  }
  if (original.evidence_summary !== undefined) {
    copy.evidence_summary = `该问题簇关联 ${opportunity.size} 条真实 GitHub Issue；下方代表性 Issue 提供原始证据，需结合具体版本、平台和触发场景进一步核查。`;
  }
  if (original.product_hypothesis !== undefined) {
    copy.product_hypothesis = `初步假设：问题可能集中在“${clusterLabel(opportunity)}”对应的产品链路；该假设尚未验证，需要结合代表性 Issue 与复现结果检验。`;
  }
  if (original.recommended_investigation !== undefined) {
    copy.recommended_investigation = investigationRecommendation(opportunity);
  }
  if (original.suggested_validation !== undefined) {
    copy.suggested_validation = "验证方案：在受影响的端与平台复现代表性 Issue 描述的关键路径，并比较成功率、错误率和恢复情况。";
  }
  if (original.metrics_to_monitor !== undefined) {
    const metrics = [
      "相关反馈量与新增量",
      "关键操作成功率与错误率",
      "重复出现的 Issue 数量",
    ];
    copy.metrics_to_monitor = original.metrics_to_monitor.map(
      (_, index) => metrics[index] ?? "相关问题的反馈与失败趋势"
    );
  }
  if (original.affected_workflow !== undefined) {
    copy.affected_workflow = `与“${clusterLabel(opportunity)}”相关的产品操作流程`;
  }
  if (original.affected_surface_platform !== undefined) {
    copy.affected_surface_platform = "涉及该问题簇对应的端与平台，详见下方代表性证据";
  }
  return copy;
}

export function getChineseBrief(opportunity: Opportunity): Brief | null {
  if (!opportunity.brief) return null;
  return chineseBriefCopy(opportunity);
}
