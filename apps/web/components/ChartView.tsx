"use client";

import ReactECharts from "echarts-for-react";

export function ChartView({
  option,
  title,
}: {
  option: Record<string, unknown>;
  title?: string;
}) {
  const themed = {
    backgroundColor: "transparent",
    textStyle: { color: "#8B949E" },
    ...option,
  };

  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-3">
      {title ? <div className="mb-2 text-xs font-medium text-[var(--text)]">{title}</div> : null}
      <ReactECharts option={themed} style={{ height: 240, width: "100%" }} notMerge lazyUpdate />
    </div>
  );
}
