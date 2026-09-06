"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell, TopBar } from "@/components/shell/TopBar";
import { api } from "@/lib/api";

type ServerRow = {
  id: string;
  status: string;
  error?: string | null;
  tool_count: number;
  tools: Array<{
    name: string;
    original_name?: string;
    description?: string;
  }>;
};

export default function McpPage() {
  const [health, setHealth] = useState("checking");
  const [enabled, setEnabled] = useState(false);
  const [configPath, setConfigPath] = useState("");
  const [servers, setServers] = useState<ServerRow[]>([]);
  const [apiKey, setApiKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const st = await api.mcpStatus();
    setEnabled(!!st.enabled);
    setConfigPath(st.config_path || "");
    setServers(st.servers || []);
  }

  useEffect(() => {
    (async () => {
      try {
        await api.health();
        setHealth("ok");
        await refresh();
      } catch (e) {
        setHealth("down");
        setError(String(e));
      }
    })();
  }, []);

  async function onReload(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      await api.mcpReload(apiKey || undefined);
      await refresh();
      setMessage("已重新加载 MCP 配置");
    } catch (err) {
      setError(String(err));
    }
  }

  return (
    <AppShell topBar={<TopBar active="mcp" health={health} />}>
      <div className="scrollbar-thin h-full overflow-auto">
        <main className="mx-auto flex w-full max-w-4xl flex-col gap-6 px-4 py-6">
          <div>
            <h1 className="text-lg font-semibold text-[var(--text)]">MCP</h1>
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              外部 MCP Server 连接状态与桥接工具目录（默认关闭，改 .env 中 MCP_ENABLED）
            </p>
          </div>

          <section className="space-y-2 border-t border-[var(--border)] pt-4">
            <div className="font-mono text-xs text-[var(--text-muted)]">
              MCP_ENABLED = <span className="text-[var(--text)]">{String(enabled)}</span>
            </div>
            <div className="font-mono text-xs text-[var(--text-muted)] break-all">
              config = <span className="text-[var(--text)]">{configPath || "—"}</span>
            </div>
            {!enabled ? (
              <p className="text-sm text-[var(--text-muted)]">
                当前未启用。将 <code className="font-mono text-[var(--text)]">MCP_ENABLED=true</code> 并配置{" "}
                <code className="font-mono text-[var(--text)]">mcp_servers.json</code>（见仓库{" "}
                <code className="font-mono">mcp_servers.example.json</code>）后重启后端。
              </p>
            ) : null}
          </section>

          <section className="space-y-3 border-t border-[var(--border)] pt-4">
            <h2 className="text-sm font-medium text-[var(--text)]">Servers</h2>
            {servers.length === 0 ? (
              <p className="text-sm text-[var(--text-muted)]">暂无已连接的 Server</p>
            ) : (
              <ul className="space-y-4">
                {servers.map((s) => (
                  <li key={s.id} className="space-y-2">
                    <div className="flex flex-wrap items-baseline gap-3">
                      <span className="font-mono text-sm text-[var(--text)]">{s.id}</span>
                      <span className="font-mono text-xs text-[var(--text-muted)]">{s.status}</span>
                      <span className="font-mono text-xs text-[var(--text-muted)]">{s.tool_count} tools</span>
                    </div>
                    {s.error ? <p className="text-xs text-[var(--error)]">{s.error}</p> : null}
                    {s.tools?.length ? (
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="text-[var(--text-muted)]">
                            <th className="py-1 pr-3 font-medium">bridged name</th>
                            <th className="py-1 pr-3 font-medium">original</th>
                            <th className="py-1 font-medium">description</th>
                          </tr>
                        </thead>
                        <tbody>
                          {s.tools.map((t) => (
                            <tr key={t.name} className="border-t border-[var(--border)]">
                              <td className="py-1.5 pr-3 font-mono text-[var(--text)]">{t.name}</td>
                              <td className="py-1.5 pr-3 font-mono text-[var(--text-muted)]">{t.original_name}</td>
                              <td className="py-1.5 text-[var(--text-muted)]">{t.description || "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <form onSubmit={onReload} className="flex flex-wrap items-end gap-3 border-t border-[var(--border)] pt-4">
            <label className="flex flex-col gap-1 text-xs text-[var(--text-muted)]">
              X-API-Key（若已配置）
              <input
                className="input-dark min-w-[200px] font-mono text-xs"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="optional"
              />
            </label>
            <button type="submit" className="btn btn-primary" disabled={!enabled}>
              Reload
            </button>
          </form>

          {message ? <p className="text-sm text-[var(--success)]">{message}</p> : null}
          {error ? <p className="text-sm text-[var(--error)]">{error}</p> : null}
        </main>
      </div>
    </AppShell>
  );
}
