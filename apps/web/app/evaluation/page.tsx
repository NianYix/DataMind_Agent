"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppShell, TopBar } from "@/components/shell/TopBar";
import { EvalCase, EvalRun, EvalSuite, api } from "@/lib/api";

function pct(v: number | null | undefined) {
  if (v == null || Number.isNaN(v)) return "-";
  return `${(v * 100).toFixed(1)}%`;
}

function num(v: number | null | undefined, digits = 1) {
  if (v == null || Number.isNaN(v)) return "-";
  return Number(v).toFixed(digits);
}

function asNum(v: unknown): number | null | undefined {
  if (v == null) return v as null | undefined;
  return typeof v === "number" ? v : Number(v);
}


export default function EvaluationPage() {
  const [suites, setSuites] = useState<EvalSuite[]>([]);
  const [suiteId, setSuiteId] = useState("sales_suite");
  const [mode, setMode] = useState<"mock" | "live">("mock");
  const [apiKey, setApiKey] = useState("");
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [current, setCurrent] = useState<EvalRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState("checking");

  const refresh = useCallback(async () => {
    const [s, r] = await Promise.all([api.evaluationSuites(), api.evaluations()]);
    setSuites(s);
    setRuns(r);
    if (s.length && !s.find((x) => x.id === suiteId)) {
      setSuiteId(s[0].id);
    }
  }, [suiteId]);

  useEffect(() => {
    api
      .health()
      .then(() => setHealth("ok"))
      .catch(() => setHealth("down"));
    refresh().catch((e) => setError(String(e)));
  }, [refresh]);

  async function onStart(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const run = await api.startEvaluation(suiteId, mode, apiKey.trim() || undefined);
      setCurrent(run);
      await refresh();
    } catch (err) {
      setError(String(err));
    } finally {
      setBusy(false);
    }
  }

  async function openRun(id: string) {
    setError(null);
    try {
      const run = await api.evaluation(id);
      setCurrent(run);
    } catch (err) {
      setError(String(err));
    }
  }

  const summary = current?.summary_json;

  return (
    <AppShell topBar={<TopBar active="evaluation" health={health} />}>
      <div className="scrollbar-thin h-full overflow-auto">
        <main className="mx-auto grid max-w-5xl gap-6 px-6 py-6 lg:grid-cols-[280px_1fr]">
          <aside className="space-y-4">
            <form onSubmit={onStart} className="panel space-y-3 rounded-md p-4">
              <div>
                <h1 className="text-lg font-semibold">Evaluation</h1>
                <p className="text-xs text-[var(--text-muted)]">Suite · mock / live · heuristic metrics</p>
              </div>
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">Suite</span>
                <select
                  className="input-dark mt-1 w-full"
                  value={suiteId}
                  onChange={(e) => setSuiteId(e.target.value)}
                >
                  {suites.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.case_count})
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">Mode</span>
                <select
                  className="input-dark mt-1 w-full"
                  value={mode}
                  onChange={(e) => setMode(e.target.value as "mock" | "live")}
                >
                  <option value="mock">mock（CI / 无 LLM）</option>
                  <option value="live">live（真实 Agent）</option>
                </select>
              </label>
              <label className="block text-sm">
                <span className="text-[var(--text-muted)]">X-API-Key</span>
                <input
                  className="input-dark mt-1 w-full"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="optional"
                />
              </label>
              <button type="submit" disabled={busy} className="btn btn-primary w-full">
                {busy ? "运行中…" : "启动评测"}
              </button>
              {error ? <p className="text-sm text-[var(--error)]">{error}</p> : null}
            </form>

            <section className="panel rounded-md p-4">
              <h2 className="label-caps">History</h2>
              <ul className="mt-2 max-h-72 space-y-1 overflow-auto text-sm">
                {runs.map((r) => (
                  <li key={r.id}>
                    <button
                      type="button"
                      className="w-full rounded px-2 py-1.5 text-left transition-colors duration-150 hover:bg-[var(--bg-2)]"
                      onClick={() => openRun(r.id)}
                    >
                      <div className="truncate font-mono text-xs text-[var(--text-muted)]">
                        {r.id.slice(0, 8)}
                      </div>
                      <div className="text-[var(--text)]">
                        {r.suite_id} · {r.mode} · {r.status}
                      </div>
                    </button>
                  </li>
                ))}
                {!runs.length ? <li className="text-[var(--text-muted)]">暂无记录</li> : null}
              </ul>
            </section>
          </aside>

          <section className="space-y-4">
            {!current ? (
              <div className="rounded-md border border-dashed border-[var(--border-strong)] bg-[var(--panel)] p-8 text-[var(--text-muted)]">
                选择历史或启动一次 mock 评测以查看汇总。
              </div>
            ) : (
              <>
                <div className="panel rounded-md p-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h2 className="text-xl font-semibold text-[var(--text)]">{current.suite_id}</h2>
                    <span className="font-mono text-xs text-[var(--text-muted)]">
                      {current.mode} · {current.status} · {current.id}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-[var(--warning)]">
                    Insight / Hallucination / Calculation 为启发式（heuristic），非 LLM-as-judge。
                  </p>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2 md:grid-cols-4">
                    <Card label="Task Success" value={pct(summary?.task_success_rate)} />
                    <Card label="Tool Success" value={pct(summary?.tool_success_rate)} />
                    <Card label="Python Success" value={pct(summary?.python_success_rate)} />
                    <Card label="SQL Success" value={pct(summary?.sql_success_rate)} />
                    <Card label="Avg Insight (h)" value={num(summary?.avg_insight_score, 3)} />
                    <Card label="Avg Calc (h)" value={num(summary?.avg_calculation_score, 3)} />
                    <Card label="Hallucination (h)" value={pct(summary?.avg_hallucination_rate)} />
                    <Card label="Avg Steps" value={num(summary?.avg_steps, 1)} />
                    <Card label="Avg Latency ms" value={num(summary?.avg_latency_ms, 0)} />
                    <Card label="Avg Tokens" value={num(summary?.avg_tokens, 0)} />
                    <Card
                      label="Passed"
                      value={summary ? `${summary.cases_passed ?? 0}/${summary.cases_total ?? 0}` : "-"}
                    />
                  </div>
                </div>

                <div className="panel overflow-auto rounded-md">
                  <table className="min-w-full text-left text-sm">
                    <thead className="border-b border-[var(--border)] bg-[var(--bg-1)] text-xs uppercase text-[var(--text-muted)]">
                      <tr>
                        <th className="px-3 py-2">Case</th>
                        <th className="px-3 py-2">Status</th>
                        <th className="px-3 py-2">Latency</th>
                        <th className="px-3 py-2">Insight</th>
                        <th className="px-3 py-2">Calc</th>
                        <th className="px-3 py-2">Halluc.</th>
                        <th className="px-3 py-2">Steps</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(current.cases || []).map((c: EvalCase) => (
                        <tr key={c.id} className="border-b border-[var(--border)]">
                          <td className="px-3 py-2 font-mono text-xs">{c.case_id}</td>
                          <td className="px-3 py-2">{c.status}</td>
                          <td className="px-3 py-2 font-mono">{c.latency_ms ?? "-"}</td>
                        <td className="px-3 py-2 font-mono">{num(asNum(c.scores_json?.insight_score), 3)}</td>
                        <td className="px-3 py-2 font-mono">{num(asNum(c.scores_json?.calculation_score), 3)}</td>
                        <td className="px-3 py-2 font-mono">{pct(asNum(c.scores_json?.hallucination_rate))}</td>
                          <td className="px-3 py-2 font-mono">{c.steps}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </section>
        </main>
      </div>
    </AppShell>
  );
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--border)] bg-[var(--bg-1)] px-3 py-2">
      <div className="text-[11px] uppercase tracking-wide text-[var(--text-muted)]">{label}</div>
      <div className="mt-1 font-medium text-[var(--text)]">{value}</div>
    </div>
  );
}
