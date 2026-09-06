"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { AgentPanel } from "@/components/agent/AgentPanel";
import { LogicCanvas } from "@/components/canvas/LogicCanvas";
import { ExecutionBar, RunMetrics } from "@/components/execution/ExecutionBar";
import { Inspector } from "@/components/inspector/Inspector";
import { AppShell, TopBar } from "@/components/shell/TopBar";
import {
  AgentRun,
  AgentStep,
  ChartItem,
  Conversation,
  Dataset,
  Evidence,
  Message,
  Workspace,
  api,
  streamMessage,
} from "@/lib/api";
import { TraceItem, buildGraphFromTrace } from "@/lib/flowModel";
import { deriveRunStatus } from "@/lib/runStatus";

export default function HomePage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [datasetId, setDatasetId] = useState("");
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [input, setInput] = useState("为什么 8 月销售下降？");
  const [running, setRunning] = useState(false);
  const [liveTrace, setLiveTrace] = useState<TraceItem[]>([]);
  const [charts, setCharts] = useState<ChartItem[]>([]);
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [evidences, setEvidences] = useState<Evidence[]>([]);
  const [report, setReport] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [metrics, setMetrics] = useState<RunMetrics>({});
  const [sqliteTable, setSqliteTable] = useState("sales");
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState("checking");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const selectedDataset = useMemo(
    () => datasets.find((d) => d.id === datasetId) || dataset,
    [datasets, datasetId, dataset],
  );

  const traceItems: TraceItem[] = useMemo(() => {
    if (steps.length) {
      return steps.map((s) => ({
        type: s.agent_name,
        summary: s.output_summary || s.input_summary || "",
      }));
    }
    return liveTrace;
  }, [steps, liveTrace]);

  const graph = useMemo(
    () => buildGraphFromTrace(traceItems, { running }),
    [traceItems, running],
  );

  const selectedNode = useMemo(
    () => graph.nodes.find((n) => n.id === selectedNodeId) || null,
    [graph.nodes, selectedNodeId],
  );

  const runStatus = deriveRunStatus({
    running,
    error,
    hasResult: Boolean(report || messages.some((m) => m.role === "assistant")),
  });

  const latestSummary = traceItems.length
    ? traceItems[traceItems.length - 1]?.summary
    : undefined;

  const refreshWorkspace = useCallback(
    async (wsId: string) => {
      const [ds, convs, runList] = await Promise.all([
        api.datasets(wsId),
        api.conversations(wsId),
        api.workspaceRuns(wsId).catch(() => []),
      ]);
      setDatasets(ds);
      setConversations(convs);
      setRuns(runList);
      if (ds.length && !datasetId) setDatasetId(ds[0].id);
    },
    [datasetId],
  );

  useEffect(() => {
    (async () => {
      try {
        await api.health();
        setHealth("ok");
        const ws = await api.workspaces();
        setWorkspaces(ws);
        if (ws[0]) {
          setWorkspaceId(ws[0].id);
          await refreshWorkspace(ws[0].id);
        }
      } catch (e) {
        setHealth("down");
        setError(e instanceof Error ? e.message : "API unavailable");
      }
    })();
  }, [refreshWorkspace]);

  useEffect(() => {
    if (!datasetId) return;
    api.dataset(datasetId).then(setDataset).catch(() => setDataset(null));
  }, [datasetId]);

  useEffect(() => {
    if (!conversationId) return;
    api.messages(conversationId).then(setMessages).catch(() => setMessages([]));
  }, [conversationId]);

  useEffect(() => {
    if (graph.nodes.length) {
      const last = graph.nodes[graph.nodes.length - 1];
      if (running) setSelectedNodeId(last.id);
    }
  }, [graph.nodes, running]);

  async function loadRun(id: string) {
    setRunId(id);
    const [trace, chartsRes, reportRes, evs, run] = await Promise.all([
      api.trace(id),
      api.charts(id),
      api.report(id).catch(() => null),
      api.evidences(id).catch(() => []),
      api.run(id).catch(() => null),
    ]);
    setSteps(trace);
    setLiveTrace([]);
    setCharts(chartsRes);
    setReport(reportRes?.markdown || "");
    setEvidences(evs);
    setEvidence(evs[0] || null);
    if (run) {
      setMetrics({
        input_tokens: run.input_tokens,
        output_tokens: run.output_tokens,
        latency_ms: run.latency_ms ?? undefined,
        estimated_cost: run.estimated_cost,
      });
    }
  }

  async function onUpload(file: File | null) {
    if (!file || !workspaceId) return;
    setError(null);
    try {
      const ds = await api.uploadDataset(workspaceId, file);
      await refreshWorkspace(workspaceId);
      setDatasetId(ds.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
  }

  async function onUploadSqlite(file: File | null) {
    if (!file || !workspaceId) return;
    setError(null);
    try {
      const ds = await api.uploadSqlite(workspaceId, file, sqliteTable || "sales");
      await refreshWorkspace(workspaceId);
      setDatasetId(ds.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "SQLite upload failed");
    }
  }

  async function ensureConversation() {
    if (conversationId) return conversationId;
    if (!workspaceId || !datasetId) throw new Error("请先选择数据集");
    const conv = await api.createConversation(workspaceId, datasetId);
    setConversationId(conv.id);
    setConversations((prev) => [conv, ...prev]);
    return conv.id;
  }

  async function onCancel() {
    if (!runId) return;
    try {
      await api.cancelRun(runId);
      setLiveTrace((prev) => [...prev, { type: "cancelled", summary: "已请求取消" }]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "取消失败");
    }
  }

  async function onAsk(e?: FormEvent) {
    e?.preventDefault();
    if (!input.trim() || running) return;
    setError(null);
    setRunning(true);
    setLiveTrace([]);
    setCharts([]);
    setSteps([]);
    setEvidences([]);
    setReport("");
    setEvidence(null);
    setMetrics({});
    setRunId(null);
    setSelectedNodeId(null);

    try {
      const cid = await ensureConversation();
      setMessages((prev) => [
        ...prev,
        {
          id: `local-${Date.now()}`,
          conversation_id: cid,
          role: "user",
          content: input.trim(),
        },
      ]);

      let localRunId: string | null = null;
      await streamMessage(cid, input.trim(), (event, data) => {
        if (event === "step") {
          setLiveTrace((prev) => [
            ...prev,
            { type: String(data.type || "step"), summary: String(data.summary || "") },
          ]);
          if (data.type === "metrics") {
            setMetrics({
              input_tokens: Number(data.input_tokens || 0),
              output_tokens: Number(data.output_tokens || 0),
              latency_ms: Number(data.latency_ms || 0),
              estimated_cost: (data.estimated_cost as number | null) ?? null,
            });
          }
          if (data.type === "cancelled") {
            setError("分析已取消");
          }
        } else if (event === "observation") {
          setLiveTrace((prev) => [
            ...prev,
            { type: "observation", summary: String(data.summary || "") },
          ]);
          if (data.evidence_id) {
            api.evidence(String(data.evidence_id)).then((ev) => {
              setEvidence(ev);
              setEvidences((prev) => {
                if (prev.some((x) => x.id === ev.id)) return prev;
                return [...prev, ev];
              });
            });
          }
        } else if (event === "chart") {
          setCharts((prev) => [
            ...prev,
            {
              id: String(data.chart_id),
              chart_type: "auto",
              title: String(data.title || "Chart"),
              option_json: (data.option as Record<string, unknown>) || {},
            },
          ]);
        } else if (event === "final") {
          const answer = String(data.answer || "");
          localRunId = data.run_id ? String(data.run_id) : null;
          setRunId(localRunId);
          setMessages((prev) => [
            ...prev,
            {
              id: `assistant-${Date.now()}`,
              conversation_id: cid,
              role: "assistant",
              content: answer,
            },
          ]);
        } else if (event === "error") {
          setError(String(data.message || "Agent error"));
        }
      });

      if (localRunId) {
        await loadRun(localRunId);
      }
      setInput("");
      await refreshWorkspace(workspaceId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "分析失败");
    } finally {
      setRunning(false);
    }
  }

  return (
    <AppShell
      topBar={
        <TopBar
          active="workspace"
          health={health}
          runStatus={runStatus}
          workspaces={workspaces}
          workspaceId={workspaceId}
          onWorkspaceChange={(id) => {
            setWorkspaceId(id);
            setConversationId("");
            refreshWorkspace(id);
          }}
          onRun={() => onAsk()}
          onStop={onCancel}
          running={running}
          canRun={Boolean(datasetId && input.trim())}
        />
      }
    >
      <div className="grid h-full min-h-0 grid-rows-[1fr_auto]">
        <div className="grid min-h-0 grid-cols-1 md:grid-cols-[280px_minmax(0,1fr)_320px]">
          <div className="min-h-0 md:block">
            <AgentPanel
              runStatus={runStatus}
              latestSummary={latestSummary}
              datasets={datasets}
              datasetId={datasetId}
              onSelectDataset={(id) => {
                setDatasetId(id);
                setConversationId("");
              }}
              onUpload={onUpload}
              onUploadSqlite={onUploadSqlite}
              sqliteTable={sqliteTable}
              onSqliteTableChange={setSqliteTable}
              conversations={conversations}
              conversationId={conversationId}
              onSelectConversation={setConversationId}
              runs={runs}
              runId={runId}
              onSelectRun={loadRun}
              messages={messages}
              input={input}
              onInputChange={setInput}
              onAsk={onAsk}
              running={running}
              error={error}
            />
          </div>

          <section className="flex min-h-0 min-w-0 flex-col border-x border-[var(--border)] bg-[var(--bg-1)]">
            <div className="flex shrink-0 items-center justify-between border-b border-[var(--border)] px-3 py-2">
              <div>
                <div className="text-xs font-medium text-[var(--text)]">Logic Canvas</div>
                <div className="font-mono text-[10px] text-[var(--text-muted)]">
                  NODE→EDGE→STATE · {graph.nodes.length} nodes
                </div>
              </div>
            </div>
            <div className="min-h-0 flex-1">
              <LogicCanvas
                nodes={graph.nodes}
                edges={graph.edges}
                width={graph.width}
                height={graph.height}
                selectedId={selectedNodeId}
                onSelect={setSelectedNodeId}
              />
            </div>
          </section>

          <div className="min-h-0">
            <Inspector
              dataset={selectedDataset}
              selectedNode={selectedNode}
              evidences={evidences}
              evidence={evidence}
              onSelectEvidence={setEvidence}
              charts={charts}
              report={report}
              runId={runId}
            />
          </div>
        </div>

        <ExecutionBar items={traceItems} metrics={metrics} runId={runId} runStatus={runStatus} />
      </div>
    </AppShell>
  );
}
