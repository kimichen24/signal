"""AI structured extraction + embeddings over ingested issues (Prompt 02).

Usage:
  python -m pipeline.analyze_issue --limit 5 [--dry-run]
  python -m pipeline.analyze_issue --limit 100
  python -m pipeline.analyze_issue --embed-only --limit 100

- Classification provider comes from AI_PROVIDER (mimo today); embeddings
  come from an independent provider (EMBEDDING_PROVIDER, e.g. the local
  sentence-transformers model). Embedding text never goes to the
  classification provider.
- Dataset window: start_date <= github_created_at < snapshot_at (recorded
  in analysis_runs).
- Model outputs are validated locally against config/ai_output.schema.json;
  failures are retried with the error included and recorded
  (analysis_error row) after the retry limit.
- Embeddings are generated from a concise semantic representation
  (title/summary/scenario/impact/category/subtopic) and stamped with
  embedding_model. By default out_of_scope rows are NOT embedded —
  downstream clustering excludes them anyway (docs/DECISIONS.md #16);
  pass --include-out-of-scope to embed everything.
- --embed-only is chunked and resumable: each batch is upserted as it
  completes, so an interrupted run continues where it stopped.
- Dry run prints the work count and selected issues but sends no API calls
  and writes nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from pipeline.ai.base import (
    AIConfigError,
    SYSTEM_PROMPT,
    build_providers,
    build_user_payload,
    semantic_text,
    vector_to_postgrest,
)
from pipeline.ai.embeddings import build_embedding_provider
from pipeline.ai.schemas import load_analysis_schema
from pipeline.dataset_window import DatasetWindow, WindowError
from pipeline.normalize import apply_deterministic_overrides
from pipeline.supabase_client import SupabaseConfigError, SupabaseRest

SCHEMA_FIELDS = (
    "issue_type",
    "surface",
    "platform",
    "category",
    "subtopic",
    "user_scenario",
    "user_impact",
    "severity",
    "sentiment",
    "summary",
    "confidence",
    "needs_review",
    "product_scope",
    "scope_confidence",
    "scope_reason",
)

ERROR_ROW_DEFAULTS: dict[str, Any] = {
    "issue_type": "other",
    "surface": "Unknown",
    "platform": "Unknown",
    "category": "Other",
    "subtopic": "analysis pending retry",
    "user_scenario": None,
    "user_impact": None,
    "severity": "low",
    "sentiment": "neutral",
    "summary": "Automatic analysis failed; see analysis_error.",
    "confidence": 0,
    "product_scope": "codex_core",
    "scope_confidence": 0,
    "scope_reason": "Analysis failed before scope could be judged; kept in core pending retry.",
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline.analyze_issue",
        description="AI structured extraction + embeddings (Prompt 02).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="max issues to process in this run (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the work count and selected issues; no API calls, no writes",
    )
    parser.add_argument(
        "--analysis-version",
        default=os.environ.get("SIGNAL_ANALYSIS_VERSION", "v0.3.4"),
        help="analysis_version tag stored with every row",
    )
    parser.add_argument(
        "--start-date",
        default=os.environ.get("SIGNAL_START_DATE"),
        help="dataset window lower bound (YYYY-MM-DD or ISO, inclusive)",
    )
    parser.add_argument(
        "--snapshot-at",
        default=os.environ.get("SIGNAL_SNAPSHOT_AT"),
        help="dataset window upper bound (default: now; recorded in analysis_runs)",
    )
    parser.add_argument(
        "--embed-only",
        action="store_true",
        help="only backfill embeddings for analyzed rows missing them",
    )
    parser.add_argument(
        "--include-out-of-scope",
        action="store_true",
        help="also embed product_scope=out_of_scope rows (skipped by "
        "default; downstream clustering excludes them)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="embedding upsert chunk size (default: 25)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="max parallel classification requests (default: 4)",
    )
    parser.add_argument(
        "--usage-out",
        default=None,
        help="write per-issue token usage JSON to this path instead of "
        "printing it in the summary",
    )
    parser.add_argument(
        "--issue-number",
        type=int,
        action="append",
        dest="issue_numbers",
        default=None,
        help="restrict the run to specific GitHub issue numbers "
        "(repeatable); used for regression reruns",
    )
    return parser


def select_pending(
    supabase: SupabaseRest,
    window: DatasetWindow,
    version: str,
    issue_numbers: list[int] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Issues inside the window vs their analysis state for this version."""
    # Columns below feed BOTH the LLM payload (parsed metadata + cleaned body)
    # and the deterministic normalization layer (parsed_platform, labels).
    issues = supabase.select_paged(
        "issues",
        columns=(
            "id,github_issue_number,title,github_created_at,"
            "parsed_version,parsed_subscription,parsed_platform,"
            "parsed_actual,parsed_steps,parsed_expected,"
            "parsed_additional_info,github_labels,body_clean"
        ),
        filters=window.postgrest_filters("github_created_at"),
        order="github_created_at.desc",
    )
    if issue_numbers:
        wanted = set(issue_numbers)
        issues = [
            issue for issue in issues if issue["github_issue_number"] in wanted
        ]
    analyses = supabase.select_paged(
        "issue_analysis",
        columns="issue_id,analysis_error,embedding",
        filters={"analysis_version": f"eq.{version}"},
    )
    ok_ids: set[str] = set()
    for row in analyses:
        if not row.get("analysis_error"):
            ok_ids.add(row["issue_id"])

    pending = [
        issue
        for issue in issues
        if issue["id"] not in ok_ids  # error rows and unanalyzed both retry
    ]
    stats = {
        "issues_in_window": len(issues),
        "analyzed_ok": len(ok_ids),
        "analyzed_error": sum(
            1 for row in analyses if row.get("analysis_error")
        ),
        "pending": len(pending),
    }
    return pending, stats


def compute_input_hash(payload: str) -> str:
    """Deterministic sha256 of the exact normalized classification payload —
    dataset membership is reproducible via the window; the analysis input is
    auditable via this hash (immune to later upstream GitHub edits)."""
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def usage_stats(values: list[int]) -> dict[str, int | None]:
    if not values:
        return {"min": None, "median": None, "mean": None, "p90": None, "max": None}
    ordered = sorted(values)
    p90_index = min(int(0.9 * len(ordered)), len(ordered) - 1)
    return {
        "min": ordered[0],
        "median": ordered[len(ordered) // 2],
        "mean": round(statistics.mean(ordered)),
        "p90": ordered[p90_index],
        "max": ordered[-1],
    }


def column_exists(supabase: SupabaseRest, table: str, column: str) -> bool:
    try:
        supabase.select(table, columns=column, limit=1)
        return True
    except RuntimeError:
        return False


def model_output_column_available(supabase: SupabaseRest) -> bool:
    """Whether migration 0003 (model_output audit column) is applied."""
    return column_exists(supabase, "issue_analysis", "model_output")


def build_analysis_row(
    issue: dict[str, Any],
    output: dict[str, Any] | None,
    version: str,
    model: str,
    min_confidence: float,
    error: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "issue_id": issue["id"],
        "analysis_version": version,
        "model_name": model,
        "analysis_error": error,
    }
    if output is None:
        row.update(ERROR_ROW_DEFAULTS)
        row["confidence"] = 0
        row["needs_review"] = True
    else:
        for field_name in SCHEMA_FIELDS:
            row[field_name] = output[field_name]
        row["confidence"] = float(output["confidence"])
        row["scope_confidence"] = float(output["scope_confidence"])
        row["needs_review"] = bool(output["needs_review"]) or (
            row["confidence"] < min_confidence
        )
    return row


def frozen_embedding_stamp(env: dict[str, str | None]) -> str | None:
    """Provider:model stamp used for embedding reuse checks."""
    name = (env.get("EMBEDDING_PROVIDER") or "").strip().lower()
    if name == "local":
        return f"local:{(env.get('LOCAL_EMBEDDING_MODEL') or '').strip() or 'intfloat/multilingual-e5-small'}"
    if name == "mimo":
        model = (env.get("MIMO_EMBEDDING_MODEL") or "").strip()
        return f"mimo:{model}" if model else None
    return None


def configured_model_display() -> str:
    provider_name = (os.environ.get("AI_PROVIDER") or "mimo").strip().lower()
    if provider_name == "mimo":
        return (
            os.environ.get("MIMO_CLASSIFICATION_MODEL") or ""
        ).strip() or "mimo-v2.5-pro"
    return (os.environ.get("OPENAI_CLASSIFICATION_MODEL") or "").strip() or "(unset)"


def print_summary(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def select_embed_pending(
    supabase: SupabaseRest,
    version: str,
    include_out_of_scope: bool,
    limit: int,
    frozen_stamp: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """In-scope analyzed rows whose embeddings are missing or stale.

    An embedding is reused only when it exists AND its embedding_model
    matches the frozen stamp. v0.3.4 analysis rows are immutable, so the
    semantic source text cannot drift under a frozen stamp — a matching
    stamp is equivalent protection against recomputation.
    """
    filters = {
        "analysis_version": f"eq.{version}",
        "analysis_error": "is.null",
    }
    if not include_out_of_scope:
        filters["product_scope"] = "neq.out_of_scope"

    def is_pending(row: dict[str, Any]) -> bool:
        if not row.get("embedding"):
            return True  # missing
        if frozen_stamp and row.get("embedding_model") != frozen_stamp:
            return True  # stale: produced by another model/version
        return False

    rows = supabase.select_paged(
        "issue_analysis",
        columns=(
            "issue_id,embedding,embedding_model,summary,user_scenario,"
            "user_impact,category,subtopic,product_scope,issues(title)"
        ),
        filters=filters,
        order="analyzed_at.desc",
    )
    pending = []
    skipped = 0
    for row in rows:
        merged = dict(row)
        merged["title"] = (row.get("issues") or {}).get("title")
        if is_pending(merged):
            pending.append(merged)
        elif not include_out_of_scope and merged.get(
            "product_scope"
        ) == "out_of_scope":
            pass  # valid embedding, excluded from nothing here
    if not include_out_of_scope:
        # out_of_scope rows are skipped BY DEFAULT — count missing/stale
        # ones (rows above already exclude them via the scope filter).
        oos_rows = supabase.select_paged(
            "issue_analysis",
            columns="issue_id,embedding,embedding_model,product_scope",
            filters={
                "analysis_version": f"eq.{version}",
                "analysis_error": "is.null",
                "product_scope": "eq.out_of_scope",
            },
        )
        skipped = sum(1 for r in oos_rows if is_pending(r))
    return pending[:limit], skipped


def embed_in_chunks(
    supabase: SupabaseRest,
    rows: list[dict[str, Any]],
    embedding_provider: Any,
    version: str,
    batch_size: int,
) -> int:
    """Batch-encode, then PATCH each row (embedding + embedding_model only).

    Resumable: every row is committed individually, so an interrupted run
    continues from the remaining embedding IS NULL rows. PATCH (pure
    update) is used instead of upsert because only these two columns
    change; the analysis columns already exist.
    """
    written = 0
    done = 0
    for start in range(0, len(rows), batch_size):
        chunk = rows[start : start + batch_size]
        vectors = embedding_provider.embed(
            [semantic_text(row) for row in chunk]
        )
        for row, vector in zip(chunk, vectors):
            supabase.update(
                "issue_analysis",
                {
                    "issue_id": f"eq.{row['issue_id']}",
                    "analysis_version": f"eq.{version}",
                },
                {
                    "embedding": vector_to_postgrest(vector),
                    "embedding_model": (
                        f"{embedding_provider.name}:"
                        f"{embedding_provider.model}"
                    ),
                },
            )
            written += 1
        done += len(chunk)
        print(f"  embedded {done}/{len(rows)}", flush=True)
    return written


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.limit < 1:
        print("--limit must be >= 1", file=sys.stderr)
        return 1
    if args.batch_size < 1:
        print("--batch-size must be >= 1", file=sys.stderr)
        return 1
    try:
        window = DatasetWindow.from_args(args.start_date, args.snapshot_at)
    except WindowError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    version = args.analysis_version
    min_confidence = float(os.environ.get("SIGNAL_MIN_CONFIDENCE", "0.6"))
    schema = load_analysis_schema()

    try:
        with SupabaseRest.from_env() as supabase:
            pending, stats = select_pending(
                supabase, window, version, args.issue_numbers
            )
            selected = pending[: args.limit]

            if args.dry_run:
                if args.embed_only:
                    embed_pending, skipped_scope = select_embed_pending(
                        supabase, version, args.include_out_of_scope,
                        args.limit,
                        frozen_stamp=frozen_embedding_stamp(os.environ),
                    )
                    print_summary(
                        {
                            "mode": "dry-run embed-only (no calls, no writes)",
                            "analysis_version": version,
                            "embedding_provider": (
                                os.environ.get("EMBEDDING_PROVIDER") or "none"
                            ),
                            "window": window.describe(),
                            "rows_missing_embedding": len(embed_pending),
                            "out_of_scope_skipped": skipped_scope,
                            "batch_size": args.batch_size,
                            "sample": [
                                r["issue_id"] for r in embed_pending[:5]
                            ],
                        }
                    )
                else:
                    print_summary(
                        {
                            "mode": "dry-run (no API calls, nothing written)",
                            "analysis_version": version,
                            "provider": (
                                os.environ.get("AI_PROVIDER") or "mimo"
                            ),
                            "model": configured_model_display(),
                            "window": window.describe(),
                            **stats,
                            "selected": len(selected),
                            "would_send_chat_calls": len(selected),
                            "sample": [
                                {
                                    "issue": issue["github_issue_number"],
                                    "title": issue["title"][:80],
                                }
                                for issue in selected[:10]
                            ],
                        }
                    )
                return 0

            run_started = time.monotonic()
            failures: list[str] = []
            notes: list[str] = []
            embedding_provider = build_embedding_provider(os.environ)
            total_usage = {"input_tokens": 0, "output_tokens": 0}
            per_issue_usage: list[dict[str, Any]] = []
            validation_retries = 0
            written = 0

            if args.embed_only:
                if embedding_provider is None:
                    raise AIConfigError(
                        "EMBEDDING_PROVIDER is not configured (set "
                        "EMBEDDING_PROVIDER=local with LOCAL_EMBEDDING_MODEL)"
                    )
                rows, skipped_scope = select_embed_pending(
                    supabase, version, args.include_out_of_scope, args.limit,
                    frozen_stamp=f"{embedding_provider.name}:{embedding_provider.model}",
                )
                if not rows:
                    print("nothing to embed")
                else:
                    written = embed_in_chunks(
                        supabase, rows, embedding_provider, version,
                        args.batch_size,
                    )
                run_row = {
                    "run_type": "embedding",
                    "analysis_version": version,
                    "model_name": f"{embedding_provider.name}:{embedding_provider.model}",
                    "start_date": window.start_date.isoformat()
                    if window.start_date
                    else None,
                    "snapshot_at": window.snapshot_at.isoformat(),
                    "item_count": written,
                    "params": {
                        "batch_size": args.batch_size,
                        "include_out_of_scope": args.include_out_of_scope,
                        "out_of_scope_skipped": skipped_scope,
                        "dry_run": False,
                        "runtime_seconds": round(
                            time.monotonic() - run_started, 1
                        ),
                    },
                    "error_summary": "; ".join(failures)[:500] or None,
                }
                supabase.insert("analysis_runs", run_row)
                print_summary(
                    {
                        "analysis_version": version,
                        "embedding_provider": embedding_provider.name,
                        "embedding_model": embedding_provider.model,
                        "embedded": written,
                        "out_of_scope_skipped": skipped_scope,
                        "runtime_seconds": round(
                            time.monotonic() - run_started, 1
                        ),
                    }
                )
                return 0

            provider = build_providers(os.environ)
            store_model_output = model_output_column_available(supabase)
            store_input_hash = column_exists(
                supabase, "issue_analysis", "analysis_input_hash"
            )
            if not store_model_output:
                print(
                    "note: model_output column missing — run "
                    "supabase/migrations/0003_model_output_audit.sql to keep "
                    "raw LLM output for audit; continuing without it",
                    file=sys.stderr,
                )
            if not store_input_hash:
                print(
                    "note: analysis_input_hash column missing — run "
                    "supabase/migrations/0007_input_hash.sql so analyses "
                    "are auditable against their exact input",
                    file=sys.stderr,
                )
            rows: list[dict[str, Any]] = []
            pending_buffer: list[dict[str, Any]] = []
            issue_id_by_number = {
                issue["github_issue_number"]: issue["id"] for issue in selected
            }

            def process_issue(issue: dict[str, Any]):
                number = issue["github_issue_number"]
                payload = build_user_payload(issue, min_confidence)
                input_hash = compute_input_hash(payload)
                output: dict[str, Any] | None = None
                error: str | None = None
                attempts = 0
                usage = {"input_tokens": 0, "output_tokens": 0}
                try:
                    result = provider.analyze(SYSTEM_PROMPT, payload, schema)
                    output = result.output
                    attempts = result.attempts
                    usage.update(result.usage)
                except Exception as exc:  # recorded, individually retryable
                    error = f"{type(exc).__name__}: {exc}"[:500]
                final_output = (
                    apply_deterministic_overrides(output, issue)
                    if output is not None
                    else None
                )
                row = build_analysis_row(
                    issue, final_output, version, provider.model,
                    min_confidence, error=error,
                )
                if store_model_output and output is not None:
                    row["model_output"] = output
                if store_input_hash:
                    row["analysis_input_hash"] = input_hash
                entry = {
                    "issue": number,
                    "input_tokens": usage["input_tokens"],
                    "output_tokens": usage["output_tokens"],
                    "validation_attempts": attempts,
                    "ok": error is None,
                    "error": error,
                }
                return row, entry

            def flush_buffer() -> None:
                nonlocal written
                if pending_buffer:
                    written += supabase.upsert(
                        "issue_analysis",
                        pending_buffer,
                        on_conflict="issue_id,analysis_version",
                    )
                    pending_buffer.clear()

            with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
                futures = {
                    executor.submit(process_issue, issue): issue["github_issue_number"]
                    for issue in selected
                }
                for future in as_completed(futures):
                    number = futures[future]
                    try:
                        row, usage_entry = future.result()
                    except Exception as exc:  # defensive: worker itself failed
                        row = build_analysis_row(
                            {"id": issue_id_by_number[number]}, None, version,
                            provider.model, min_confidence,
                            error=f"worker: {type(exc).__name__}: {exc}"[:500],
                        )
                        usage_entry = {
                            "issue": number, "input_tokens": 0,
                            "output_tokens": 0, "validation_attempts": 0,
                            "ok": False, "error": str(exc)[:200],
                        }
                    rows.append(row)
                    pending_buffer.append(row)
                    per_issue_usage.append(usage_entry)
                    if usage_entry["ok"]:
                        validation_retries += usage_entry["validation_attempts"] - 1
                        for key in total_usage:
                            total_usage[key] += usage_entry[key]
                    else:
                        failures.append(f"#{number} {usage_entry.get('error', '')}")
                    if len(pending_buffer) >= 25:
                        flush_buffer()
                    status = "ok" if usage_entry["ok"] else "FAILED"
                    print(f"[{len(rows)}/{len(selected)}] #{number} {status}", flush=True)
            flush_buffer()

            # ---- embeddings (chunked, only after successful analysis) -----
            embedded_count = 0
            out_of_scope_skipped = 0
            if any(row.get("analysis_error") is None for row in rows):
                ok_rows = [
                    row for row in rows if row.get("analysis_error") is None
                ]
                if embedding_provider is None:
                    note = (
                        "no embedding provider configured (set "
                        "EMBEDDING_PROVIDER=local); analyses saved without "
                        "embeddings — re-run --embed-only once configured"
                    )
                    notes.append(note)
                    print(note, file=sys.stderr)
                else:
                    issue_by_id = {issue["id"]: issue for issue in selected}
                    scope_by_row = {
                        row["issue_id"]: row.get("product_scope")
                        for row in ok_rows
                    }
                    embeddable = [
                        row
                        for row in ok_rows
                        if args.include_out_of_scope
                        or scope_by_row.get(row["issue_id"])
                        != "out_of_scope"
                    ]
                    out_of_scope_skipped = len(ok_rows) - len(embeddable)
                    if out_of_scope_skipped:
                        print(
                            f"skipping embeddings for {out_of_scope_skipped} "
                            f"out_of_scope rows (--include-out-of-scope to "
                            f"embed them)",
                            flush=True,
                        )
                    # Copies: never mutate the analysis rows that get upserted.
                    embed_input = [
                        {**row, **issue_by_id.get(row["issue_id"], {})}
                        for row in embeddable
                    ]
                    embedded_count = embed_in_chunks(
                        supabase, embed_input, embedding_provider, version,
                        args.batch_size,
                    )

            if not rows:
                print("nothing to write for this window/version")
                return 0

            written = supabase.upsert(
                "issue_analysis",
                rows,
                on_conflict="issue_id,analysis_version",
            )

            # Aggregates always come from persisted records, never hand counts.
            needs_review_total = supabase.count(
                "issue_analysis",
                filters={
                    "analysis_version": f"eq.{version}",
                    "needs_review": "eq.true",
                },
            )

            run_row = {
                "run_type": "analysis",
                "analysis_version": version,
                "model_name": provider.model,
                "start_date": window.start_date.isoformat()
                if window.start_date
                else None,
                "snapshot_at": window.snapshot_at.isoformat(),
                "item_count": written,
                "params": {
                    "limit": args.limit,
                    "selected": len(selected),
                    "dry_run": False,
                    "issue_numbers": args.issue_numbers,
                    "notes": notes or None,
                    "validation_retries": validation_retries,
                    "embedded": embedded_count,
                    "out_of_scope_skipped": out_of_scope_skipped,
                    "api_stats": getattr(provider, "stats", None),
                    "concurrency": args.concurrency,
                    "embedding_provider": (
                        f"{embedding_provider.name}:{embedding_provider.model}"
                        if embedding_provider
                        else None
                    ),
                    "runtime_seconds": round(
                        time.monotonic() - run_started, 1
                    ),
                    **stats,
                    **(
                        {"token_usage": total_usage}
                        if total_usage["input_tokens"]
                        else {}
                    ),
                },
                "error_summary": "; ".join(failures)[:500] or None,
            }
            supabase.insert("analysis_runs", run_row)

            ok_usage = [u for u in per_issue_usage if u["ok"]]
            usage_summary = {
                "input_tokens_per_issue": usage_stats(
                    [u["input_tokens"] for u in ok_usage]
                ),
                "output_tokens_per_issue": usage_stats(
                    [u["output_tokens"] for u in ok_usage]
                ),
            }
            if args.usage_out:
                with open(args.usage_out, "w", encoding="utf-8") as handle:
                    json.dump(
                        {
                            "analysis_version": version,
                            "provider": provider.name,
                            "model": provider.model,
                            "total_usage": total_usage,
                            "per_issue": per_issue_usage,
                        },
                        handle,
                        indent=2,
                    )
                print(f"per-issue usage written to {args.usage_out}")

            print_summary(
                {
                    "analysis_version": version,
                    "provider": provider.name,
                    "model": provider.model,
                    "window": window.describe(),
                    "written": written,
                    "ok": sum(
                        1 for r in rows if r.get("analysis_error") is None
                    ),
                    "failed": len(failures),
                    "validation_retries": validation_retries,
                    "embedded": embedded_count,
                    "needs_review_total": needs_review_total,
                    "runtime_seconds": round(time.monotonic() - run_started, 1),
                    "token_usage": total_usage or None,
                    **usage_summary,
                    "api_stats": getattr(provider, "stats", None),
                    "concurrency": args.concurrency,
                    "failures": failures or None,
                    "notes": notes or None,
                }
            )
            return 0
    except (SupabaseConfigError, AIConfigError, RuntimeError, ValueError) as exc:
        print(f"Analysis failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    from pipeline.supabase_client import load_env

    load_env()
    raise SystemExit(main())
