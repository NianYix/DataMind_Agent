export type RunUiStatus = "IDLE" | "RUNNING" | "COMPLETED" | "WARNING" | "ERROR";

export function deriveRunStatus(opts: {
  running: boolean;
  error?: string | null;
  hasResult?: boolean;
  runStatus?: string | null;
}): RunUiStatus {
  if (opts.running) return "RUNNING";
  if (opts.error || opts.runStatus === "error") return "ERROR";
  if (opts.runStatus === "cancelled") return "WARNING";
  if (opts.hasResult || opts.runStatus === "done" || opts.runStatus === "completed") return "COMPLETED";
  return "IDLE";
}

export const RUN_STATUS_COLOR: Record<RunUiStatus, string> = {
  IDLE: "var(--text-muted)",
  RUNNING: "var(--primary)",
  COMPLETED: "var(--success)",
  WARNING: "var(--warning)",
  ERROR: "var(--error)",
};
