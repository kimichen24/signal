import { EmptyState } from "@/components/empty-state";
import { getReleasesData } from "@/lib/data-adapter";
import { getClusterDisplayName } from "@/lib/cluster-labels";

export const metadata = { title: "版本影响" };

function BarComparison({
  before,
  after,
  max,
}: {
  before: number;
  after: number;
  max: number;
}) {
  const beforeWidth = max > 0 ? Math.max((before / max) * 100, 2) : 2;
  const afterWidth = max > 0 ? Math.max((after / max) * 100, 2) : 2;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-3 text-sm">
        <span className="w-14 shrink-0 text-xs text-muted-foreground">
          发布前
        </span>
        <span className="relative h-2 flex-1 overflow-hidden rounded-full bg-secondary">
          <span
            className="absolute inset-y-0 left-0 rounded-full bg-foreground/20"
            style={{ width: `${beforeWidth}%` }}
          />
        </span>
        <span className="w-10 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
          {before}
        </span>
      </div>
      <div className="flex items-center gap-3 text-sm">
        <span className="w-14 shrink-0 text-xs text-muted-foreground">
          发布后
        </span>
        <span className="relative h-2 flex-1 overflow-hidden rounded-full bg-secondary">
          <span
            className="absolute inset-y-0 left-0 rounded-full bg-primary/40"
            style={{ width: `${afterWidth}%` }}
          />
        </span>
        <span className="w-10 shrink-0 text-right text-xs tabular-nums text-foreground">
          {after}
        </span>
      </div>
    </div>
  );
}

export default async function ReleasesPage() {
  const { configured, error, rows } = await getReleasesData();

  const sufficientCount = rows.filter((r) => r.sufficientHistory).length;
  const insufficientCount = rows.filter((r) => !r.sufficientHistory).length;

  return (
    <div className="space-y-12">
      {/* Header */}
      <header className="space-y-3">
        <p className="text-xs font-medium tracking-wide text-muted-foreground">
          版本影响
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          版本影响
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          对比公开版本发布前后的真实用户反馈变化，识别值得进一步调查的关联信号。
        </p>
        <p className="text-xs text-muted-foreground">
          相关性不代表因果关系
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="数据库未配置"
          description="请配置 Supabase 连接以查看版本影响数据。"
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_ANON_KEY"
        />
      ) : error ? (
        <EmptyState
          title="数据库查询失败"
          description={`版本数据读取未成功，请检查配置后重试。(${error})`}
          hint="运行 python -m pipeline.releases 导入真实公开版本"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="尚未记录版本事件"
          description="版本事件从官方公开发布说明导入，每条都带有 source_url 溯源链接。"
          hint="python -m pipeline.releases"
        />
      ) : (
        <section>
          {/* Summary strip */}
          <div className="mb-8 flex flex-wrap items-baseline gap-x-8 gap-y-2 text-sm">
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular-nums text-foreground">
                {rows.length}
              </span>
              <span className="text-xs text-muted-foreground">公开版本</span>
            </div>
            <div className="hidden h-5 w-px bg-border sm:block" />
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular-nums text-foreground">
                {sufficientCount}
              </span>
              <span className="text-xs text-muted-foreground">可比较</span>
            </div>
            <div className="hidden h-5 w-px bg-border sm:block" />
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold tabular-nums text-muted-foreground">
                {insufficientCount}
              </span>
              <span className="text-xs text-muted-foreground">历史数据不足</span>
            </div>
          </div>

          {/* Timeline */}
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-[7px] top-3 bottom-3 w-px bg-border" />

            <div className="space-y-10">
              {rows.map((release) => {
                const dateStr = release.releaseDate.slice(0, 10);
                const maxCount = Math.max(
                  release.totalBefore,
                  release.totalAfter,
                  1
                );

                return (
                  <div key={release.id} className="relative pl-8">
                    {/* Timeline dot */}
                    <div className="absolute left-0 top-1.5 size-[15px] rounded-full border-2 border-primary bg-background" />

                    {/* Date */}
                    <p className="text-xs tabular-nums text-muted-foreground">
                      {dateStr}
                    </p>

                    {/* Release name + link */}
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                      <a
                        href={release.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium text-foreground underline-offset-4 hover:underline"
                      >
                        {release.name}
                      </a>
                      <a
                        href={release.sourceUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-primary underline-offset-4 hover:underline"
                      >
                        GitHub Release →
                      </a>
                    </div>

                    {/* Content based on sufficiency */}
                    {release.sufficientHistory && release.hasImpact ? (
                      <div className="mt-4 max-w-md space-y-3">
                        <BarComparison
                          before={release.totalBefore}
                          after={release.totalAfter}
                          max={maxCount}
                        />

                        {release.totalBefore === release.totalAfter ? (
                          <p className="text-xs text-muted-foreground">
                            发布前后相关反馈量保持稳定，未观察到可报告的变化。
                          </p>
                        ) : release.totalAfter > release.totalBefore ? (
                          <p className="text-xs text-muted-foreground">
                            该版本发布后，相关反馈有所增加，值得进一步调查。
                          </p>
                        ) : (
                          <p className="text-xs text-muted-foreground">
                            该版本发布后，相关反馈有所减少。
                          </p>
                        )}

                        <p className="text-[11px] text-muted-foreground">
                          {release.impactedClusters} 个问题簇参与对比
                        </p>

                        {/* Top impacted clusters */}
                        {release.topClusters.length > 0 ? (
                          <div className="space-y-1.5 pt-1">
                            {release.topClusters.map((cluster) => {
                              const displayName = getClusterDisplayName({
                                clusterKey: cluster.clusterKey,
                                name: cluster.clusterName,
                              });
                              return (
                                <div
                                  key={cluster.clusterId}
                                  className="flex items-center gap-2 text-xs"
                                >
                                  <span className="min-w-0 flex-1 truncate text-muted-foreground">
                                    {displayName}
                                  </span>
                                  <span className="shrink-0 tabular-nums text-muted-foreground">
                                    {cluster.beforeCount} →{" "}
                                    {cluster.afterCount}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        ) : null}
                      </div>
                    ) : (
                      <div className="mt-4 max-w-md rounded-lg border border-dashed border-border p-4">
                        <p className="text-sm font-medium text-foreground">
                          历史数据不足
                        </p>
                        <p className="mt-1 text-xs leading-5 text-muted-foreground">
                          当前数据窗口无法完整覆盖该版本发布前后的比较周期，因此暂不进行前后趋势判断。
                        </p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Methodology disclosure */}
          <details className="mt-12 text-xs text-muted-foreground">
            <summary className="cursor-pointer hover:text-foreground">
              方法说明
            </summary>
            <div className="mt-3 space-y-1 pl-4">
              <p>
                版本来源：GitHub 官方公开 Release，每条带有 source_url 溯源链接。
              </p>
              <p>
                比较窗口：版本发布日期前7天和后7天，裁剪至数据集边界（2026-08-23 →
                2026-09-06）。
              </p>
              <p>
                覆盖保障：任一侧覆盖不足 5 天的比较标记为历史数据不足。
              </p>
              <p>
                相关性 ≠ 因果关系：反馈量在版本发布后变化仅值得进一步调查，不代表版本与问题之间存在因果关系。
              </p>
              <p>
                数据集：codex-14d-2026-09-06 · 仅真实 GitHub Issues（PR 已过滤）。
              </p>
            </div>
          </details>
        </section>
      )}
    </div>
  );
}
