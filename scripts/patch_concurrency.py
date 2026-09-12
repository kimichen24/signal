"""One-off patch: bounded concurrency in analyze_issue (request scheduling only)."""
from pathlib import Path

path = Path("pipeline/analyze_issue.py")
src = path.read_text(encoding="utf-8")

pairs = []

pairs.append((
    """import argparse
import hashlib
import json
import os
import statistics
import sys
import time
from typing import Any""",
    """import argparse
import hashlib
import json
import os
import statistics
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any""",
))

pairs.append((
    '''    parser.add_argument(
        "--usage-out",''',
    '''    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="max parallel classification requests (default: 4)",
    )
    parser.add_argument(
        "--usage-out",''',
))

old_analysis = (
    '''            rows: list[dict[str, Any]] = []
            for index, issue in enumerate(selected, start=1):
                number = issue["github_issue_number"]
                payload = build_user_payload(issue, min_confidence)
                input_hash = compute_input_hash(payload)
                output: dict[str, Any] | None = None
                error: str | None = None
                try:
                    result = provider.analyze(SYSTEM_PROMPT, payload, schema)
                    output = result.output
                    validation_retries += result.attempts - 1
                    for key in total_usage:
                        total_usage[key] += result.usage.get(key, 0)
                    per_issue_usage.append(
                        {
                            "issue": number,
                            "input_tokens": result.usage.get("input_tokens", 0),
                            "output_tokens": result.usage.get("output_tokens", 0),
                            "validation_attempts": result.attempts,
                            "ok": True,
                        }
                    )
                    print(
                        f"[{index}/{len(selected)}] #{number} ok "
                        f"(attempt {result.attempts}, confidence "
                        f"{output['confidence']}, scope "
                        f"{output['product_scope']})",
                        flush=True,
                    )
                except Exception as exc:  # logged, retried next run
                    error = f"{type(exc).__name__}: {exc}"[:500]
                    failures.append(f"#{number} {error}")
                    per_issue_usage.append(
                        {
                            "issue": number,
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "validation_attempts": 0,
                            "ok": False,
                        }
                    )
                    print(
                        f"[{index}/{len(selected)}] #{number} FAILED: {error}",
                        file=sys.stderr,
                        flush=True,
                    )
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
                rows.append(row)'''
)

new_analysis = (
    '''            rows: list[dict[str, Any]] = []
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
            flush_buffer()'''
)

pairs.append((old_analysis, new_analysis))

pairs.append((
    '''                    issue_by_row = {
                        row["issue_id"]: issue
                        for row, issue in zip(rows, selected)
                    }
                    scope_by_row = {''',
    '''                    issue_by_id = {issue["id"]: issue for issue in selected}
                    scope_by_row = {''',
))

pairs.append((
    '''                    # Copies: never mutate the analysis rows that get upserted.
                    embed_input = [
                        {**row, **(issue_by_row.get(row["issue_id"]) or {})}
                        for row in embeddable
                    ]''',
    '''                    # Copies: never mutate the analysis rows that get upserted.
                    embed_input = [
                        {**row, **issue_by_id.get(row["issue_id"], {})}
                        for row in embeddable
                    ]''',
))

pairs.append((
    '''                    "embedded": embedded_count,
                    "out_of_scope_skipped": out_of_scope_skipped,
                    "embedding_provider": (''',
    '''                    "embedded": embedded_count,
                    "out_of_scope_skipped": out_of_scope_skipped,
                    "api_stats": getattr(provider, "stats", None),
                    "concurrency": args.concurrency,
                    "embedding_provider": (''',
))

pairs.append((
    '''                    "token_usage": total_usage or None,
                    **usage_summary,
                    "failures": failures or None,
                    "notes": notes or None,''',
    '''                    "token_usage": total_usage or None,
                    **usage_summary,
                    "api_stats": getattr(provider, "stats", None),
                    "concurrency": args.concurrency,
                    "failures": failures or None,
                    "notes": notes or None,''',
))

for index, (old, new) in enumerate(pairs, 1):
    if old not in src:
        raise SystemExit(f"pattern {index} not found in {path}")
    src = src.replace(old, new, 1)

path.write_text(src, encoding="utf-8")
print(f"applied {len(pairs)} patches")
