import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/empty-state";
import { getRecentIssues } from "@/lib/supabase/queries";

export const dynamic = "force-dynamic";

export const metadata = { title: "Feedback" };

export default async function FeedbackPage() {
  const { configured, error, rows } = await getRecentIssues(10);

  return (
    <div className="space-y-8">
      <header className="space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          Feedback
        </p>
        <h1 className="text-3xl font-semibold tracking-tight">Feedback</h1>
        <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
          Individual GitHub issues with structured analysis: surface, platform,
          category, subtopic and AI-estimated severity. Filters and the detail
          drawer are delivered with the ingestion prompt.
        </p>
      </header>

      {!configured ? (
        <EmptyState
          title="Database not configured"
          description="Create .env.local from .env.example and set the Supabase URL and service-role key, then run supabase/schema.sql."
          hint="NEXT_PUBLIC_SUPABASE_URL · SUPABASE_SERVICE_ROLE_KEY"
        />
      ) : error ? (
        <EmptyState
          title="Database query failed"
          description={`The issues table could not be read. (${error})`}
          hint="Run supabase/schema.sql against your Supabase project"
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No feedback imported yet"
          description="Run the GitHub ingestion pipeline to import real issues from the configured repository. Only issues are collected — PRs are filtered out — and raw issue bodies are preserved."
          hint="prompts/01_DATA_INGESTION.md"
        />
      ) : (
        <section className="space-y-3">
          <p className="text-xs text-muted-foreground">
            Latest {rows.length} ingested issue{rows.length === 1 ? "" : "s"} —
            the full list with filters arrives with Prompt 01.
          </p>
          <div className="overflow-hidden rounded-lg border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-card/50 text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-4 py-2.5 font-medium">Issue</th>
                  <th className="px-4 py-2.5 font-medium">Title</th>
                  <th className="px-4 py-2.5 font-medium">State</th>
                  <th className="px-4 py-2.5 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b last:border-0">
                    <td className="px-4 py-2.5 tabular-nums text-muted-foreground">
                      #{row.github_issue_number}
                    </td>
                    <td className="max-w-md truncate px-4 py-2.5">
                      <a
                        href={row.github_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline-offset-4 hover:underline"
                      >
                        {row.title}
                      </a>
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge variant="outline">{row.state ?? "unknown"}</Badge>
                    </td>
                    <td className="px-4 py-2.5 tabular-nums text-muted-foreground">
                      {row.github_created_at.slice(0, 10)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
