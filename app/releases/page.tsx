import { EmptyState } from "@/components/empty-state";
import { getReleases } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "版本影响" };

export default async function ReleasesPage() {
  const { configured, error, rows } = await getReleases();

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          版本影响
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">版本影响</h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          Public Codex releases (authoritative GitHub source URLs) compared
          against in-scope feedback volume 前 and 后 each release.
          Signal reports <strong>相关性</strong> — related feedback
          increasing 后 a release 值得进一步调查; it never
          establishes 因果. Windows are ±7 days clipped to the dataset
          bounds (2026-08-23 → 2026-09-06); comparisons below 5 days of
          coverage on either side are marked insufficient.
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="数据库未配置"
          description="请从 .env.example 创建 .env.local，填入 Supabase URL 和 anon key。"
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY"
        />
      ) : error ? (
        <EmptyState
          title="数据库查询失败"
          description={`The releases table could not be read. (${error})`}
          hint="运行 python -m pipeline.releases 导入真实公开版本"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="尚未记录版本事件"
          description="版本事件从官方公开发布说明导入，每条都带有 source_url 溯源链接。"
          hint="python -m pipeline.releases"
        />
      ) : (
        <section className="space-y-3">
          {rows.map((release) => (
            <div
              key={release.id}
              className="rounded-lg border px-4 py-3 text-sm"
            >
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <a
                  href={release.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-medium underline-offset-4 hover:underline"
                >
                  {release.name}
                </a>
                <span className="tabular-nums text-xs text-muted-foreground">
                  {release.releaseDate.slice(0, 10)}
                </span>
                {release.hasImpact ? (
                  <span className="text-xs text-muted-foreground">
                    有效反馈： {release.beforeTotal} 前 → {" "}
                    {release.afterTotal} 后 · {release.clustersImpacted}{" "}
                    个问题簇比对
                  </span>
                ) : (
                  <span className="text-xs text-warning">
                    历史数据不足 — temporal coverage in this dataset
                    is incomplete for a ±7 day comparison
                  </span>
                )}
              </div>
              {release.hasImpact ? (
                <p className="mt-1 text-xs text-muted-foreground">
                  Where related feedback increased 后 this release, it
                  值得进一步调查 — this is a 相关性 observation,
                  not a causal claim.
                </p>
              ) : null}
            </div>
          ))}
        </section>
      )}
    </div>
  );
}
