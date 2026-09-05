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

| Module | Purpose | Delivered |
| --- | --- | --- |
| `ingest_github.py` | GitHub REST API → Supabase (issues only, PRs filtered) | Prompt 01 |
| `clean_issue.py` | `body_clean`: strip logs / doctor reports / code blocks for LLM input (raw preserved) | Prompt 01 |
| `analyze_issue.py` | OpenAI Responses API structured extraction (JSON Schema) | Prompt 02 |
| `embed_issues.py` | Embeddings → pgvector | Prompt 02 |
| `cluster_issues.py` | Clustering within top-level categories | Prompt 03 |
| `compute_trends.py` | Deterministic trends / emerging signals | Prompt 03 |
| `compute_release_impact.py` | Before/after windows (correlation only) | Prompt 04 |
| `evaluate.py` | 100-item human eval workflow | Prompt 05 |

Counts, growth rates, trends and priority scores are always computed by deterministic code — never by the LLM (AGENTS.md §2.8).
