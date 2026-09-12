"""Independent Codex reference labeling of the frozen 50-item holdout.

Reads ONLY eval/holdout_v0.3.4_blind.csv (+ frozen definitions in
config/taxonomy.json and docs/DECISIONS.md). Labels below were assigned by
manual review of each row's evidence against the frozen v0.3.4 severity
rubric and workflow-based product_scope definitions.

No database, AI-prediction, cluster, or summary data was consulted.
"""
import csv
import json
import sys

INPUT = "eval/holdout_v0.3.4_blind.csv"
OUTPUT = "eval/holdout_v0.3.4_blind_codex_labeled.csv"

# issue_number -> (scope, issue_type, category, surface, platform, severity, notes)
LABELS = {
    40185: ("codex_core", "documentation", "Onboarding & Documentation", "CLI", "Unknown", "low",
            "Docs-only: stale links to deprecated skills repo and overstated codex-universal parity; no functional impact."),
    40223: ("codex_core", "bug", "Usage & Credits", "Codex App", "macOS", "medium",
            "Title generation inherits full agent context and burns tokens per thread; cost friction, task still completes."),
    40312: ("codex_core", "bug", "Authentication & Account", "Codex App", "Windows", "medium",
            "Sign-out completes but UI hits global error boundary; relaunch restores normal state."),
    40349: ("codex_core", "bug", "Reliability", "Codex App", "Windows", "high",
            "App repeatedly terminates restoring oversized browser-heavy tasks; workaround is relaunch/avoiding those tasks."),
    40439: ("codex_core", "bug", "Model Quality", "CLI", "Linux", "high",
            "Agent stuck in a loop retrying a failing rg command (custom qwen model); task cannot proceed."),
    40440: ("codex_core", "bug", "Tool Execution", "Codex App", "Windows", "medium",
            "Self-archive succeeds but tool reports failure and interrupts the turn; ambiguous outcome handling."),
    40708: ("codex_core", "bug", "Other", "CLI", "Unknown", "low",
            "Empty body; only labels (bug/CLI/custom-model/config) and a 4-word title — insufficient evidence for precision."),
    40792: ("out_of_scope", "bug", "Usage & Credits", "Codex App", "Linux", "low",
            "Codex usage limit wrongly gates ChatGPT chat-mode Voice; affected workflow is chatting, not a Codex workflow."),
    40829: ("codex_core", "bug", "MCP & Integrations", "Codex App", "Windows", "high",
            "WSL workspace tasks fail to start on invalid mcp_servers.codex_app transport config."),
    40899: ("codex_core", "bug", "Tool Execution", "Codex App", "Windows", "high",
            "code-mode host exits during handshake; exec tool calls fail intermittently but frequently."),
    40968: ("codex_core", "bug", "Reliability", "Codex App", "Windows", "high",
            "Follow-up prompts never submit in existing threads (spinner forever); new threads work."),
    41066: ("codex_core", "bug", "App / UI / UX", "Codex App", "macOS", "high",
            "Plan mode stays active internally after UI disable; execution refused and usage consumed without result."),
    41114: ("codex_adjacent", "feature_request", "App / UI / UX", "Codex App", "iOS", "medium",
            "Enhancement: persistent logical Remote Control session across iOS backgrounding; recurring 10s+ reconnect friction."),
    41133: ("codex_core", "bug", "Authentication & Account", "CLI", "macOS", "medium",
            "MCP shutdown race can drop a rotated refresh token; token family revoked, re-authentication required."),
    41186: ("codex_core", "bug", "Tool Execution", "Codex App", "Unknown", "high",
            "Browser runtime attachment fails across full restarts; @Browser tool never exposed to tasks."),
    41187: ("codex_core", "bug", "Installation & Updates", "CLI", "macOS", "medium",
            "codex agents requires installer-managed standalone path; brew installs blocked."),
    41324: ("codex_core", "bug", "Reliability", "Codex App", "Linux", "high",
            "Typing '/' crashes the whole desktop app (SIGTRAP); composer input path broken for that character."),
    41326: ("codex_core", "bug", "Tool Execution", "Codex App", "macOS", "high",
            "Computer Use crashes on every click after get_app_state; CU actions unusable."),
    41372: ("codex_core", "bug", "Performance", "Codex App", "Windows", "medium",
            "Heartbeat automation takes ~3 minutes for a sub-second local scan; advice arrives very late."),
    41389: ("codex_core", "bug", "App / UI / UX", "Codex App", "Windows", "low",
            "Follow-up code-level evidence for a composer text-normalization defect (&#x20; handling); symptom partially truncated in report."),
    41402: ("codex_core", "feature_request", "App / UI / UX", "Codex App", "macOS", "low",
            "Enhancement: surface stable project identity when opening remote SSH connections."),
    41507: ("codex_core", "bug", "Tool Execution", "Codex App", "Windows", "high",
            "code-mode host exits on handshake; entire 5.6 model family unusable in desktop app (CLI works as fallback)."),
    41538: ("codex_core", "feature_request", "Context & Memory", "CLI", "Unknown", "low",
            "Enhancement proposal: opt-in adaptive context budget driven by compaction feedback."),
    41556: ("codex_core", "bug", "Installation & Updates", "Codex App", "Windows", "high",
            "Invalid TOML conflict causes startup setup loop with unusable UI; manual config repair required."),
    41603: ("codex_core", "bug", "Tool Execution", "Codex App", "Windows", "high",
            "Local execution helper fails initialization; chat-agent cannot execute any local command."),
    41667: ("codex_core", "bug", "Reliability", "Codex App", "Windows", "medium",
            "Sidebar fork aborts five WebSocket sends before HTTP fallback succeeds; recovery is built in."),
    41694: ("out_of_scope", "other", "Other", "Unknown", "Unknown", "low",
            "Agent task request (autonomous audit/fix/deploy of an external product) filed as an issue; not Codex product feedback."),
    41695: ("codex_adjacent", "bug", "Performance", "Codex App", "iOS", "high",
            "iPad client freezes consistently when opening longer remote Codex sessions; iPhone unaffected."),
    41704: ("codex_core", "bug", "Context & Memory", "Codex App", "Windows", "high",
            "Agents repeatedly lose AGENTS.md-derived governance rules during long sessions."),
    41708: ("codex_adjacent", "bug", "Reliability", "Codex App", "Android", "high",
            "Android Remote queue silently discards six queued messages or delays them ~40 minutes; user input loss."),
    41726: ("codex_core", "bug", "Performance", "Codex App", "Windows", "medium",
            "Local chat search stalls on 'Loading chats...' and aborts on navigation; cloud results are fast."),
    41754: ("codex_core", "bug", "Tool Execution", "CLI", "Windows", "high",
            "Native Windows sandbox provisioning fails on every command since 0.147.0; SentinelOne co-present."),
    41767: ("codex_core", "bug", "Safety & Permissions", "Codex App", "macOS", "high",
            "Routine authorized maintenance blocked by Trusted Access cyber-safety notice; explanatory follow-up also fails."),
    41797: ("codex_core", "bug", "MCP & Integrations", "CLI", "macOS", "medium",
            "Numeric MCP form elicitation degrades to generic approval and submits empty content."),
    41807: ("codex_core", "bug", "App / UI / UX", "Web", "iOS", "high",
            "Codex Cloud regression: new mobile tasks edit files but diff/Create-PR handoff never appears (blocked review step)."),
    41930: ("codex_core", "feature_request", "App / UI / UX", "Codex App", "Windows", "low",
            "Localization request: zh-CN resources ship but UI remains English."),
    42088: ("codex_core", "bug", "Tool Execution", "Codex App", "Unknown", "high",
            "function_call_output emitted without call_id; strict upstreams reject thread resume with 400."),
    42116: ("codex_core", "bug", "Installation & Updates", "Codex App", "macOS", "critical",
            "Startup config/batchWrite silently truncates user config.toml (12.3KB to 2.2KB), destroying unmanaged user state — strong before/after evidence of data-integrity damage."),
    42198: ("codex_core", "bug", "App / UI / UX", "Codex App", "macOS", "low",
            "Only the first Cmd+V after opening an external file is swallowed; second paste works."),
    42305: ("codex_core", "bug", "Tool Execution", "Codex App", "macOS", "medium",
            "Computer Use loses Shift through Tart/Screen Sharing; shifted input arrives unshifted."),
    42345: ("codex_core", "feature_request", "Performance", "CLI", "macOS", "medium",
            "Rollout files duplicate command output 4x; measured 1.4GB session growth over 12 days."),
    42466: ("codex_core", "bug", "Safety & Permissions", "Codex App", "Unknown", "high",
            "Browser Use fails on every site: admin-enforced policy cannot be verified; entire feature blocked."),
    42499: ("codex_core", "bug", "App / UI / UX", "Codex App", "macOS", "low",
            "Cosmetic: sticky code-block header overlaps code while scrolling."),
    42611: ("codex_core", "bug", "Context & Memory", "CLI", "Linux", "high",
            "Auto-compaction replays an already-answered user message as a new turn; risk of repeating state-changing actions (local hook mitigation exists)."),
    42732: ("codex_core", "feature_request", "App / UI / UX", "Codex App", "Unknown", "low",
            "Cosmetic customization request: per-session background/accent colors."),
    42747: ("codex_core", "bug", "IDE Integration", "IDE Extension", "Linux", "medium",
            "Follow-up chat messages error out in VS Code extension; screenshot-only evidence limits severity read."),
    42759: ("codex_core", "bug", "Performance", "Codex App", "Windows", "medium",
            "Idle Beta app pegs CPU and spikes network reproducibly; workaround: use stable channel."),
    42815: ("codex_core", "bug", "Context & Memory", "Unknown", "high",
            "placeholder"),
    42857: ("codex_core", "bug", "App / UI / UX", "Codex App", "Linux", "low",
            "Cosmetic: floating pet jitters/jumps during rapid dragging on Wayland."),
    42936: ("codex_core", "bug", "Reliability", "Codex App", "macOS", "high",
            "Reproducible send failure with reconnect loop on new chat; no workaround given."),
}

# 42815 surface/platform: long-session agent report; platform/surface not
# explicitly stated in the visible evidence — fix the placeholder:
LABELS[42815] = (
    "codex_core", "bug", "Context & Memory", "Unknown", "Unknown", "high",
    "Long-running session: agent repeatedly ignored durable instructions, misreported completion state, enforced approval gates inconsistently; platform not stated in report.",
)

TAXONOMY = {
    "product_scope": {"codex_core", "codex_adjacent", "out_of_scope"},
    "issue_type": {"bug", "feature_request", "ux_issue", "documentation", "other"},
    "category": {
        "Reliability", "Performance", "Context & Memory", "Model Quality",
        "Tool Execution", "Git & Workspace", "App / UI / UX", "CLI",
        "IDE Integration", "Authentication & Account", "Usage & Credits",
        "MCP & Integrations", "Safety & Permissions", "Installation & Updates",
        "Onboarding & Documentation", "Other",
    },
    "surface": {"Codex App", "CLI", "IDE Extension", "Web", "Unknown"},
    "platform": {"Windows", "macOS", "Linux", "Android", "iOS", "Other", "Unknown"},
    "severity": {"critical", "high", "medium", "low"},
}

EVIDENCE_COLUMNS = (
    "github_issue_number", "title", "github_url", "body_clean",
    "parsed_version", "parsed_subscription", "parsed_platform",
    "parsed_actual", "parsed_steps", "parsed_expected",
    "parsed_additional_info", "github_labels",
)


def main() -> int:
    with open(INPUT, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    problems: list[str] = []

    if len(rows) != 50:
        problems.append(f"row count {len(rows)} != 50")

    numbers = [int(r["github_issue_number"]) for r in rows]
    if len(set(numbers)) != 50:
        problems.append("duplicate github_issue_number values")

    if set(numbers) != set(LABELS):
        missing = set(LABELS) - set(numbers)
        extra = set(numbers) - set(LABELS)
        problems.append(f"label/row mismatch: missing labels {sorted(missing)}, unexpected rows {sorted(extra)}")

    labeled_rows = []
    for row in rows:
        number = int(row["github_issue_number"])
        scope, issue_type, category, surface, platform, severity, notes = LABELS[number]

        for field, value in (
            ("product_scope", scope), ("issue_type", issue_type),
            ("category", category), ("surface", surface),
            ("platform", platform), ("severity", severity),
        ):
            if value not in TAXONOMY[field]:
                problems.append(f"#{number}: {field}='{value}' not in frozen taxonomy")

        if not all(str(row[f]).strip() is not None for f in EVIDENCE_COLUMNS):
            problems.append(f"#{number}: evidence column missing")

        labeled_rows.append(
            {
                **row,
                "human_product_scope": scope,
                "human_issue_type": issue_type,
                "human_category": category,
                "human_surface": surface,
                "human_platform": platform,
                "human_severity": severity,
                "human_notes": notes,
            }
        )

    # evidence columns unchanged vs input
    for original, labeled in zip(rows, labeled_rows):
        for col in EVIDENCE_COLUMNS:
            if original[col] != labeled[col]:
                problems.append(f"#{original['github_issue_number']}: evidence column '{col}' modified")

    empty_labels = [
        f"#{r['github_issue_number']}"
        for r in labeled_rows
        for f in ("human_product_scope", "human_issue_type", "human_category",
                  "human_surface", "human_platform", "human_severity")
        if not r[f].strip()
    ]
    if empty_labels:
        problems.append(f"empty categorical labels: {empty_labels}")

    if problems:
        print("VALIDATION FAILED:")
        for p in problems:
            print(" -", p)
        return 1

    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(labeled_rows)

    print("VALIDATION PASSED")
    print(f"rows: {len(labeled_rows)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
