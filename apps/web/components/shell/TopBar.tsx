"use client";

import Link from "next/link";
import { ReactNode } from "react";
import { StatusDot } from "@/components/shell/StatusDot";
import { RunUiStatus } from "@/lib/runStatus";
import { Workspace } from "@/lib/api";

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
  active: "workspace" | "settings" | "evaluation" | "data-sources" | "prompts" | "login" | "knowledge" | "mcp";
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
  const nav = (href: string, key: typeof active, label: string) => (
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
  );

  return (
    <header className="flex h-12 shrink-0 items-center justify-between gap-3 border-b border-[var(--border)] bg-[var(--bg-1)] px-3 md:px-4">
      <div className="flex min-w-0 items-center gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold tracking-tight text-[var(--text)]">DataMind</div>
          <div className="font-mono text-[10px] text-[var(--text-muted)]">LOGIC WORKSPACE</div>
        </div>
        {workspaces && onWorkspaceChange ? (
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
        ) : null}
      </div>

      <div className="flex items-center gap-2">
        {onRun || onStop ? (
          <>
            <button type="button" className="btn btn-primary" disabled={!canRun || running} onClick={onRun}>
              Run ▶
            </button>
            <button type="button" className="btn btn-danger" disabled={!running} onClick={onStop}>
              Stop ■
            </button>
          </>
        ) : null}
        {runStatus ? <StatusDot status={runStatus} label={runStatus} /> : null}
      </div>

      <div className="flex items-center gap-2">
        {nav("/", "workspace", "Workspace")}
        {nav("/knowledge", "knowledge", "Knowledge")}
        {nav("/mcp", "mcp", "MCP")}
        {nav("/data-sources", "data-sources", "Data Sources")}
        {nav("/prompts", "prompts", "Prompts")}
        {nav("/evaluation", "evaluation", "Evaluation")}
        {nav("/settings", "settings", "Settings")}
        {nav("/login", "login", "Login")}
        {health != null ? (
          <StatusDot
            status={health === "ok" ? "ok" : health === "checking" ? "checking" : "down"}
            label={health === "ok" ? "Connected" : `API ${health}`}
          />
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
