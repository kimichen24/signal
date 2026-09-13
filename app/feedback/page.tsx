import { EmptyState } from "@/components/empty-state";
import { FeedbackInbox } from "@/components/feedback-inbox";
import { getFeedbackInbox } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "反馈" };

export default async function FeedbackPage() {
  const { configured, error, rows } = await getFeedbackInbox(20);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <p className="text-xs font-medium tracking-wide text-muted-foreground">
          反馈
        </p>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          反馈智能工作台
        </h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          从原始 GitHub Issue 到 Signal 结构化理解。
          左侧选择一条反馈，右侧查看 AI 分析结果。
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="数据库未配置"
          description="请配置 Supabase 连接以查看反馈数据。"
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_ANON_KEY"
        />
      ) : error ? (
        <EmptyState
          title="数据库查询失败"
          description={`反馈数据读取未成功，请检查配置后重试。(${error})`}
          hint="在 Supabase 项目中执行 supabase/schema.sql"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="尚未导入反馈"
          description="请运行 GitHub 采集流水线，从配置的仓库导入真实 Issues。"
          hint="prompts/01_DATA_INGESTION.md"
        />
      ) : (
        <FeedbackInbox items={rows} />
      )}
    </div>
  );
}
