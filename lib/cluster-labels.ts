/**
 * Signal v1.0 frozen cluster Chinese display names.
 * Keyed by stable cluster_key (not mutable display text).
 * Total: 197 clusters, analysis_version = v0.3.4.
 *
 * This mapping is the single source of truth for recruiter-facing
 * cluster names. Do NOT edit database values.
 */

export const CLUSTER_LABELS: Record<string, string> = {
  // ── Usage & Credits ──────────────────────────────────────────
  "Usage & Credits:531d0144": "用量配额与使用窗口限制",
  "Usage & Credits:5a7fa01f": "额度耗尽后用量追踪与模型切换异常",
  "Usage & Credits:e7c0cde3": "Luna Reserve 激活失败",
  "Usage & Credits:64f39276": "未经授权自动消耗储备额度",
  "Usage & Credits:7400c021": "Codex 用量与权益不匹配",
  "Usage & Credits:a409b61a": "任务执行期间配额与资源管理问题",
  "Usage & Credits:6270d9ec": "每日额度重置与用量计量失败",

  // ── Reliability ──────────────────────────────────────────────
  "Reliability:8bbb6c56": "Windows 桌面端崩溃与意外退出",
  "Reliability:5d3e1c96": "分页会话历史记录显示异常",
  "Reliability:537ffbf6": "后端 API 返回404错误",
  "Reliability:3a790bb5": "对话内容丢失或不可用",
  "Reliability:2c086199": "提交请求卡住无响应",
  "Reliability:75931aff": "macOS 桌面端请求失败",
  "Reliability:a49aaba8": "Windows 沙盒配置与初始化失败",
  "Reliability:98d028a7": "任务过早终止与状态误报",
  "Reliability:154fcba7": "Android 远程同步与连接失败",
  "Reliability:b811c8ba": "应用服务器 RPC 断开与无响应",
  "Reliability:b379f302": "Windows 插件初始化与缓存失败",
  "Reliability:e9853d95": "macOS 桌面端任务卡顿与流断开",
  "Reliability:11759e9d": "会话与对话历史持久化失败",
  "Reliability:e205f9b6": "Windows Codex 桌面端更新失败",
  "Reliability:42d3cb74": "线程状态同步与数据完整性问题",
  "Reliability:b721e93e": "模型容量错误中断活跃任务",
  "Reliability:6aded3c2": "CLI 对话中断与意外退出",
  "Reliability:df39222b": "侧边栏与线程状态持久化失败",
  "Reliability:d99968f5": "WebSocket 连接稳定性与卡顿问题",
  "Reliability:d969e37b": "本地会话存储无限增长",
  "Reliability:e989e117": "macOS EXC_BREAKPOINT/SIGTRAP 崩溃",
  "Reliability:3aeba2ad": "配置与传输错误导致线程恢复失败",
  "Reliability:df29b0f2": "Windows 文件操作循环与资源耗尽",
  "Reliability:8d3e90c6": "会话恢复与分叉失败",
  "Reliability:8b46abf9": "代理与会话初始化失败",
  "Reliability:12307d6a": "Remote Control 同步与可见性问题",
  "Reliability:e8b3f082": "Codex Cloud 任务触发与执行失败",
  "Reliability:2048ce39": "会话与线程切换错误",
  "Reliability:8fdafbbf": "内置浏览器可靠性问题",
  "Reliability:7ec000d6": "VS Code 扩展会话与 Webview 回退",
  "Reliability:90eee383": "心跳自动化结果未渲染",
  "Reliability:8fa30f21": "应用服务器会话挂起与生命周期失败",
  "Reliability:f35a88a0": "Chrome 扩展初始化与连接失败",
  "Reliability:34f2538b": "Linux 桌面端崩溃（多种信号）",
  "Reliability:3f6dd27e": "GPT-6 Astra 连接与处理可靠性问题",
  "Reliability:ceb7a227": "远程线程写入锁冲突",
  "Reliability:3de393ac": "请求期间流断开",
  "Reliability:db979c7a": "CLI 与功能间歇性失败",
  "Reliability:27da8ec9": "远程会话任务连续性问题",
  "Reliability:2b08b5cc": "持续超时与配置加载失败",
  "Reliability:3e513fbd": "启动与权限状态可靠性问题",
  "Reliability:0c99bcba": "应用服务器线程生命周期与恢复可靠性",
  "Reliability:d363e0cf": "终端会话状态显示问题",
  "Reliability:3218bf9d": "远程 SSH 连接与生命周期失败",
  "Reliability:6437ebf4": "特定设备远程 QR 配对失败",
  "Reliability:2add997c": "活跃会话期间斜杠命令失败",
  "Reliability:9d4d4461": "多窗口并发 Codex 轮次重复",
  "Reliability:e35e1913": "Python SDK 轮次卡顿与通知丢失",
  "Reliability:d82feb34": "Windows/WSL Codex 桌面端可靠性回退",
  "Reliability:4b347cb1": "下载与连接失败但误报成功",
  "Reliability:7910ef29": "应用更新后 CLI 与包路径过期",
  "Reliability:ec532fb7": "Windows 应用 UI 无响应或隐藏",
  "Reliability:b633b829": "API 请求字段与配置不一致",
  "Reliability:da5c6ca2": "特定交互下应用崩溃",
  "Reliability:cbd36b90": "桌面端启动错误与日志洪泛",
  "Reliability:81570409": "macOS Computer Use 服务唤醒显示问题",
  "Reliability:d2171ed8": "Windows setProgressBar 文件操作 TypeError",
  "Reliability:710bfbee": "SQLite 元数据导致回滚会话恢复问题",
  "Reliability:2d9e3465": "WSL 代理模式路径处理失败",
  "Reliability:7b54a855": "听写与音频可视化器冲突",
  "Reliability:e07fe910": "SQLite 数据库问题导致桌面端启动失败",

  // ── Performance ──────────────────────────────────────────────
  "Performance:63476339": "桌面端应用高资源消耗",
  "Performance:97c1988e": "回滚与会话存储过度膨胀",
  "Performance:22f57b6b": "macOS 桌面端性能与卡顿问题",
  "Performance:217809fa": "CLI 性能下降与 Token 放大",
  "Performance:0be50e8f": "Windows 首次启动运行时提取延迟",
  "Performance:56456c1f": "桌面端资源使用峰值与泄漏",
  "Performance:078c4c63": "macOS CPU/GPU 高占用与过热",
  "Performance:c3de76c2": "TUI 输入延迟与无响应",

  // ── Tool Execution ───────────────────────────────────────────
  "Tool Execution:dd43bcc7": "Windows 统一执行工具失败",
  "Tool Execution:e500db54": "浏览器控制会话挂起与超时",
  "Tool Execution:c6cfce67": "独立 function_call_output 缺失 call_id",
  "Tool Execution:a7b152e5": "跨任务消息传递工具缺失或损坏",
  "Tool Execution:4349f19e": "Computer Use 工具失败与功能缺失",
  "Tool Execution:165fe7c4": "Windows 沙盒执行失败",
  "Tool Execution:939727f6": "内置浏览器插件初始化或挂载失败",
  "Tool Execution:b4a361c5": "Node REPL 中 Computer Use 执行失败",
  "Tool Execution:13de305b": "CLI 工具可用性与执行失败",
  "Tool Execution:c1927145": "macOS Computer Use 辅助程序崩溃",
  "Tool Execution:65f838e9": "图片生成工具问题",
  "Tool Execution:8ed346f5": "工具结果上报与计时问题",
  "Tool Execution:11d17f73": "Windows PowerShell 命令执行失败",
  "Tool Execution:9829a81c": "多功能工具执行失败",
  "Tool Execution:42905bae": "代理工具执行与文件系统范围问题",
  "Tool Execution:da9da1af": "后台进程清理与生命周期问题",
  "Tool Execution:d96ebd06": "子代理工具与工作区访问限制",
  "Tool Execution:73bcf9a1": "Windows Git 执行与 Shell 回退问题",
  "Tool Execution:6f5ab48e": "自定义搜索引擎 Web 搜索失败",
  "Tool Execution:0a00f8c7": "管理员策略阻止浏览器工具执行",

  // ── App / UI / UX ────────────────────────────────────────────
  "App / UI / UX:97578255": "桌面宠物交互与响应失败",
  "App / UI / UX:cc54824e": "桌面端聊天历史持久化与删除失败",
  "App / UI / UX:9acaaa6c": "桌面端模式切换失败",
  "App / UI / UX:322995a4": "TUI 渲染与显示不一致",
  "App / UI / UX:52c7927a": "Remote Control 与跨设备同步问题",
  "App / UI / UX:2f8dc02f": "Chrome 扩展侧边栏与标签页控制问题",
  "App / UI / UX:a2084867": "UI 面板与输入框意外消失",
  "App / UI / UX:4e157013": "快捷键冲突与自定义问题",
  "App / UI / UX:f1282831": "启动与全屏时白屏/空白屏",
  "App / UI / UX:0b3c03b6": "Windows 语音覆盖层控件无响应且不可移动",
  "App / UI / UX:8ecfbc04": "Codex 线程与任务组织功能",
  "App / UI / UX:a833064e": "Open-with/Open-in 工具栏操作缺失或损坏",
  "App / UI / UX:862ca6ca": "浏览器面板与链接路由问题",
  "App / UI / UX:32d36e7c": "粘贴文本损坏与处理问题",
  "App / UI / UX:3e7fa8f4": "本地项目侧边栏管理问题",
  "App / UI / UX:b4add0a4": "命令活动紧凑分组切换",
  "App / UI / UX:421aad7b": "消息重复与不完整渲染",
  "App / UI / UX:184ad1fa": "macOS 应用窗口管理问题",
  "App / UI / UX:4358f053": "侧边栏任务信息显示问题",
  "App / UI / UX:5987b389": "深色主题文本可见性与对比度问题",
  "App / UI / UX:dde150df": "推理强度重置为 Instant",
  "App / UI / UX:c56b0e5d": "响应渲染与交互问题",
  "App / UI / UX:456cc2e4": "Codex 聊天中代码块渲染与高亮",
  "App / UI / UX:621e9b07": "聊天 UI 历史与消息操作问题",
  "App / UI / UX:dd6d65d3": "终端剪贴板复制/粘贴问题",
  "App / UI / UX:75e3ad73": "ChatGPT 桌面端云任务与代理 UI 缺口",
  "App / UI / UX:3ff75c8f": "Codex Canvas 与聊天中图片处理问题",
  "App / UI / UX:1092b3e3": "可配置对话体验设置",
  "App / UI / UX:4c2985f8": "Codex 桌面端持久化模型与预设配置",
  "App / UI / UX:66092ff1": "Codex 宠物创建与交互增强",
  "App / UI / UX:942f3286": "RTL 布局与窗口标题栏控件问题",
  "App / UI / UX:c6bea76a": "简体中文 UI 本地化缺失",
  "App / UI / UX:6e065f33": "macOS 编辑器输入与格式化问题",
  "App / UI / UX:a7332d9e": "可配置内联 Diff 预览限制",
  "App / UI / UX:d8c30bfb": "macOS 意外前台焦点抢占",

  // ── MCP & Integrations ───────────────────────────────────────
  "MCP & Integrations:6136492c": "MCP OAuth 认证与状态显示问题",
  "MCP & Integrations:5d1f0c72": "MCP 工具发现与调用失败",
  "MCP & Integrations:e14cc255": "Windows WSL 模式下 MCP 传输无效",
  "MCP & Integrations:907516b4": "MCP 客户端连接与会话失败",
  "MCP & Integrations:7c874460": "远程目录中插件与技能发现失败",
  "MCP & Integrations:18d123c7": "REPL 插件环境与配置问题",
  "MCP & Integrations:269c7e1b": "MCP 线程工具审批模式与继承问题",
  "MCP & Integrations:3a4df55d": "GitHub 连接器工具可用性与能力缺口",
  "MCP & Integrations:7cee3169": "MCP 引导式交互处理问题",
  "MCP & Integrations:e8ffaffc": "MCP 进程堆积与清理不完全",

  // ── Authentication & Account ─────────────────────────────────
  "Authentication & Account:0bc846a7": "桌面端会话与 Token 处理失败",
  "Authentication & Account:4ab43198": "跨环境 OAuth 认证流程失败",
  "Authentication & Account:6bf3d2a6": "MCP OAuth 集成不一致",
  "Authentication & Account:5d850e57": "认证与套餐同步问题",
  "Authentication & Account:5f8b3ab2": "Windows Remote Control 认证失败",
  "Authentication & Account:6abb9f60": "订阅与账户访问拒绝",
  "Authentication & Account:b362a836": "Desktop 连接器线程认证失败",
  "Authentication & Account:988eb846": "应用中登录-登出循环与退出错误",
  "Authentication & Account:30745a58": "账户轮换与会话接管",

  // ── Context & Memory ─────────────────────────────────────────
  "Context & Memory:8c3a7aa6": "上下文压缩可靠性与副作用失败",
  "Context & Memory:0aaffd19": "上下文窗口大小与管理不可靠",
  "Context & Memory:334cc257": "Codex 中持久化聊天上下文与历史",
  "Context & Memory:9fca0651": "跨任务委托 Prompt 上下文失败",
  "Context & Memory:449b272d": "AGENTS.md 处理问题",
  "Context & Memory:57ce90f4": "技能与能力上下文持久化问题",
  "Context & Memory:3f721039": "跨线程任务交接与路由失败",
  "Context & Memory:f299e8d0": "按上下文配置与可见性",

  // ── Safety & Permissions ─────────────────────────────────────
  "Safety & Permissions:25cd0c87": "安全与内容过滤误判拦截",
  "Safety & Permissions:a9264eaa": "沙盒权限配置文件执行失败",
  "Safety & Permissions:b0e3122f": "Windows 沙盒配置与权限问题",
  "Safety & Permissions:631e4b09": "Codex 桌面端权限与审批策略不一致",
  "Safety & Permissions:ba1799cc": "Browser Use 误判站点拦截",
  "Safety & Permissions:fa8ecaee": "沙盒权限拒绝与崩溃",
  "Safety & Permissions:e2ba1ce6": "未经授权的代理操作",
  "Safety & Permissions:07d214bd": "更新与代理运行期间配置文件被修改",
  "Safety & Permissions:7f8655c7": "自动审核模型与授权问题",
  "Safety & Permissions:c1580b8d": "权限请求与授予行为异常",
  "Safety & Permissions:925bb82d": "未经授权或意外的生产部署",
  "Safety & Permissions:e0022443": "macOS Keychain 与安全输入持久化问题",
  "Safety & Permissions:12dffdea": "create_thread 权限与归属降级",
  "Safety & Permissions:0b601740": "审批与权限配置绕过或覆盖",
  "Safety & Permissions:9aa9fc6e": "Codex 应用 Trusted Access 验证问题",
  "Safety & Permissions:13325f86": "macOS 沙盒工作区访问问题",
  "Safety & Permissions:fd1a26dc": "代理未经用户同意执行重置操作",

  // ── Git & Workspace ──────────────────────────────────────────
  "Git & Workspace:6e0094fc": "Windows/WSL 路径处理破坏项目操作",
  "Git & Workspace:f69197d9": "Worktree 生命周期管理失败",
  "Git & Workspace:26579f77": "后台 Git 操作在工作区留下过期状态",
  "Git & Workspace:674cc553": "工作区路径管理与配置问题",

  // ── Installation & Updates ───────────────────────────────────
  "Installation & Updates:4a6426fa": "Windows Codex CLI 更新后二进制不可用",
  "Installation & Updates:522e697c": "跨平台 CLI 安装与更新失败",
  "Installation & Updates:6efbd50d": "Windows 沙盒配置失败",
  "Installation & Updates:5e059ec9": "Chrome 原生宿主注册文件过期或缺失",

  // ── CLI ──────────────────────────────────────────────────────
  "CLI:e18010c1": "CLI 专属 Windows Remote Control 托管",
  "CLI:4269d33d": "CLI 静默失败与参数解析问题",
  "CLI:f7316b12": "Windows 终端 TUI 功能限制",
  "CLI:96263cfb": "会话中 CLI 自定义命令",
  "CLI:faa94489": "终端会话退出与恢复行为问题",

  // ── Model Quality ────────────────────────────────────────────
  "Model Quality:3f7c4979": "长任务中 Codex 误报完成与范围漂移",
  "Model Quality:a72fd87b": "生成标题与摘要中出现意外语言",
  "Model Quality:4b8dcbe7": "GPT-5.6 Sol 指令遵循与任务漂移问题",
  "Model Quality:afd2fa9d": "代理忽略明确指令与约束",
  "Model Quality:3fb96eb7": "代理忽略用户指令与确认请求",
  "Model Quality:8e2b3710": "Codex 对话输出质量问题",
  "Model Quality:577bb5a5": "模型可用性与身份不一致",
  "Model Quality:d2d10366": "模型路由或选择默认值错误",

  // ── Other ────────────────────────────────────────────────────
  "Other:acba3f53": "OpenTelemetry 遥测属性与关联问题",
};

/**
 * Get the Chinese display name for a cluster.
 * Returns the Chinese name if mapped, or the original English name as fallback.
 * In production, every frozen v0.3.4 cluster MUST have a mapping.
 */
export function getClusterDisplayName(
  cluster: { clusterKey?: string; name: string }
): string {
  if (cluster.clusterKey && CLUSTER_LABELS[cluster.clusterKey]) {
    return CLUSTER_LABELS[cluster.clusterKey];
  }
  // Fallback: try exact English name match (for components that don't have clusterKey)
  return cluster.name;
}

/**
 * Validation helper: check that all production clusters have Chinese labels.
 * Run at build time or in tests.
 */
export function validateClusterLabels(
  productionKeys: string[]
): { total: number; mapped: number; missing: string[] } {
  const missing = productionKeys.filter((k) => !CLUSTER_LABELS[k]);
  return {
    total: productionKeys.length,
    mapped: productionKeys.length - missing.length,
    missing,
  };
}
