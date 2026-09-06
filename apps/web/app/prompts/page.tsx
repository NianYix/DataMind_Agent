"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, TopBar } from "@/components/shell/TopBar";
import { api } from "@/lib/api";

type Prompt = {
  id: string;
  name: string;
  content: string;
  version: number;
  is_active: boolean;
  role: string;
};

export default function PromptsPage() {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [name, setName] = useState("system_analyst");
  const [content, setContent] = useState(
    "You are the Planner Agent for DataMind. Prefer progressive drill-down and return STRICT JSON plan.",
  );
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState("checking");

  async function refresh() {
    setPrompts(await api.prompts());
  }

  useEffect(() => {
    api
      .health()
      .then(() => setHealth("ok"))
      .catch(() => setHealth("down"));
    refresh().catch((e) => setError(String(e)));
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api.createPrompt({ name, content, activate: true }, apiKey || undefined);
      setMessage("已创建并激活");
      await refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  async function onActivate(p: Prompt) {
    try {
      await api.activatePrompt(p.name, p.version, apiKey || undefined);
      setMessage(`已激活 ${p.name} v${p.version}`);
      await refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <AppShell topBar={<TopBar active="prompts" health={health} />}>
      <div className="scrollbar-thin h-full overflow-auto">
        <main className="mx-auto grid max-w-5xl gap-6 px-6 py-6 lg:grid-cols-[1fr_1fr]">
          <form onSubmit={onCreate} className="panel space-y-3 rounded-md p-4">
            <h1 className="text-lg font-semibold">Prompts</h1>
            <label className="block text-sm">
              <span className="text-[var(--text-muted)]">Name</span>
              <input className="input-dark mt-1 w-full" value={name} onChange={(e) => setName(e.target.value)} />
            </label>
            <label className="block text-sm">
              <span className="text-[var(--text-muted)]">Content</span>
              <textarea className="input-dark mt-1 min-h-[160px] w-full" value={content} onChange={(e) => setContent(e.target.value)} />
            </label>
            <label className="block text-sm">
              <span className="text-[var(--text-muted)]">X-API-Key</span>
              <input className="input-dark mt-1 w-full" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
            </label>
            <button type="submit" className="btn btn-primary">
              Create + Activate
            </button>
            {message ? <p className="text-sm text-[var(--success)]">{message}</p> : null}
            {error ? <p className="text-sm text-[var(--error)]">{error}</p> : null}
          </form>

          <section className="panel space-y-2 rounded-md p-4">
            <h2 className="label-caps">Versions</h2>
            <ul className="space-y-2">
              {prompts.map((p) => (
                <li key={p.id} className="rounded border border-[var(--border)] bg-[var(--bg-1)] p-3 text-sm">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs">
                      {p.name} · v{p.version} {p.is_active ? "· ACTIVE" : ""}
                    </span>
                    {!p.is_active ? (
                      <button type="button" className="btn" onClick={() => onActivate(p)}>
                        Activate
                      </button>
                    ) : null}
                  </div>
                  <pre className="mt-2 max-h-28 overflow-auto whitespace-pre-wrap text-[11px] text-[var(--text-muted)]">
                    {p.content}
                  </pre>
                </li>
              ))}
              {!prompts.length ? <li className="text-xs text-[var(--text-muted)]">暂无自定义 Prompt，将使用内置默认</li> : null}
            </ul>
          </section>
        </main>
      </div>
    </AppShell>
  );
}
