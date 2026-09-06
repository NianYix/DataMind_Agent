const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

function authHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("datamind_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = {
    ...authHeaders(),
    ...(init?.headers as Record<string, string> | undefined),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    try {
      const data = JSON.parse(text) as { detail?: unknown };
      const detail = data.detail;
      if (typeof detail === "string") throw new Error(detail);
      if (Array.isArray(detail)) throw new Error(detail.map((d) => JSON.stringify(d)).join("; "));
    } catch (e) {
      if (e instanceof Error && e.message !== text) throw e;
    }
    throw new Error(text || res.statusText);
  }
  return res.json() as Promise<T>;
}


export type Workspace = { id: string; name: string; created_at?: string };
export type DatasetField = {
  id: string;
  name: string;
  inferred_type: string;
  null_ratio: number;
  nunique: number;
};
export type Dataset = {
  id: string;
  workspace_id: string;
  name: string;
  row_count: number;
  col_count: number;
  source_type?: string;
  table_name?: string | null;
  profile_json?: {
    summary_text?: string;
    time_range?: { start: string; end: string };
    duplicate_rows?: number;
    fields?: Array<Record<string, unknown>>;
  } | null;
  status: string;
  fields?: DatasetField[];
};
export type Conversation = {
  id: string;
  workspace_id: string;
  dataset_id: string | null;
  title: string;
};
export type Message = {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
};
export type AgentStep = {
  id: string;
  seq: number;
  agent_name: string;
  input_summary?: string | null;
  output_summary?: string | null;
  status: string;
};
export type AgentRun = {
  id: string;
  conversation_id: string;
  question: string;
  status: string;
  input_tokens?: number;
  output_tokens?: number;
  latency_ms?: number | null;
  estimated_cost?: number | null;
  final_answer?: string | null;
};
export type Evidence = {
  id: string;
  claim: string;
  tool_call_id?: string | null;
  payload_json?: {
    code_or_query?: string;
    result_preview?: unknown;
    tool_name?: string;
  } | null;
};
export type ChartItem = {
  id: string;
  chart_type: string;
  title: string;
  option_json: Record<string, unknown>;
};
export type EvalSuite = {
  id: string;
  name: string;
  description?: string;
  case_count: number;
  path?: string;
};
export type EvalCase = {
  id: string;
  case_id: string;
  agent_run_id?: string | null;
  status: string;
  scores_json?: Record<string, number | boolean | string[] | null> | null;
  final_answer?: string | null;
  latency_ms?: number | null;
  input_tokens?: number;
  output_tokens?: number;
  steps?: number;
  tool_stats_json?: Record<string, number> | null;
  error?: string | null;
};
export type EvalRun = {
  id: string;
  suite_id: string;
  mode: string;
  status: string;
  summary_json?: {
    task_success_rate?: number;
    tool_success_rate?: number | null;
    python_success_rate?: number | null;
    sql_success_rate?: number | null;
    avg_insight_score?: number;
    avg_calculation_score?: number;
    avg_hallucination_rate?: number;
    avg_steps?: number;
    avg_latency_ms?: number;
    avg_tokens?: number;
    avg_cost?: number | null;
    cases_total?: number;
    cases_passed?: number;
    heuristic?: boolean;
  } | null;
  created_at?: string | null;
  cases?: EvalCase[];
};

export const api = {
  health: () => request<{ status: string; auth_enabled?: boolean; version?: string }>("/api/health"),
  workspaces: () => request<Workspace[]>("/api/workspaces"),
  datasets: (workspaceId: string) =>
    request<Dataset[]>(`/api/workspaces/${workspaceId}/datasets`),
  dataset: (id: string) => request<Dataset>(`/api/datasets/${id}`),
  uploadDataset: async (workspaceId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Dataset>(`/api/workspaces/${workspaceId}/datasets`, {
      method: "POST",
      body: form,
    });
  },
  uploadSqlite: async (workspaceId: string, file: File, tableName: string, name?: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("table_name", tableName);
    if (name) form.append("name", name);
    return request<Dataset>(`/api/workspaces/${workspaceId}/datasets/sqlite`, {
      method: "POST",
      body: form,
    });
  },
  conversations: (workspaceId: string) =>
    request<Conversation[]>(`/api/workspaces/${workspaceId}/conversations`),
  createConversation: (workspaceId: string, datasetId: string, title?: string) =>
    request<Conversation>(`/api/workspaces/${workspaceId}/conversations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dataset_id: datasetId, title }),
    }),
  messages: (conversationId: string) =>
    request<Message[]>(`/api/conversations/${conversationId}/messages`),
  workspaceRuns: (workspaceId: string) =>
    request<AgentRun[]>(`/api/workspaces/${workspaceId}/agent-runs`),
  cancelRun: (runId: string) =>
    request<AgentRun>(`/api/agent-runs/${runId}/cancel`, { method: "POST" }),
  run: (runId: string) => request<AgentRun>(`/api/agent-runs/${runId}`),
  trace: (runId: string) => request<AgentStep[]>(`/api/agent-runs/${runId}/trace`),
  evidence: (id: string) => request<Evidence>(`/api/evidences/${id}`),
  evidences: (runId: string) => request<Evidence[]>(`/api/agent-runs/${runId}/evidences`),
  report: (runId: string) =>
    request<{ id: string; markdown: string }>(`/api/agent-runs/${runId}/report`),
  reportPdfUrl: (runId: string) => `${API_BASE}/api/agent-runs/${runId}/report.pdf`,
  charts: (runId: string) => request<ChartItem[]>(`/api/agent-runs/${runId}/charts`),
  settings: () => request<Record<string, unknown>>("/api/settings"),
  metrics: () => request<Record<string, unknown>>("/api/metrics"),
  exportUrl: (runId: string) => `${API_BASE}/api/agent-runs/${runId}/export`,
  evaluationSuites: () => request<EvalSuite[]>("/api/evaluation-suites"),
  evaluations: (limit = 50) => request<EvalRun[]>(`/api/evaluations?limit=${limit}`),
  evaluation: (id: string) => request<EvalRun>(`/api/evaluations/${id}`),
  evaluationSummary: (id: string) =>
    request<{ id: string; suite_id: string; mode: string; status: string; summary_json: Record<string, unknown> }>(
      `/api/evaluations/${id}/summary`,
    ),
  startEvaluation: (suiteId: string, mode: "mock" | "live", apiKey?: string) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) headers["X-API-Key"] = apiKey;
    return request<EvalRun>("/api/evaluations", {
      method: "POST",
      headers,
      body: JSON.stringify({ suite_id: suiteId, mode }),
    });
  },
  login: (username: string, password: string) =>
    request<{ access_token: string; user: { id: string; username: string; global_role: string } }>("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  me: () => request<{ id: string; username: string; global_role: string }>("/api/auth/me"),
  dataSources: (workspaceId?: string) =>
    request<
      Array<{
        id: string;
        name: string;
        db_type: string;
        host: string;
        port: number;
        database: string;
        username: string;
        ssl: boolean;
      }>
    >(`/api/data-sources${workspaceId ? `?workspace_id=${workspaceId}` : ""}`),
  createDataSource: (body: Record<string, unknown>, apiKey?: string) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) headers["X-API-Key"] = apiKey;
    return request("/api/data-sources", { method: "POST", headers, body: JSON.stringify(body) });
  },
  testDataSource: (id: string) => request<{ ok: boolean; error?: string }>(`/api/data-sources/${id}/test`, { method: "POST" }),
  dataSourceTables: (id: string) => request<{ tables: string[] }>(`/api/data-sources/${id}/tables`),
  registerRemoteDataset: (id: string, table_name: string, name?: string) =>
    request(`/api/data-sources/${id}/datasets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ table_name, name }),
    }),
  prompts: (name?: string) =>
    request<Array<{ id: string; name: string; content: string; version: number; is_active: boolean; role: string }>>(
      `/api/prompts${name ? `?name=${encodeURIComponent(name)}` : ""}`,
    ),
  createPrompt: (body: { name: string; content: string; activate?: boolean }, apiKey?: string) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) headers["X-API-Key"] = apiKey;
    return request("/api/prompts", { method: "POST", headers, body: JSON.stringify(body) });
  },
  activatePrompt: (name: string, version: number, apiKey?: string) => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey) headers["X-API-Key"] = apiKey;
    return request(`/api/prompts/${encodeURIComponent(name)}/activate`, {
      method: "POST",
      headers,
      body: JSON.stringify({ version }),
    });
  },
};


export async function streamMessage(
  conversationId: string,
  content: string,
  onEvent: (event: string, data: Record<string, unknown>) => void,
) {
  const res = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok || !res.body) {
    throw new Error(await res.text());
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventName = "message";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n");
    buffer = parts.pop() || "";
    for (const line of parts) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const raw = line.slice(5).trim();
        if (!raw) continue;
        try {
          onEvent(eventName, JSON.parse(raw));
        } catch {
          onEvent(eventName, { raw });
        }
        eventName = "message";
      }
    }
  }
}
