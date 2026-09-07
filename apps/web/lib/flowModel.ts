export type FlowKind = "ai" | "logic" | "data" | "action" | "system";
export type FlowNodeStatus = "pending" | "running" | "done" | "error";

export type TraceItem = {
  type: string;
  summary: string;
  inputSummary?: string;
  outputSummary?: string;
  stepStatus?: string;
};

export type FlowNodeModel = {
  id: string;
  type: string;
  kind: FlowKind;
  title: string;
  summary: string;
  inputSummary?: string;
  outputSummary?: string;
  stepStatus?: string;
  status: FlowNodeStatus;
  x: number;
  y: number;
};

export type FlowEdgeModel = {
  id: string;
  from: string;
  to: string;
  active?: boolean;
  error?: boolean;
};

export type GraphModel = {
  nodes: FlowNodeModel[];
  edges: FlowEdgeModel[];
  width: number;
  height: number;
};

const NODE_W = 200;
const NODE_H = 88;
const GAP_X = 48;
const GAP_Y = 36;
const PAD = 32;

function kindOf(type: string): FlowKind {
  const t = type.toLowerCase();
  if (/(error|cancel)/.test(t)) return "system";
  if (/(metric)/.test(t)) return "system";
  if (/(tool|execute|sql|python|statistics|anomaly|http|search)/.test(t)) return "action";
  if (/(observe|observation|data|profile)/.test(t)) return "data";
  if (/(plan|understand)/.test(t)) return "logic";
  if (/(insight|report|final|supervisor|agent|llm|critic|planner|understand)/.test(t)) return "ai";
  return "logic";
}

function titleOf(type: string): string {
  if (!type) return "Step";
  const map: Record<string, string> = {
    critic: "Critic",
    insight: "Insight",
    supervisor: "Supervisor",
    planner: "Planner",
    understand: "Understand",
    report: "Report",
    Analyst: "Analyst",
    Tools: "Tools",
  };
  if (map[type]) return map[type];
  return type.replace(/_/g, " ");
}

export function buildGraphFromTrace(
  items: TraceItem[],
  opts?: { running?: boolean },
): GraphModel {
  if (!items.length) {
    const id = "N-000";
    return {
      nodes: [
        {
          id,
          type: "idle",
          kind: "system",
          title: "Awaiting Run",
          summary: "提交问题后，Agent Trace 将在此展开为逻辑节点",
          status: "pending",
          x: PAD,
          y: PAD,
        },
      ],
      edges: [],
      width: PAD * 2 + NODE_W,
      height: PAD * 2 + NODE_H,
    };
  }

  const cols = Math.min(3, Math.max(1, Math.ceil(Math.sqrt(items.length))));
  const nodes: FlowNodeModel[] = items.map((item, idx) => {
    const col = idx % cols;
    const row = Math.floor(idx / cols);
    const isLast = idx === items.length - 1;
    let status: FlowNodeStatus = "done";
    if (opts?.running && isLast) status = "running";
    if (/error/i.test(item.type) || /error/i.test(item.stepStatus || "")) status = "error";
    return {
      id: `N-${String(idx + 1).padStart(3, "0")}`,
      type: item.type,
      kind: kindOf(item.type),
      title: titleOf(item.type),
      summary: item.summary || item.outputSummary || item.inputSummary || "",
      inputSummary: item.inputSummary,
      outputSummary: item.outputSummary || item.summary,
      stepStatus: item.stepStatus,
      status,
      x: PAD + col * (NODE_W + GAP_X),
      y: PAD + row * (NODE_H + GAP_Y),
    };
  });

  const edges: FlowEdgeModel[] = [];
  for (let i = 0; i < nodes.length - 1; i++) {
    edges.push({
      id: `E-${i + 1}`,
      from: nodes[i].id,
      to: nodes[i + 1].id,
      active: Boolean(opts?.running && i === nodes.length - 2),
      error: nodes[i + 1].status === "error",
    });
  }

  const maxX = Math.max(...nodes.map((n) => n.x)) + NODE_W + PAD;
  const maxY = Math.max(...nodes.map((n) => n.y)) + NODE_H + PAD;
  return { nodes, edges, width: maxX, height: maxY };
}

export function canvasBounds(nodes: FlowNodeModel[]): { width: number; height: number } {
  if (!nodes.length) return { width: 480, height: 320 };
  const maxX = Math.max(...nodes.map((n) => n.x)) + NODE_W + PAD;
  const maxY = Math.max(...nodes.map((n) => n.y)) + NODE_H + PAD;
  return { width: Math.max(maxX, 480), height: Math.max(maxY, 320) };
}

export const FLOW_NODE_SIZE = { w: NODE_W, h: NODE_H };

export function kindColor(kind: FlowKind): string {
  switch (kind) {
    case "ai":
      return "var(--node-ai)";
    case "logic":
      return "var(--node-logic)";
    case "data":
      return "var(--node-data)";
    case "action":
      return "var(--node-action)";
    default:
      return "var(--node-system)";
  }
}
