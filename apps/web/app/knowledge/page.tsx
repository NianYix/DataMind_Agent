"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, TopBar } from "@/components/shell/TopBar";
import { api } from "@/lib/api";

type KB = { id: string; name: string; description?: string | null; workspace_id: string };
type Doc = {
  id: string;
  filename: string;
  status: string;
  chunk_count: number;
  error?: string | null;
};
type Hit = { text: string; filename?: string; score?: number; doc_id?: string };

export default function KnowledgePage() {
  const [health, setHealth] = useState("checking");
  const [workspaceId, setWorkspaceId] = useState("");
  const [workspaces, setWorkspaces] = useState<Array<{ id: string; name: string }>>([]);
  const [kbs, setKbs] = useState<KB[]>([]);
  const [kbId, setKbId] = useState("");
  const [docs, setDocs] = useState<Doc[]>([]);
  const [name, setName] = useState("业务口径库");
  const [query, setQuery] = useState("华东口径是什么");
  const [hits, setHits] = useState<Hit[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshKbs(ws: string) {
    const list = await api.knowledgeBases(ws);
    setKbs(list);
    if (list.length && !list.find((k) => k.id === kbId)) {
      setKbId(list[0].id);
    }
  }

  async function refreshDocs(id: string) {
    if (!id) {
      setDocs([]);
      return;
    }
    setDocs(await api.knowledgeDocuments(id));
  }

  useEffect(() => {
    (async () => {
      try {
        await api.health();
        setHealth("ok");
        const ws = await api.workspaces();
        setWorkspaces(ws);
        if (ws[0]) {
          setWorkspaceId(ws[0].id);
          await refreshKbs(ws[0].id);
        }
      } catch (e) {
        setHealth("down");
        setError(String(e));
      }
    })();
  }, []);

  useEffect(() => {
    refreshDocs(kbId).catch((e) => setError(String(e)));
  }, [kbId]);

  async function onCreateKb(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const kb = await api.createKnowledgeBase({ workspace_id: workspaceId, name }, apiKey || undefined);
      setMessage(`已创建知识库 ${kb.name}`);
      await refreshKbs(workspaceId);
      setKbId(kb.id);
    } catch (err) {
      setError(String(err));
    }
  }

  async function onUpload(file: File | null) {
    if (!file || !kbId) return;
    setError(null);
    try {
      const doc = await api.uploadKnowledgeDocument(kbId, file, apiKey || undefined);
      setMessage(`已入库 ${doc.filename} · ${doc.chunk_count} chunks · ${doc.status}`);
      await refreshDocs(kbId);
    } catch (err) {
      setError(String(err));
    }
  }

  async function onSearch(e: FormEvent) {
    e.preventDefault();
    if (!kbId) return;
    setError(null);
    try {
      const res = await api.searchKnowledge(kbId, query);
      if (!res.success) {
        setError(res.error || "search failed");
        setHits([]);
        return;
      }
      setHits(res.results || []);
      setMessage(res.message || `命中 ${(res.results || []).length} 条`);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <AppShell
      topBar={
        <TopBar
          active="knowledge"
          health={health}
          workspaces={workspaces}
          workspaceId={workspaceId}
          onWorkspaceChange={(id) => {
            setWorkspaceId(id);
            refreshKbs(id).catch((e) => setError(String(e)));
          }}
        />
      }
    >
      <div className="scrollbar-thin h-full overflow-auto">
        <main className="mx-auto grid max-w-5xl gap-6 px-6 py-6 lg:grid-cols-[1fr_1fr]">
          <section className="space-y-4">
            <form onSubmit={onCreateKb} className="panel space-y-3 rounded-md p-4">
              <h1 className="text-lg font-semibold">Knowledge</h1>
              <p className="text-xs text-[var(--text-muted)]">上传 MD/TXT/PDF → 切分向量化 → 试检索 / Agent knowledge_search</p>
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">新知识库名称</span>
                <input className="input-dark mt-1 w-full" value={name} onChange={(e) => setName(e.target.value)} />
              </label>
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">X-API-Key（写操作可选）</span>
                <input className="input-dark mt-1 w-full" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
              </label>
              <button type="submit" className="btn btn-primary">
                Create KB
              </button>
            </form>

            <div className="panel space-y-3 rounded-md p-4">
              <div className="label-caps">Knowledge Bases</div>
              <select className="input-dark w-full" value={kbId} onChange={(e) => setKbId(e.target.value)}>
                {!kbs.length ? <option value="">暂无知识库</option> : null}
                {kbs.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.name}
                  </option>
                ))}
              </select>
              <label className="btn btn-primary inline-block cursor-pointer">
                Upload MD/TXT/PDF
                <input
                  type="file"
                  accept=".md,.txt,.pdf"
                  className="hidden"
                  onChange={(e) => onUpload(e.target.files?.[0] || null)}
                />
              </label>
              <ul className="space-y-2 text-sm">
                {docs.map((d) => (
                  <li key={d.id} className="rounded border border-[var(--border)] bg-[var(--bg-1)] px-3 py-2">
                    <div className="font-medium">{d.filename}</div>
                    <div className="font-mono text-[10px] text-[var(--text-muted)]">
                      {d.status} · {d.chunk_count} chunks
                    </div>
                    {d.error ? <div className="mt-1 text-[11px] text-[var(--error)]">{d.error}</div> : null}
                  </li>
                ))}
                {!docs.length ? <li className="text-xs text-[var(--text-muted)]">暂无文档</li> : null}
              </ul>
            </div>
          </section>

          <section className="panel space-y-3 rounded-md p-4">
            <form onSubmit={onSearch} className="space-y-3">
              <div className="label-caps">Try Search</div>
              <input className="input-dark w-full" value={query} onChange={(e) => setQuery(e.target.value)} />
              <button type="submit" className="btn btn-primary" disabled={!kbId}>
                Search
              </button>
            </form>
            {message ? <p className="text-sm text-[var(--success)]">{message}</p> : null}
            {error ? <p className="text-sm text-[var(--error)]">{error}</p> : null}
            <ul className="space-y-2">
              {hits.map((h, i) => (
                <li key={`${h.doc_id}-${i}`} className="rounded border border-[var(--border)] bg-[var(--bg-1)] p-3 text-sm">
                  <div className="font-mono text-[10px] text-[var(--text-muted)]">
                    {h.filename || "doc"} · score {h.score ?? "-"}
                  </div>
                  <pre className="mt-1 whitespace-pre-wrap text-[12px] leading-5 text-[var(--text-muted)]">{h.text}</pre>
                </li>
              ))}
            </ul>
          </section>
        </main>
      </div>
    </AppShell>
  );
}
