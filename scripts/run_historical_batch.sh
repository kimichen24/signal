#!/usr/bin/env bash
# Historical v0.3.4 batch runner — resumable, one batch per invocation.
# Usage: run_historical_batch.sh <batch-index> [limit] [concurrency]
set -uo pipefail
cd "$(dirname "$0")/.."

BATCH="${1:?batch index required}"
LIMIT="${2:-250}"
CONCURRENCY="${3:-4}"
mkdir -p logs

PENDING=$(.venv/Scripts/python - << 'EOF'
from pipeline.dataset_window import DatasetWindow
from pipeline.supabase_client import SupabaseRest
w = DatasetWindow.from_args("2026-08-23", "2026-09-06T00:00:00Z")
total = SupabaseRest.from_env().count("issues", filters=w.postgrest_filters("github_created_at"))
ok = SupabaseRest.from_env().count("issue_analysis", filters={
    "analysis_version": "eq.v0.3.4", "analysis_error": "is.null"})
print(total - ok)
EOF
)
echo "[$(date -u +%H:%M:%SZ)] batch $BATCH (limit=$LIMIT concurrency=$CONCURRENCY) pending before: $PENDING"
if [ "$PENDING" -eq 0 ]; then
  echo "batch $BATCH: nothing pending — dataset complete"
  exit 0
fi

EMBEDDING_PROVIDER=none .venv/Scripts/python -m pipeline.analyze_issue \
  --limit $LIMIT \
  --concurrency $CONCURRENCY \
  --analysis-version v0.3.4 \
  --start-date 2026-08-23 \
  --snapshot-at 2026-09-06T00:00:00Z \
  --usage-out "logs/hist_usage_b${BATCH}.json" \
  > "logs/hist_batch_${BATCH}.log" 2>&1
STATUS=$?

AFTER=$(.venv/Scripts/python - << 'EOF'
from pipeline.dataset_window import DatasetWindow
from pipeline.supabase_client import SupabaseRest
w = DatasetWindow.from_args("2026-08-23", "2026-09-06T00:00:00Z")
total = SupabaseRest.from_env().count("issues", filters=w.postgrest_filters("github_created_at"))
ok = SupabaseRest.from_env().count("issue_analysis", filters={
    "analysis_version": "eq.v0.3.4", "analysis_error": "is.null"})
print(total - ok)
EOF
)
echo "[$(date -u +%H:%M:%SZ)] batch $BATCH status=$STATUS pending after: $AFTER"
grep -E '"(ok|failed|validation_retries|needs_review_total|input_tokens|output_tokens|runtime_seconds|api_stats|concurrency)"' "logs/hist_batch_${BATCH}.log" | head -14
exit $STATUS
