"use client";

import { FormEvent, useState } from "react";
import { StatusDot } from "@/components/shell/StatusDot";
import { AgentRun, Conversation, Dataset, Message } from "@/lib/api";
import { RunUiStatus } from "@/lib/runStatus";

export function AgentPanel({
  runStatus,
  latestSummary,
  datasets,
  datasetId,
  onSelectDataset,
  onUpload,
  onUploadSqlite,
  sqliteTable,
  onSqliteTableChange,
  conversations,
  conversationId,
  onSelectConversation,
  runs,
  runId,
  onSelectRun,
  messages,
  input,
  onInputChange,
  onAsk,
  running,
  error,
}: {
  runStatus: RunUiStatus;
  latestSummary?: string;
  datasets: Dataset[];
  datasetId: string;
  onSelectDataset: (id: string) => void;
  onUpload: (file: File | null) => void;
  onUploadSqlite: (file: File | null) => void;
  sqliteTable: string;
  onSqliteTableChange: (v: string) => void;
  conversations: Conversation[];
  conversationId: string;
  onSelectConversation: (id: string) => void;
  runs: AgentRun[];
  runId: string | null;
  onSelectRun: (id: string) => void;
  messages: Message[];
  input: string;
  onInputChange: (v: string) => void;
  onAsk: (e: FormEvent) => void;
  running: boolean;
  error: string | null;
}) {
  const [showMessages, setShowMessages] = useState(false);

  return (
    <aside className="scrollbar-thin flex h-full min-h-0 flex-col gap-3 overflow-auto border-r border-[var(--border)] bg-[var(--panel)] p-3">
      <section className="panel-2 rounded-md p-3">
        <div className="label-caps mb-2">Agent</div>
        <StatusDot status={runStatus} label={runStatus} />
        <div className="mt-2 text-xs leading-5 text-[var(--text-muted)]">
          {latestSummary || "Waiting for planning / tool actions…"}
        </div>
      </section>

      <section>
        <div className="mb-2 flex items-center justify-between gap-2">
          <div className="label-caps">Datasets</div>
          <label className="btn btn-primary cursor-pointer px-2 py-1 text-[11px]">
            CSV/Excel
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => onUpload(e.target.files?.[0] || null)}
            />
          </label>
        </div>
        <div className="mb-2 rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-2">
          <div className="mb-1 text-[11px] text-[var(--text-muted)]">SQLite table</div>
          <input
            className="input-dark mb-2 w-full py-1 text-xs"
            value={sqliteTable}
            onChange={(e) => onSqliteTableChange(e.target.value)}
            placeholder="sales"
          />
          <label className="btn cursor-pointer px-2 py-1 text-[11px]">
            Upload .db
            <input
              type="file"
              accept=".db,.sqlite,.sqlite3"
              className="hidden"
              onChange={(e) => onUploadSqlite(e.target.files?.[0] || null)}
            />
          </label>
        </div>
        <ul className="space-y-1">
          {datasets.map((d) => (
            <li key={d.id}>
              <button
                type="button"
                className={`w-full rounded-md px-2 py-2 text-left text-sm transition-colors duration-150 ${
                  datasetId === d.id
                    ? "border border-[var(--primary)] bg-[var(--bg-2)]"
                    : "border border-transparent hover:bg-[var(--bg-2)]"
                }`}
                onClick={() => onSelectDataset(d.id)}
              >
                <div className="font-medium">{d.name}</div>
                <div className="font-mono text-[10px] text-[var(--text-muted)]">
                  {d.source_type || "file"} · {d.row_count.toLocaleString()}×{d.col_count}
                </div>
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <div className="label-caps mb-2">Conversations</div>
        <ul className="space-y-1">
          {conversations.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className={`w-full rounded-md px-2 py-1.5 text-left text-xs transition-colors duration-150 ${
                  conversationId === c.id ? "bg-[var(--bg-2)] text-[var(--text)]" : "text-[var(--text-muted)] hover:bg-[var(--bg-2)]"
                }`}
                onClick={() => onSelectConversation(c.id)}
              >
                {c.title}
              </button>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <div className="label-caps mb-2">Runs</div>
        <ul className="space-y-1">
          {runs.slice(0, 12).map((r) => (
            <li key={r.id}>
              <button
                type="button"
                className={`w-full rounded-md px-2 py-1.5 text-left text-[11px] transition-colors duration-150 ${
                  runId === r.id ? "border border-[var(--primary)] bg-[var(--bg-2)]" : "hover:bg-[var(--bg-2)]"
                }`}
                onClick={() => onSelectRun(r.id)}
              >
                <div className="line-clamp-2 text-[var(--text)]">{r.question}</div>
                <div className="mt-0.5 font-mono text-[10px] text-[var(--text-muted)]">
                  {r.status} · {(r.input_tokens || 0) + (r.output_tokens || 0)} tok
                </div>
              </button>
            </li>
          ))}
          {!runs.length ? <li className="text-xs text-[var(--text-muted)]">暂无历史</li> : null}
        </ul>
      </section>

      <section className="mt-auto border-t border-[var(--border)] pt-3">
        <button
          type="button"
          className="btn btn-ghost mb-2 w-full text-left text-[11px] text-[var(--text-muted)]"
          onClick={() => setShowMessages((v) => !v)}
        >
          {showMessages ? "Hide messages" : "Show messages"} ({messages.length})
        </button>
        {showMessages ? (
          <div className="scrollbar-thin mb-2 max-h-36 space-y-1.5 overflow-auto">
            {messages.map((m) => (
              <div
                key={m.id}
                className="rounded px-2 py-1.5 text-[11px] leading-4"
                style={{
                  background:
                    m.role === "user"
                      ? "color-mix(in srgb, var(--primary) 18%, transparent)"
                      : "var(--bg-2)",
                  color: m.role === "user" ? "var(--text)" : "var(--text-muted)",
                }}
              >
                {m.content}
              </div>
            ))}
          </div>
        ) : null}

        {error ? (
          <div className="mb-2 rounded border border-[color-mix(in_srgb,var(--error)_40%,var(--border))] bg-[color-mix(in_srgb,var(--error)_12%,transparent)] px-2 py-1.5 text-[11px] text-[#ffb4ba]">
            {error}
          </div>
        ) : null}

        <form onSubmit={onAsk} className="space-y-2">
          <textarea
            className="input-dark min-h-[72px] w-full resize-y"
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            placeholder="例如：为什么 8 月销售下降？"
            disabled={running}
          />
          <button type="submit" className="btn btn-primary w-full" disabled={running || !datasetId}>
            {running ? "Running…" : "Ask Agent"}
          </button>
        </form>
      </section>
    </aside>
  );
}
