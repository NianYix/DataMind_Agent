"use client";

import { FLOW_NODE_SIZE, FlowEdgeModel, FlowNodeModel, kindColor } from "@/lib/flowModel";

export function FlowEdge({
  edge,
  nodes,
}: {
  edge: FlowEdgeModel;
  nodes: FlowNodeModel[];
}) {
  const from = nodes.find((n) => n.id === edge.from);
  const to = nodes.find((n) => n.id === edge.to);
  if (!from || !to) return null;

  const x1 = from.x + FLOW_NODE_SIZE.w;
  const y1 = from.y + FLOW_NODE_SIZE.h / 2;
  const x2 = to.x;
  const y2 = to.y + FLOW_NODE_SIZE.h / 2;
  const mx = (x1 + x2) / 2;
  const d = `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
  const stroke = edge.error ? "var(--error)" : edge.active ? "var(--primary)" : "var(--border-strong)";

  return (
    <path
      d={d}
      fill="none"
      stroke={stroke}
      strokeWidth={edge.active ? 2 : 1.25}
      className={edge.active ? "edge-active" : undefined}
    />
  );
}

export function FlowNode({
  node,
  selected,
  onSelect,
}: {
  node: FlowNodeModel;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const accent = kindColor(node.kind);
  return (
    <button
      type="button"
      onClick={() => onSelect(node.id)}
      className={`absolute text-left transition-colors duration-150 ${
        node.status === "running" ? "node-running" : ""
      }`}
      style={{
        left: node.x,
        top: node.y,
        width: FLOW_NODE_SIZE.w,
        height: FLOW_NODE_SIZE.h,
      }}
    >
      <div
        className="h-full overflow-hidden rounded-md border bg-[var(--panel)] px-2.5 py-2"
        style={{
          borderColor: selected ? "var(--primary)" : accent,
          boxShadow: selected
            ? "0 0 0 1px color-mix(in srgb, var(--primary) 50%, transparent)"
            : "none",
        }}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-1.5">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: accent }} />
            <span className="truncate text-xs font-medium text-[var(--text)]">{node.title}</span>
          </div>
          <span className="font-mono text-[10px] text-[var(--text-muted)]">{node.id}</span>
        </div>
        <div className="mt-1 font-mono text-[10px] uppercase tracking-wide text-[var(--text-muted)]">
          {node.kind} · {node.status}
        </div>
        <div className="mt-1 line-clamp-2 text-[11px] leading-4 text-[var(--text-muted)]">
          {node.summary || "—"}
        </div>
      </div>
    </button>
  );
}

export function LogicCanvas({
  nodes,
  edges,
  width,
  height,
  selectedId,
  onSelect,
}: {
  nodes: FlowNodeModel[];
  edges: FlowEdgeModel[];
  width: number;
  height: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="canvas-grid relative h-full min-h-0 overflow-auto">
      <div className="relative" style={{ width: Math.max(width, 480), height: Math.max(height, 320) }}>
        <svg className="pointer-events-none absolute inset-0" width={width} height={height}>
          {edges.map((e) => (
            <FlowEdge key={e.id} edge={e} nodes={nodes} />
          ))}
        </svg>
        {nodes.map((n) => (
          <FlowNode key={n.id} node={n} selected={selectedId === n.id} onSelect={onSelect} />
        ))}
      </div>
    </div>
  );
}
