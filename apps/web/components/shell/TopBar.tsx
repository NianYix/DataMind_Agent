"use client";

import Link from "next/link";
import { ReactNode } from "react";
import { StatusDot } from "@/components/shell/StatusDot";
import { Tip } from "@/components/shell/Tip";
import { RunUiStatus } from "@/lib/runStatus";
import { Workspace } from "@/lib/api";

const NAV_TIPS: Record<
  "workspace" | "settings" | "evaluation" | "data-sources" | "prompts" | "login" | "knowledge" | "mcp" | "workflows",
  string
> = {
  workspace: "自然语言分析台：提问 → Agent 调工具下钻 → 图表 / 报告 / Trace",
  knowledge: "知识库 RAG：上传口径/制度文档，Agent 可检索 definitions",
  workflows: "可保存的分析工作流：模板 / JSON 编排 → 一键复跑",
  mcp: "MCP 连接：接入外部工具，或把 DataMind 能力暴露给宿主",
  "data-sources": "数据源：连接 MySQL / PostgreSQL / mock，注册表为 Dataset",
  prompts: "提示词版本：覆盖 Planner / Insight / Critic 等系统提示",
  evaluation: "评测回归：用 Suite（mock/live）检查分析与工具成功率",
  settings: "模型、超时与运维指标；部分开关以 .env 为准",
  login: "登录与鉴权（AUTH_ENABLED=true 时生效）",
};

export function TopBar({
  active,
  health,
  runStatus,
  workspaces,
  workspaceId,
  onWorkspaceChange,
  onRun,
  onStop,
  running,
  canRun,
  trailing,
}: {
  active: keyof typeof NAV_TIPS;
  health?: string;
  runStatus?: RunUiStatus;
  workspaces?: Workspace[];
  workspaceId?: string;
  onWorkspaceChange?: (id: string) => void;
  onRun?: () => void;
  onStop?: () => void;
  running?: boolean;
  canRun?: boolean;
  trailing?: ReactNode;
}) {
  const nav = (href: string, key: keyof typeof NAV_TIPS, label: string) => (
    <Tip tip={NAV_TIPS[key]}>
      <Link
        href={href}
        className={`rounded px-2.5 py-1.5 text-xs transition-colors duration-150 ${
          active === key
            ? "bg-[var(--bg-2)] text-[var(--text)] border border-[var(--border-strong)]"
            : "text-[var(--text-muted)] hover:text-[var(--text)] border border-transparent"
        }`}
      >
        {label}
      </Link>
    </Tip>
  );

  return (
    <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--bg-1)] px-3 md:px-4">
      <div className="flex min-w-0 items-center gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold tracking-tight text-[var(--text)]">DataMind</div>
          <div className="font-mono text-[10px] text-[var(--text-muted)]">LOGIC WORKSPACE</div>
        </div>
        {workspaces && onWorkspaceChange ? (
          <Tip tip="切换当前 Workspace（数据集与会话按空间隔离）">
            <select
              className="input-dark max-w-[160px] py-1 text-xs"
              value={workspaceId || ""}
              onChange={(e) => onWorkspaceChange(e.target.value)}
            >
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
          </Tip>
        ) : null}
      </div>

      <div className="flex items-center gap-2">
        {onRun || onStop ? (
          <>
            <Tip tip="开始一次 Agent 分析（需已选数据集与问题）">
              <button type="button" className="btn btn-primary" disabled={!canRun || running} onClick={onRun}>
                Run ▶
              </button>
            </Tip>
            <Tip tip="请求停止当前正在执行的分析">
              <button type="button" className="btn btn-danger" disabled={!running} onClick={onStop}>
                Stop ■
              </button>
            </Tip>
          </>
        ) : null}
        {runStatus ? <StatusDot status={runStatus} label={runStatus} /> : null}
      </div>

      <div className="flex items-center gap-2">
        {nav("/", "workspace", "Workspace")}
        {nav("/knowledge", "knowledge", "Knowledge")}
        {nav("/workflows", "workflows", "Workflows")}
        {nav("/mcp", "mcp", "MCP")}
        {nav("/data-sources", "data-sources", "Data Sources")}
        {nav("/prompts", "prompts", "Prompts")}
        {nav("/evaluation", "evaluation", "Evaluation")}
        {nav("/settings", "settings", "Settings")}
        {nav("/login", "login", "Login")}
        {health != null ? (
          <Tip tip="后端 API 连通状态（/api/health）">
            <span className="inline-flex">
              <StatusDot
                status={health === "ok" ? "ok" : health === "checking" ? "checking" : "down"}
                label={health === "ok" ? "Connected" : `API ${health}`}
              />
            </span>
          </Tip>
        ) : null}
        {trailing}
      </div>
    </header>
  );
}

export function AppShell({
  children,
  topBar,
}: {
  children: ReactNode;
  topBar: ReactNode;
}) {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-[var(--bg-0)] text-[var(--text)]">
      {topBar}
      <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
    </div>
  );
}
