/** Signal 全站简体中文展示标签 — 集中维护，避免术语不一致 */

export const SEVERITY: Record<string, string> = {
  critical: "严重", high: "高", medium: "中", low: "低",
};

export const SCOPE: Record<string, string> = {
  codex_core: "Codex 核心", codex_adjacent: "Codex 邻接", out_of_scope: "范围外",
};

export const ISSUE_TYPE: Record<string, string> = {
  bug: "Bug", feature_request: "功能请求", ux_issue: "体验问题",
  documentation: "文档", other: "其他",
};

export const CATEGORY: Record<string, string> = {
  "Reliability": "可靠性",
  "Performance": "性能",
  "Context & Memory": "上下文与记忆",
  "Model Quality": "模型质量",
  "Tool Execution": "工具执行",
  "Git & Workspace": "Git 与工作区",
  "App / UI / UX": "应用 / 界面 / 体验",
  "CLI": "CLI",
  "IDE Integration": "IDE 集成",
  "Authentication & Account": "认证与账户",
  "Usage & Credits": "用量与额度",
  "MCP & Integrations": "MCP 与集成",
  "Safety & Permissions": "安全与权限",
  "Installation & Updates": "安装与更新",
  "Onboarding & Documentation": "入门与文档",
  "Other": "其他",
};

export const SURFACE: Record<string, string> = {
  "Codex App": "桌面端", "CLI": "CLI", "IDE Extension": "IDE 扩展",
  "Web": "Web 端", "Unknown": "未知",
};

export const PLATFORM: Record<string, string> = {
  Windows: "Windows", macOS: "macOS", Linux: "Linux",
  Android: "Android", iOS: "iOS", Other: "其他", Unknown: "未知",
};

export const ACTION: Record<string, string> = {
  investigate_now: "立即调查", validate: "待验证",
  monitor: "持续观察", low_priority: "低优先级",
};

export const TREND_STATE: Record<string, string> = {
  normal_growth: "正常增长", low_base_acceleration: "低基数加速", new_signal: "新信号",
};
