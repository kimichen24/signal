# Pipeline

Python data pipeline:
GitHub ingestion → cleaning → OpenAI structured extraction → embeddings → clustering → deterministic analytics → eval.

## Environment

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash (macOS/Linux: source .venv/bin/activate)
pip install -r pipeline/requirements.txt
python -m pytest tests -q       # config consistency tests
```

Bootstrap 阶段只安装 pytest 即可运行配置测试；完整运行时依赖随 Prompt 01+ 安装。

## Modules

| Module | Purpose | Status |
| --- | --- | --- |
| `github_client.py` | GitHub REST fetch (pagination, optional token, dataset window) | ✅ Prompt 01 |
| `ingest_github.py` | CLI: issues → Supabase upsert (PRs filtered, idempotent, window-bounded) | ✅ Prompt 01 |
| `clean_issue.py` | Heading parser (parsed_*) + `body_clean` builder | ✅ Prompt 01 |
| `supabase_client.py` | PostgREST reads/upserts/inserts (service role) | ✅ Prompt 01 |
| `dataset_window.py` | Reproducible window: `start_date <= created < snapshot_at` | ✅ Prompt 02 |
| `ai/base.py` | Provider-agnostic interface, system prompt, provider factory | ✅ Prompt 02 |
| `ai/schemas.py` | Local JSON extraction + jsonschema validation of model output | ✅ Prompt 02 |
| `ai/mimo.py` | Xiaomi MiMo provider (OpenAI-compatible base_url + validation retry loop) | ✅ Prompt 02 |
| `analyze_issue.py` | AI extraction CLI (dry-run, versioned, retryable failures, embeddings) | ✅ Prompt 02 |
| `audit_set.py` | 20-item human audit set builder (fixed seed, groups, CSV export) | ✅ 人工审计 |
| `eval_agreement.py` | Per-field human-AI agreement from a filled audit CSV | ✅ 人工审计 |
| `cluster_issues.py` | Clustering within top-level categories | Prompt 03 |
| `compute_trends.py` | Deterministic trends / emerging signals | Prompt 03 |
| `compute_release_impact.py` | Before/after windows (correlation only) | Prompt 04 |
| `evaluate.py` | 100-item human eval workflow | Prompt 05 |

## CLI

```bash
# First 100 real issues (anonymous GitHub access; add GITHUB_TOKEN for higher limits)
python -m pipeline.ingest_github --repo openai/codex --limit 100

# Created-at cutoff window (NOT GitHub's `since`, which filters by updated_at)
python -m pipeline.ingest_github --since 2026-08-07 --limit 100

# Preview without writing
python -m pipeline.ingest_github --limit 100 --dry-run
```

## 人工盲评工作流（Human Blind-Review Workflow）

```bash
# 1. 生成审计集（固定 seed，可复现）
python -m pipeline.audit_set --analysis-version v0.3.3 --seed 42

# 2. 派生最终人工标注文件（剥离 ai_* 与 audit_group，seed 洗牌；参考文件不动）
python -m pipeline.audit_set --blind-final-from eval/audit_set_v0.3.3.csv --seed 42

# 3. 在 eval/audit_set_v0.3.3_blind_final.csv 中独立填写 human_* 列 + reviewer_note

# 4. 按 github_issue_number join 回 AI 预测，计算各字段一致率
python -m pipeline.eval_agreement eval/audit_set_v0.3.3_blind_final.csv --reference eval/audit_set_v0.3.3.csv
```

Counts, growth rates, trends and priority scores are always computed by deterministic code — never by the LLM (AGENTS.md §2.8).
