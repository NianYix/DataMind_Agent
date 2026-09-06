"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, TopBar } from "@/components/shell/TopBar";
import { api } from "@/lib/api";

type Source = {
  id: string;
  name: string;
  db_type: string;
  host: string;
  port: number;
  database: string;
  username: string;
  ssl: boolean;
};

export default function DataSourcesPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [tables, setTables] = useState<string[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState("checking");
  const [form, setForm] = useState({
    name: "Mock Sales DB",
    db_type: "mock",
    host: "localhost",
    port: 5432,
    database: "sales",
    username: "demo",
    password: "demo",
    ssl: false,
  });

  async function refresh() {
    setSources((await api.dataSources()) as Source[]);
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
      await api.createDataSource(form, apiKey || undefined);
      setMessage("数据源已创建");
      await refresh();
    } catch (err) {
      setError(String(err));
    }
  }

  async function onTest(id: string) {
    setError(null);
    try {
      const res = await api.testDataSource(id);
      setMessage(res.ok ? "连接成功" : `失败: ${res.error}`);
    } catch (err) {
      setError(String(err));
    }
  }

  async function onTables(id: string) {
    setSelected(id);
    const res = await api.dataSourceTables(id);
    setTables(res.tables);
  }

  async function onRegister(table: string) {
    if (!selected) return;
    try {
      const ds = await api.registerRemoteDataset(selected, table);
      setMessage(`已注册 Dataset: ${(ds as { name?: string }).name || table}`);
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <AppShell topBar={<TopBar active="data-sources" health={health} />}>
      <div className="scrollbar-thin h-full overflow-auto">
        <main className="mx-auto grid max-w-5xl gap-6 px-6 py-6 lg:grid-cols-[1fr_1fr]">
          <form onSubmit={onCreate} className="panel space-y-3 rounded-md p-4">
            <h1 className="text-lg font-semibold">Data Sources</h1>
            <p className="text-xs text-[var(--text-muted)]">支持 mysql / postgresql / mock（本地无 Docker 验收）</p>
            {(
              [
                ["name", "Name"],
                ["db_type", "Type (mysql|postgresql|mock)"],
                ["host", "Host"],
                ["port", "Port"],
                ["database", "Database"],
                ["username", "Username"],
                ["password", "Password"],
              ] as const
            ).map(([key, label]) => (
              <label key={key} className="block text-sm">
                <span className="text-[var(--text-muted)]">{label}</span>
                <input
                  className="input-dark mt-1 w-full"
                  type={key === "password" ? "password" : key === "port" ? "number" : "text"}
                  value={String(form[key])}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      [key]: key === "port" ? Number(e.target.value) : e.target.value,
                    })
                  }
                />
              </label>
            ))}
            <label className="block text-sm">
              <span className="text-[var(--text-muted)]">X-API-Key（若需要）</span>
              <input className="input-dark mt-1 w-full" type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
            </label>
            <button type="submit" className="btn btn-primary">
              Create
            </button>
            {message ? <p className="text-sm text-[var(--success)]">{message}</p> : null}
            {error ? <p className="text-sm text-[var(--error)]">{error}</p> : null}
          </form>

          <section className="panel space-y-3 rounded-md p-4">
            <h2 className="label-caps">Sources</h2>
            <ul className="space-y-2">
              {sources.map((s) => (
                <li key={s.id} className="rounded border border-[var(--border)] bg-[var(--bg-1)] p-3 text-sm">
                  <div className="font-medium">{s.name}</div>
                  <div className="font-mono text-[10px] text-[var(--text-muted)]">
                    {s.db_type} · {s.host}:{s.port}/{s.database}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2">
                    <button type="button" className="btn" onClick={() => onTest(s.id)}>
                      Test
                    </button>
                    <button type="button" className="btn" onClick={() => onTables(s.id)}>
                      Tables
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            {tables.length ? (
              <div>
                <div className="label-caps mb-2">Tables → Dataset</div>
                <ul className="space-y-1">
                  {tables.map((t) => (
                    <li key={t}>
                      <button type="button" className="btn w-full text-left" onClick={() => onRegister(t)}>
                        Register {t}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>
        </main>
      </div>
    </AppShell>
  );
}
