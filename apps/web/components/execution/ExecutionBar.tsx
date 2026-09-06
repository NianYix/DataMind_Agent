"use client";

import { TraceItem } from "@/lib/flowModel";
import { api } from "@/lib/api";
import { StatusDot } from "@/components/shell/StatusDot";
import { RunUiStatus } from "@/lib/runStatus";

export type RunMetrics = {
  input_tokens?: number;
  output_tokens?: number;
  latency_ms?: number;
  estimated_cost?: number | null;
};

export function ExecutionBar({
  items,
  metrics,
  runId,
  runStatus,
}: {
  items: TraceItem[];
  metrics: RunMetrics;
  runId: string | null;
  runStatus: RunUiStatus;
}) {
  return (
    <footer className="shrink-0 border-t border-[var(--border)] bg-[var(--bg-1)]">
      <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] px-3 py-1.5">
        <div className="flex items-center gap-3">
          <span className="label-caps">Execution</span>
          <StatusDot status={runStatus} label={runStatus} />
          {runId ? (
            <span className="font-mono text-[10px] text-[var(--text-muted)]">RUN {runId.slice(0, 8)}</span>
          ) : null}
        </div>
        <div className="flex items-center gap-3 font-mono text-[10px] text-[var(--text-muted)]">
          <span>
            TOK {metrics.input_tokens ?? 0}/{metrics.output_tokens ?? 0}
          </span>
          {metrics.latency_ms != null ? <span>LAT {metrics.latency_ms}ms</span> : null}
          {metrics.estimated_cost != null ? <span>COST ${metrics.estimated_cost}</span> : null}
          {runId ? (
            <a
              className="text-[var(--primary)] underline"
              href={api.exportUrl(runId)}
              target="_blank"
              rel="noreferrer"
            >
              Export JSON
            </a>
          ) : null}
        </div>
      </div>
      <div className="scrollbar-thin flex gap-2 overflow-x-auto px-3 py-2">
        {items.length ? (
          items.map((item, idx) => {
            const done = idx < items.length - 1 || runStatus === "COMPLETED";
            const current = idx === items.length - 1 && runStatus === "RUNNING";
            const mark = /error/i.test(item.type) ? "✕" : current ? "▶" : done ? "✓" : "○";
            return (
              <div
                key={`${item.type}-${idx}`}
                className="flex min-w-[140px] max-w-[200px] items-start gap-2 rounded border border-[var(--border)] bg-[var(--panel)] px-2 py-1.5"
              >
                <span className="font-mono text-[10px] text-[var(--text-muted)]">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <div className="min-w-0">
                  <div className="flex items-center gap-1 text-[11px]">
                    <span>{mark}</span>
                    <span className="truncate">{item.type}</span>
                  </div>
                  <div className="truncate text-[10px] text-[var(--text-muted)]">{item.summary || "—"}</div>
                </div>
              </div>
            );
          })
        ) : (
          <span className="text-[11px] text-[var(--text-muted)]">No execution steps yet</span>
        )}
      </div>
    </footer>
  );
}
