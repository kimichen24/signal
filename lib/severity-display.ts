export function formatClusterSeverity(score: number | null | undefined): string {
  return score == null
    ? "簇平均 AI 严重度：—"
    : `簇平均 AI 严重度：${score.toFixed(2)} / 1`;
}
