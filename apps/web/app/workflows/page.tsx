"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AppShell, TopBar } from "@/components/shell/TopBar";
import { api } from "@/lib/api";

type Wf = {
  id: string;
  name: string;
  description?: string | null;
  version: number;
  enabled: boolean;
  graph: Record<string, unknown>;
};

type Step = {
  id: string;
  seq: number;
  node_id: string;
  node_type: string;
  status: string;
  output?: Record<string, unknown> | null;
  error?: string | null;
  agent_run_id?: string | null;
};

export default function WorkflowsPage() {
  const [health, setHealth] = useState("checking");
  const [workspaces, setWorkspaces] = useState<Array<{ id: string; name: string }>>([]);
  const [workspaceId, setWorkspaceId] = useState("");
  const [datasets, setDatasets] = useState<Array<{ id: string; name: string }>>([]);
  const [datasetId, setDatasetId] = useState("");
  const [list, setList] = useState<Wf[]>([]);
  const [templates, setTemplates] = useState<Array<{ id: string; name: string; description?: string }>>([]);
  const [selectedId, setSelectedId] = useState("");
  const [graphText, setGraphText] = useState("");
  const [name, setName] = useState("我的工作流");
  const [question, setQuestion] = useState("为什么 8 月销售下降？");
  const [apiKey, setApiKey] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<string | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const selected = useMemo(() => list.find((w) => w.id === selectedId) || null, [list, selectedId]);

  const nodes = useMemo(() => {
    try {
      const g = JSON.parse(graphText || "{}") as { nodes?: Array<{ id: string; type: string }> };
      return g.nodes || [];
    } catch {
      return [];
    }
  }, [graphText]);

  async function refreshList(ws: string) {
    const items = await api.workflows(ws);
    setList(items as Wf[]);
    if (items.length && !items.find((w) => w.id === selectedId)) {
      const first = items[0] as Wf;
      setSelectedId(first.id);
      setGraphText(JSON.stringify(first.graph, null, 2));
      setName(first.name);
    }
  }

  useEffect(() => {
    (async () => {
      try {
        await api.health();
        setHealth("ok");
        const [ws, tpls] = await Promise.all([api.workspaces(), api.workflowTemplates()]);
        setWorkspaces(ws);
        setTemplates(tpls);
        if (ws[0]) {
          setWorkspaceId(ws[0].id);
          const ds = await api.datasets(ws[0].id);
          setDatasets(ds);
          if (ds[0]) setDatasetId(ds[0].id);
          await refreshList(ws[0].id);
        }
      } catch (e) {
        setHealth("down");
        setError(String(e));
      }
    })();
  }, []);

  useEffect(() => {
    if (!selected) return;
    setGraphText(JSON.stringify(selected.graph, null, 2));
    setName(selected.name);
  }, [selectedId]);

  async function onCreateFromTemplate(templateId: string) {
    setError(null);
    try {
      const w = (await api.createWorkflow(
        { workspace_id: workspaceId, template_id: templateId, name: `${name || "Workflow"}` },
        apiKey || undefined,
      )) as Wf;
      setMessage(`已从模板创建 ${w.name}`);
      await refreshList(workspaceId);
      setSelectedId(w.id);
    } catch (e) {
      setError(String(e));
    }
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!selectedId) return;
    setError(null);
    try {
      const graph = JSON.parse(graphText);
      await api.updateWorkflow(selectedId, { name, graph }, apiKey || undefined);
      setMessage("已保存");
      await refreshList(workspaceId);
    } catch (err) {
      setError(String(err));
    }
  }

  async function onRun(e: FormEvent) {
    e.preventDefault();
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    setSteps([]);
    try {
      const run = await api.startWorkflowRun(selectedId, {
        question: question || undefined,
        dataset_id: datasetId || undefined,
      });
      setRunId(run.id);
      setRunStatus(run.status);
      const st = await api.workflowRunSteps(run.id);
      setSteps(st);
      setMessage(run.status === "done" ? "Run 完成" : `Run 状态: ${run.status}${run.error ? ` · ${run.error}` : ""}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell
      topBar={
        <TopBar
          active="workflows"
          health={health}
          workspaces={workspaces}
          workspaceId={workspaceId}
          onWorkspaceChange={async (id) => {
            setWorkspaceId(id);
            const ds = await api.datasets(id);
            setDatasets(ds);
            setDatasetId(ds[0]?.id || "");
            await refreshList(id);
          }}
        />
      }
    >
      <div className="scrollbar-thin h-full overflow-auto">
        <main className="mx-auto grid max-w-5xl gap-6 px-6 py-6 lg:grid-cols-[1fr_1.2fr]">
          <section className="space-y-4">
            <div>
              <h1 className="text-lg font-semibold text-[var(--text)]">Workflows</h1>
              <p className="mt-1 text-sm text-[var(--text-muted)]">JSON DAG：start → analyze → condition? → end</p>
            </div>

            <div className="space-y-2 border-t border-[var(--border)] pt-4">
              <div className="label-caps">Templates</div>
              <div className="flex flex-wrap gap-2">
                {templates.map((t) => (
                  <button key={t.id} type="button" className="btn" onClick={() => onCreateFromTemplate(t.id)}>
                    {t.name}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2 border-t border-[var(--border)] pt-4">
              <div className="label-caps">Saved</div>
              <select
                className="input-dark w-full"
                value={selectedId}
                onChange={(e) => setSelectedId(e.target.value)}
              >
                {!list.length ? <option value="">暂无工作流</option> : null}
                {list.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.name} · v{w.version}
                  </option>
                ))}
              </select>
            </div>

            <form onSubmit={onRun} className="space-y-3 border-t border-[var(--border)] pt-4">
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">Question override</span>
                <input className="input-dark mt-1 w-full" value={question} onChange={(e) => setQuestion(e.target.value)} />
              </label>
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">Dataset</span>
                <select className="input-dark mt-1 w-full" value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
                  {!datasets.length ? <option value="">暂无数据集</option> : null}
                  {datasets.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <button type="submit" className="btn btn-primary" disabled={!selectedId || busy}>
                {busy ? "Running…" : "Run"}
              </button>
            </form>

            {runId ? (
              <div className="space-y-2 border-t border-[var(--border)] pt-4">
                <div className="font-mono text-xs text-[var(--text-muted)]">
                  run={runId.slice(0, 8)} · {runStatus}
                </div>
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-[var(--text-muted)]">
                      <th className="py-1 pr-2">#</th>
                      <th className="py-1 pr-2">node</th>
                      <th className="py-1 pr-2">type</th>
                      <th className="py-1">status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {steps.map((s) => (
                      <tr key={s.id} className="border-t border-[var(--border)]">
                        <td className="py-1 pr-2 font-mono">{s.seq}</td>
                        <td className="py-1 pr-2 font-mono">{s.node_id}</td>
                        <td className="py-1 pr-2">{s.node_type}</td>
                        <td className="py-1 font-mono">
                          {s.status}
                          {s.error ? ` · ${s.error}` : ""}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </section>

          <section className="space-y-3">
            <form onSubmit={onSave} className="space-y-3">
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">Name</span>
                <input className="input-dark mt-1 w-full" value={name} onChange={(e) => setName(e.target.value)} />
              </label>
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">X-API-Key（写操作可选）</span>
                <input
                  className="input-dark mt-1 w-full"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </label>
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">Graph JSON</span>
                <textarea
                  className="input-dark mt-1 min-h-[280px] w-full font-mono text-[11px]"
                  value={graphText}
                  onChange={(e) => setGraphText(e.target.value)}
                />
              </label>
              <button type="submit" className="btn btn-primary" disabled={!selectedId}>
                Save
              </button>
            </form>

            <div>
              <div className="label-caps mb-1">Nodes</div>
              <ul className="space-y-1 font-mono text-[11px] text-[var(--text-muted)]">
                {nodes.map((n) => (
                  <li key={n.id}>
                    {n.id} · {n.type}
                  </li>
                ))}
                {!nodes.length ? <li>解析 graph 后显示</li> : null}
              </ul>
            </div>

            {message ? <p className="text-sm text-[var(--success)]">{message}</p> : null}
            {error ? <p className="text-sm text-[var(--error)]">{error}</p> : null}
          </section>
        </main>
      </div>
    </AppShell>
  );
}
