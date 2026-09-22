"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell, TopBar } from "@/components/shell/TopBar";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

type LlmProvider = "api" | "ollama";

type Settings = {
  llm_provider: LlmProvider;
  llm_base_url: string;
  llm_api_key: string;
  llm_api_key_set: boolean;
  llm_model: string;
  ollama_base_url: string;
  max_agent_steps: number;
  tool_timeout_sec: number;
  run_timeout_sec: number;
  llm_input_price_per_1k: number;
  llm_output_price_per_1k: number;
  large_file_mb: number;
  profile_sample_rows: number;
  sql_max_rows: number;
  app_api_key_required: boolean;
  multi_agent_enabled?: boolean;
  critic_enabled?: boolean;
};

type Metrics = {
  runs_total: number;
  runs_by_status: Record<string, number>;
  avg_latency_ms: number | null;
  avg_input_tokens: number | null;
  avg_output_tokens: number | null;
  tool_success_rate: number | null;
  python_success_rate: number | null;
  sql_success_rate: number | null;
};

type OllamaHealth = {
  ok: boolean;
  base_url: string;
  latency_ms?: number;
  models: string[];
  error?: string | null;
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [llmKey, setLlmKey] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState("checking");
  const [ollamaHealth, setOllamaHealth] = useState<OllamaHealth | null>(null);
  const [testingOllama, setTestingOllama] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<string[]>([]);
  /** Remember each provider's model so switching does not clobber the other. */
  const [apiModelDraft, setApiModelDraft] = useState("");
  const [ollamaModelDraft, setOllamaModelDraft] = useState("");

  const authHeaders = useCallback((): Record<string, string> => {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (apiKey.trim()) headers["X-API-Key"] = apiKey.trim();
    return headers;
  }, [apiKey]);

  const fetchOllamaModels = useCallback(
    async (opts?: { persistUrl?: boolean; baseUrl?: string; currentModel?: string }) => {
      setTestingOllama(true);
      setError(null);
      try {
        if (opts?.persistUrl && opts.baseUrl) {
          const saveRes = await fetch(`${API_BASE}/api/settings`, {
            method: "PUT",
            headers: authHeaders(),
            body: JSON.stringify({
              ollama_base_url: opts.baseUrl,
              ...(opts.currentModel ? { llm_model: opts.currentModel } : {}),
            }),
          });
          if (!saveRes.ok) {
            setError(await saveRes.text());
            return null;
          }
        }
        const h: OllamaHealth = await fetch(`${API_BASE}/api/llm/ollama/health`).then((r) => r.json());
        setOllamaHealth(h);
        const models = h.ok ? h.models || [] : [];
        setOllamaModels(models);
        return h;
      } catch (e) {
        setError(String(e));
        setOllamaHealth({ ok: false, base_url: opts?.baseUrl || "", models: [], error: String(e) });
        setOllamaModels([]);
        return null;
      } finally {
        setTestingOllama(false);
      }
    },
    [authHeaders],
  );

  async function load() {
    const [s, m, h] = await Promise.all([
      fetch(`${API_BASE}/api/settings`).then((r) => r.json()),
      fetch(`${API_BASE}/api/metrics`).then((r) => r.json()),
      fetch(`${API_BASE}/api/health`)
        .then((r) => (r.ok ? "ok" : "down"))
        .catch(() => "down"),
    ]);
    const provider: LlmProvider = s.llm_provider === "ollama" ? "ollama" : "api";
    const next: Settings = {
      ...s,
      llm_provider: provider,
      ollama_base_url: s.ollama_base_url || "http://localhost:11434",
    };
    setSettings(next);
    setMetrics(m);
    setHealth(h);
    if (provider === "api") {
      setApiModelDraft(s.llm_model || "");
    } else {
      setOllamaModelDraft(s.llm_model || "");
    }
    return next;
  }

  useEffect(() => {
    load()
      .then((s) => {
        if (s?.llm_provider === "ollama") {
          void fetchOllamaModels().then((h) => {
            if (!h?.ok || !h.models.length) return;
            setSettings((prev) => {
              if (!prev) return prev;
              const pick =
                prev.llm_model && h.models.includes(prev.llm_model) ? prev.llm_model : h.models[0];
              setOllamaModelDraft(pick);
              return { ...prev, llm_model: pick };
            });
          });
        }
      })
      .catch((e) => {
        setError(String(e));
        setHealth("down");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial load only
  }, []);

  function onProviderChange(next: LlmProvider) {
    if (!settings || next === settings.llm_provider) return;
    if (settings.llm_provider === "api") {
      setApiModelDraft(settings.llm_model);
    } else {
      setOllamaModelDraft(settings.llm_model);
    }
    const restored = next === "api" ? apiModelDraft || settings.llm_model : ollamaModelDraft || settings.llm_model;
    setSettings({ ...settings, llm_provider: next, llm_model: restored });
    if (next === "ollama") {
      void fetchOllamaModels().then((h) => {
        if (!h?.ok || !h.models.length) return;
        const pick = restored && h.models.includes(restored) ? restored : h.models[0];
        setOllamaModelDraft(pick);
        setSettings((prev) => (prev ? { ...prev, llm_model: pick } : prev));
      });
    }
  }

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (!settings) return;
    setMessage(null);
    setError(null);
    const body: Record<string, unknown> = {
      llm_provider: settings.llm_provider,
      llm_base_url: settings.llm_base_url,
      llm_model: settings.llm_model,
      ollama_base_url: settings.ollama_base_url,
      max_agent_steps: Number(settings.max_agent_steps),
      tool_timeout_sec: Number(settings.tool_timeout_sec),
      run_timeout_sec: Number(settings.run_timeout_sec),
      llm_input_price_per_1k: Number(settings.llm_input_price_per_1k),
      llm_output_price_per_1k: Number(settings.llm_output_price_per_1k),
      large_file_mb: Number(settings.large_file_mb),
      profile_sample_rows: Number(settings.profile_sample_rows),
      sql_max_rows: Number(settings.sql_max_rows),
    };
    if (llmKey.trim()) body.llm_api_key = llmKey.trim();

    const res = await fetch(`${API_BASE}/api/settings`, {
      method: "PUT",
      headers: authHeaders(),
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      setError(await res.text());
      return;
    }
    setMessage("已保存");
    setLlmKey("");
    if (settings.llm_provider === "api") setApiModelDraft(settings.llm_model);
    else setOllamaModelDraft(settings.llm_model);
    await load();
  }

  async function testOllama() {
    if (!settings) return;
    const h = await fetchOllamaModels({
      persistUrl: true,
      baseUrl: settings.ollama_base_url,
      currentModel: settings.llm_model,
    });
    if (!h) return;
    if (h.ok && h.models.length) {
      const pick =
        settings.llm_model && h.models.includes(settings.llm_model) ? settings.llm_model : h.models[0];
      setOllamaModelDraft(pick);
      setSettings({ ...settings, llm_model: pick });
    }
    await load();
  }

  if (!settings) {
    return (
      <AppShell topBar={<TopBar active="settings" health={health} />}>
        <div className="p-8 text-[var(--text-muted)]">加载 Settings… {error}</div>
      </AppShell>
    );
  }

  const isOllama = settings.llm_provider === "ollama";
  const selectModels =
    ollamaModels.length > 0
      ? ollamaModels
      : settings.llm_model
        ? [settings.llm_model]
        : [];

  return (
    <AppShell topBar={<TopBar active="settings" health={health} />}>
      <div className="scrollbar-thin h-full overflow-auto">
        <main className="mx-auto grid max-w-4xl gap-6 px-6 py-6 md:grid-cols-[1.2fr_0.8fr]">
          <form onSubmit={onSave} className="panel space-y-4 rounded-md p-5">
            <div>
              <h1 className="text-lg font-semibold">Settings</h1>
              <p className="text-xs text-[var(--text-muted)]">模型、限额与运维指标</p>
              <p className="mt-2 font-mono text-[11px] text-[var(--text-muted)]">
                MULTI_AGENT={String(settings.multi_agent_enabled ?? true)} · CRITIC={String(settings.critic_enabled ?? false)}{" "}
                <span className="text-[var(--text-muted)]">（.env 只读）</span>
              </p>
            </div>

            <label className="block text-sm">
              <span className="text-[var(--text-muted)]">LLM Provider</span>
              <select
                className="input-dark mt-1 w-full"
                value={settings.llm_provider}
                onChange={(e) => onProviderChange(e.target.value as LlmProvider)}
              >
                <option value="api">远程 API（OpenAI 兼容）</option>
                <option value="ollama">Ollama 本地</option>
              </select>
            </label>

            {isOllama ? (
              <>
                <label className="block text-sm">
                  <span className="text-[var(--text-muted)]">Ollama Base URL</span>
                  <input
                    className="input-dark mt-1 w-full"
                    value={settings.ollama_base_url}
                    onChange={(e) => setSettings({ ...settings, ollama_base_url: e.target.value })}
                    placeholder="http://localhost:11434"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-[var(--text-muted)]">LLM Model（本地可用）</span>
                  <select
                    className="input-dark mt-1 w-full font-mono"
                    value={selectModels.includes(settings.llm_model) ? settings.llm_model : selectModels[0] || ""}
                    disabled={selectModels.length === 0}
                    onChange={(e) => {
                      const v = e.target.value;
                      setOllamaModelDraft(v);
                      setSettings({ ...settings, llm_model: v });
                    }}
                  >
                    {selectModels.length === 0 ? (
                      <option value="">暂无可用模型 — 请先测试连接</option>
                    ) : (
                      selectModels.map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))
                    )}
                  </select>
                </label>
                <p className="text-xs text-[var(--text-muted)]">
                  本地模式无需云厂商 API Key。列表来自 Ollama；建议选用支持 tool calling 的模型。
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    type="button"
                    className="btn"
                    disabled={testingOllama}
                    onClick={() => void testOllama()}
                  >
                    {testingOllama ? "刷新中…" : "测试连接 / 刷新模型"}
                  </button>
                  {ollamaHealth ? (
                    <span
                      className={`text-sm ${ollamaHealth.ok ? "text-[var(--success)]" : "text-[var(--error)]"}`}
                    >
                      {ollamaHealth.ok
                        ? `可达 · ${ollamaHealth.latency_ms ?? "-"} ms · ${ollamaHealth.models.length} 个模型`
                        : `不可达 · ${ollamaHealth.error || "unknown"}`}
                    </span>
                  ) : null}
                </div>
              </>
            ) : (
              <>
                <label className="block text-sm">
                  <span className="text-[var(--text-muted)]">LLM Base URL</span>
                  <input
                    className="input-dark mt-1 w-full"
                    value={settings.llm_base_url}
                    onChange={(e) => setSettings({ ...settings, llm_base_url: e.target.value })}
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-[var(--text-muted)]">LLM Model（远程配置）</span>
                  <input
                    className="input-dark mt-1 w-full"
                    value={settings.llm_model}
                    onChange={(e) => {
                      setApiModelDraft(e.target.value);
                      setSettings({ ...settings, llm_model: e.target.value });
                    }}
                    placeholder="deepseek-chat"
                  />
                </label>
                <label className="block text-sm">
                  <span className="text-[var(--text-muted)]">
                    LLM API Key {settings.llm_api_key_set ? `(当前 ${settings.llm_api_key})` : "(未设置)"}
                  </span>
                  <input
                    className="input-dark mt-1 w-full"
                    type="password"
                    placeholder="留空则不修改"
                    value={llmKey}
                    onChange={(e) => setLlmKey(e.target.value)}
                  />
                </label>
              </>
            )}

            <div className="grid grid-cols-2 gap-3">
              {(
                [
                  ["max_agent_steps", "Max Steps"],
                  ["tool_timeout_sec", "Tool Timeout"],
                  ["run_timeout_sec", "Run Timeout"],
                  ["large_file_mb", "Large File MB"],
                  ["sql_max_rows", "SQL Max Rows"],
                  ["profile_sample_rows", "Profile Sample Rows"],
                  ["llm_input_price_per_1k", "Input $/1K"],
                  ["llm_output_price_per_1k", "Output $/1K"],
                ] as const
              ).map(([key, label]) => (
                <label key={key} className="block text-sm">
                  <span className="text-[var(--text-muted)]">{label}</span>
                  <input
                    className="input-dark mt-1 w-full"
                    type="number"
                    value={settings[key] as number}
                    onChange={(e) =>
                      setSettings({ ...settings, [key]: Number(e.target.value) } as Settings)
                    }
                  />
                </label>
              ))}
            </div>
            {settings.app_api_key_required ? (
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">X-API-Key（写操作需要）</span>
                <input
                  className="input-dark mt-1 w-full"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
              </label>
            ) : (
              <p className="text-xs text-[var(--warning)]">未配置 APP_API_KEY，写操作在开发模式下开放。</p>
            )}
            <button type="submit" className="btn btn-primary">
              保存
            </button>
            {message ? <p className="text-sm text-[var(--success)]">{message}</p> : null}
            {error ? <p className="text-sm text-[var(--error)]">{error}</p> : null}
          </form>

          <section className="panel space-y-3 rounded-md p-5">
            <h2 className="label-caps">Metrics</h2>
            {metrics ? (
              <div className="grid grid-cols-2 gap-3 text-sm">
                <MetricCard label="Runs" value={String(metrics.runs_total)} />
                <MetricCard
                  label="Avg Latency"
                  value={metrics.avg_latency_ms != null ? `${metrics.avg_latency_ms} ms` : "-"}
                />
                <MetricCard
                  label="Tool Success"
                  value={
                    metrics.tool_success_rate != null
                      ? `${(metrics.tool_success_rate * 100).toFixed(1)}%`
                      : "-"
                  }
                />
                <MetricCard
                  label="SQL Success"
                  value={
                    metrics.sql_success_rate != null
                      ? `${(metrics.sql_success_rate * 100).toFixed(1)}%`
                      : "-"
                  }
                />
                <MetricCard
                  label="Python Success"
                  value={
                    metrics.python_success_rate != null
                      ? `${(metrics.python_success_rate * 100).toFixed(1)}%`
                      : "-"
                  }
                />
                <MetricCard
                  label="Avg Tokens"
                  value={
                    metrics.avg_input_tokens != null
                      ? `${Math.round(metrics.avg_input_tokens)}/${Math.round(metrics.avg_output_tokens || 0)}`
                      : "-"
                  }
                />
              </div>
            ) : (
              <p className="text-sm text-[var(--text-muted)]">暂无指标</p>
            )}
            {metrics?.runs_by_status ? (
              <pre className="rounded bg-[var(--bg-1)] p-3 font-mono text-xs text-[var(--text-muted)]">
                {JSON.stringify(metrics.runs_by_status, null, 2)}
              </pre>
            ) : null}
          </section>
        </main>
      </div>
    </AppShell>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--bg-1)] px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)]">{label}</div>
      <div className="mt-1 font-medium text-[var(--text)]">{value}</div>
    </div>
  );
}
