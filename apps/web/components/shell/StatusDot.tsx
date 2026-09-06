"use client";

import { RUN_STATUS_COLOR, RunUiStatus } from "@/lib/runStatus";

export function StatusDot({
  status,
  label,
  size = 8,
}: {
  status: RunUiStatus | "ok" | "down" | "checking";
  label?: string;
  size?: number;
}) {
  const color =
    status === "ok"
      ? "var(--success)"
      : status === "down"
        ? "var(--error)"
        : status === "checking"
          ? "var(--warning)"
          : RUN_STATUS_COLOR[status as RunUiStatus];

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-[var(--text-muted)]">
      <span
        className="inline-block rounded-full"
        style={{ width: size, height: size, background: color, boxShadow: `0 0 0 2px color-mix(in srgb, ${color} 25%, transparent)` }}
        aria-hidden
      />
      {label ? <span>{label}</span> : null}
    </span>
  );
}
