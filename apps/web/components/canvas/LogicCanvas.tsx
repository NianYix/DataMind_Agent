"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  FLOW_NODE_SIZE,
  FlowEdgeModel,
  FlowNodeModel,
  canvasBounds,
  kindColor,
} from "@/lib/flowModel";

const DRAG_THRESHOLD = 8;

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
  dragging,
  onPointerDown,
  onPointerMove,
  onPointerUp,
}: {
  node: FlowNodeModel;
  selected: boolean;
  dragging: boolean;
  onPointerDown: (id: string, e: React.PointerEvent<HTMLButtonElement>) => void;
  onPointerMove: (e: React.PointerEvent<HTMLButtonElement>) => void;
  onPointerUp: (e: React.PointerEvent<HTMLButtonElement>) => void;
}) {
  const accent = kindColor(node.kind);

  return (
    <button
      type="button"
      onPointerDown={(e) => onPointerDown(node.id, e)}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      className={`absolute touch-none select-none text-left ${node.status === "running" ? "node-running" : ""} ${
        dragging ? "z-10 cursor-grabbing" : "cursor-grab"
      }`}
      style={{
        left: node.x,
        top: node.y,
        width: FLOW_NODE_SIZE.w,
        height: FLOW_NODE_SIZE.h,
      }}
      title={node.summary || undefined}
    >
      <div
        className="pointer-events-none h-full overflow-hidden rounded-md border bg-[var(--panel)] px-2.5 py-2"
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
  layoutKey,
  onSelect,
}: {
  nodes: FlowNodeModel[];
  edges: FlowEdgeModel[];
  width: number;
  height: number;
  selectedId: string | null;
  /** Reset drag offsets when Run / trace identity changes */
  layoutKey?: string | null;
  onSelect: (id: string) => void;
}) {
  const [overlays, setOverlays] = useState<Record<string, { x: number; y: number }>>({});
  const dragRef = useRef<{
    id: string;
    pointerId: number;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    moved: boolean;
  } | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const displayRef = useRef<FlowNodeModel[]>([]);

  useEffect(() => {
    setOverlays({});
  }, [layoutKey]);

  const displayNodes = useMemo(
    () =>
      nodes.map((n) => {
        const o = overlays[n.id];
        return o ? { ...n, x: o.x, y: o.y } : n;
      }),
    [nodes, overlays],
  );
  displayRef.current = displayNodes;

  const bounds = useMemo(() => {
    const b = canvasBounds(displayNodes);
    return {
      width: Math.max(b.width, width, 480),
      height: Math.max(b.height, height, 320),
    };
  }, [displayNodes, width, height]);

  const endDrag = useCallback(
    (e: React.PointerEvent<HTMLButtonElement>) => {
      const d = dragRef.current;
      if (!d || e.pointerId !== d.pointerId) return;
      const moved = d.moved;
      const id = d.id;
      dragRef.current = null;
      setDraggingId(null);
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch {
        /* ignore */
      }
      if (!moved) onSelect(id);
    },
    [onSelect],
  );

  const onNodePointerDown = useCallback((id: string, e: React.PointerEvent<HTMLButtonElement>) => {
    if (e.button !== 0) return;
    const node = displayRef.current.find((n) => n.id === id);
    if (!node) return;
    e.currentTarget.setPointerCapture(e.pointerId);
    dragRef.current = {
      id,
      pointerId: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      originX: node.x,
      originY: node.y,
      moved: false,
    };
    setDraggingId(id);
  }, []);

  const onNodePointerMove = useCallback((e: React.PointerEvent<HTMLButtonElement>) => {
    const d = dragRef.current;
    if (!d || e.pointerId !== d.pointerId) return;
    const dx = e.clientX - d.startX;
    const dy = e.clientY - d.startY;
    if (!d.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
    d.moved = true;
    const x = Math.max(8, d.originX + dx);
    const y = Math.max(8, d.originY + dy);
    setOverlays((prev) => ({ ...prev, [d.id]: { x, y } }));
  }, []);

  return (
    <div className="canvas-grid relative h-full min-h-0 w-full overflow-auto">
      <div className="relative" style={{ width: bounds.width, height: bounds.height }}>
        <svg className="pointer-events-none absolute inset-0" width={bounds.width} height={bounds.height}>
          {edges.map((ed) => (
            <FlowEdge key={ed.id} edge={ed} nodes={displayNodes} />
          ))}
        </svg>
        {displayNodes.map((n) => (
          <FlowNode
            key={n.id}
            node={n}
            selected={selectedId === n.id}
            dragging={draggingId === n.id}
            onPointerDown={onNodePointerDown}
            onPointerMove={onNodePointerMove}
            onPointerUp={endDrag}
          />
        ))}
      </div>
    </div>
  );
}
