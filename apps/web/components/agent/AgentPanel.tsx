"use client";

import { FormEvent, useState } from "react";
import { StatusDot } from "@/components/shell/StatusDot";
import { Tip } from "@/components/shell/Tip";
import { AgentRun, Conversation, Dataset, Message } from "@/lib/api";
import { RunUiStatus } from "@/lib/runStatus";

export function AgentPanel({
  runStatus,
  latestSummary,
  datasets,
  datasetIds,
  primaryDatasetId,
  onToggleDataset,
  onSetPrimaryDataset,
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
  datasetIds: string[];
  primaryDatasetId: string;
  onToggleDataset: (id: string) => void;
  onSetPrimaryDataset: (id: string) => void;
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
  const selected = new Set(datasetIds);

  return (
    <aside className="scrollbar-thin flex h-full min-h-0 flex-col gap-3 overflow-auto border-r border-[var(--border)] bg-[var(--panel)] p-3">
      <section className="panel-2 rounded-md p-3">
        <Tip tip="当前 Agent 运行状态与最近一步摘要">
          <div className="label-caps mb-2 cursor-default">Agent</div>
        </Tip>
        <StatusDot status={runStatus} label={runStatus} />
        <div className="mt-2 text-xs leading-5 text-[var(--text-muted)]">
          {latestSummary || "Waiting for planning / tool actions…"}
        </div>
      </section>

      <section>
        <div className="mb-2 flex items-center justify-between gap-2">
          <Tip tip="可多选 Dataset 同次分析；主表用于默认 df/data">
            <div className="label-caps cursor-default">Datasets</div>
          </Tip>
          <Tip tip="上传 CSV / Excel，自动建 Dataset 并画像">
            <label className="btn btn-primary cursor-pointer px-2 py-1 text-[11px]">
              CSV/Excel
              <input
                type="file"
                accept=".csv,.xlsx,.xls"
                className="hidden"
                onChange={(e) => onUpload(e.target.files?.[0] || null)}
              />
            </label>
          </Tip>
        </div>
        <div className="mb-2 rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-2">
          <Tip tip="上传 SQLite 前填写要分析的表名（如 sales）">
            <div className="mb-1 cursor-default text-[11px] text-[var(--text-muted)]">SQLite table</div>
          </Tip>
          <input
            className="input-dark mb-2 w-full py-1 text-xs"
            value={sqliteTable}
            onChange={(e) => onSqliteTableChange(e.target.value)}
            placeholder="sales"
          />
          <Tip tip="上传 .db / .sqlite，按上方表名注册为 Dataset">
            <label className="btn cursor-pointer px-2 py-1 text-[11px]">
              Upload .db
              <input
                type="file"
                accept=".db,.sqlite,.sqlite3"
                className="hidden"
                onChange={(e) => onUploadSqlite(e.target.files?.[0] || null)}
              />
            </label>
          </Tip>
        </div>
        <ul className="space-y-1">
          {datasets.map((d) => {
            const isOn = selected.has(d.id);
            const isPrimary = primaryDatasetId === d.id;
            return (
              <li key={d.id}>
                <div
                  className={`flex w-full items-start gap-2 rounded-md border px-2 py-2 text-left text-sm transition-colors duration-150 ${
                    isOn
                      ? "border-[var(--primary)] bg-[var(--bg-2)]"
                      : "border-transparent hover:bg-[var(--bg-2)]"
                  }`}
                >
                  <button
                    type="button"
                    className="mt-0.5 font-mono text-[11px] text-[var(--text-muted)]"
                    onClick={() => onToggleDataset(d.id)}
                    aria-pressed={isOn}
                    title={isOn ? "取消选中" : "选中参与分析"}
                  >
                    {isOn ? "[x]" : "[ ]"}
                  </button>
                  <button type="button" className="min-w-0 flex-1 text-left" onClick={() => onToggleDataset(d.id)}>
                    <div className="flex items-center gap-1.5">
                      <span className="truncate font-medium">{d.name}</span>
                      {isPrimary ? (
                        <span className="shrink-0 rounded bg-[var(--primary)]/20 px-1 font-mono text-[10px] text-[var(--primary)]">
                          主
                        </span>
                      ) : null}
                    </div>
                    <div className="font-mono text-[10px] text-[var(--text-muted)]">
                      {d.source_type || "file"} · {d.row_count.toLocaleString()}×{d.col_count}
                    </div>
                  </button>
                  {isOn && !isPrimary ? (
                    <button
                      type="button"
                      className="shrink-0 font-mono text-[10px] text-[var(--text-muted)] hover:text-[var(--primary)]"
                      onClick={() => onSetPrimaryDataset(d.id)}
                      title="设为主表"
                    >
                      设为主
                    </button>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      </section>

      <section>
        <Tip tip="同一数据集下的对话线程；切换可回看历史消息">
          <div className="label-caps mb-2 cursor-default">Conversations</div>
        </Tip>
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
        <Tip tip="历史 Agent Run；点击可加载 Trace / 报告 / Evidence">
          <div className="label-caps mb-2 cursor-default">Runs</div>
        </Tip>
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
        <Tip tip="展开/折叠本会话的用户与助手消息">
          <button
            type="button"
            className="btn btn-ghost mb-2 w-full text-left text-[11px] text-[var(--text-muted)]"
            onClick={() => setShowMessages((v) => !v)}
          >
            {showMessages ? "Hide messages" : "Show messages"} ({messages.length})
          </button>
        </Tip>
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
          <Tip tip="用自然语言描述分析问题；需先选中 Dataset">
            <textarea
              className="input-dark min-h-[72px] w-full resize-y"
              value={input}
              onChange={(e) => onInputChange(e.target.value)}
              placeholder="例如：为什么 8 月销售下降？"
              disabled={running}
            />
          </Tip>
          <Tip tip="提交问题并启动 Agent（等同 TopBar Run）">
            <button type="submit" className="btn btn-primary w-full" disabled={running || !primaryDatasetId}>
              {running ? "Running…" : "Ask Agent"}
            </button>
          </Tip>
        </form>
      </section>
    </aside>
  );
}
