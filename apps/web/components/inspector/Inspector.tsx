"use client";

import { useEffect, useState } from "react";
import { ChartView } from "@/components/ChartView";
import { ChartItem, Dataset, Evidence } from "@/lib/api";
import { FlowNodeModel } from "@/lib/flowModel";
import { api } from "@/lib/api";
import { Tip } from "@/components/shell/Tip";

export type CollaborationInfo = {
  enabled: boolean;
  critic_enabled: boolean;
  agents_involved: string[];
  handoffs: Array<{
    id?: string;
    from_agent: string;
    to_agent: string;
    reason?: string;
    summary?: string | null;
  }>;
  blackboard: Record<string, unknown>;
  critic_result?: { pass?: boolean; issues?: string[]; suggestions?: string[] } | null;
};

type Tab = "context" | "node" | "agents" | "evidence" | "charts" | "report";

const TAB_TIPS: Record<Tab, string> = {
  context: "当前数据集画像与字段概览",
  node: "Canvas 中选中节点的详情",
  agents: "Multi-Agent：参与角色、交接、黑板与 Critic",
  evidence: "工具结果支撑的证据链（claim + 预览）",
  charts: "本轮分析生成的图表",
  report: "Markdown 分析报告（可导出 PDF）",
};

export function Inspector({
  dataset,
  boundDatasets = [],
  primaryDatasetId,
  selectedNode,
  nodeFocusKey = 0,
  evidences,
  evidence,
  onSelectEvidence,
  charts,
  report,
  runId,
  collaboration,
}: {
  dataset: Dataset | null;
  boundDatasets?: Dataset[];
  primaryDatasetId?: string;
  selectedNode: FlowNodeModel | null;
  /** Bumped on every Canvas node select so Node tab opens even when re-clicking the same id */
  nodeFocusKey?: number;
  evidences: Evidence[];
  evidence: Evidence | null;
  onSelectEvidence: (ev: Evidence) => void;
  charts: ChartItem[];
  report: string;
  runId: string | null;
  collaboration?: CollaborationInfo | null;
}) {
  const [tab, setTab] = useState<Tab>("context");

  useEffect(() => {
    if (nodeFocusKey > 0 && selectedNode) setTab("node");
  }, [nodeFocusKey, selectedNode]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "context", label: "Context" },
    { id: "node", label: "Node" },
    { id: "agents", label: "Agents" },
    { id: "evidence", label: "Evidence" },
    { id: "charts", label: "Charts" },
    { id: "report", label: "Report" },
  ];

  return (
    <aside className="flex h-full min-h-0 w-full flex-col bg-[var(--panel)]">
      <div className="flex shrink-0 gap-1 overflow-x-auto border-b border-[var(--border)] px-2 py-2">
        {tabs.map((t) => (
          <Tip key={t.id} tip={TAB_TIPS[t.id]}>
            <button
              type="button"
              className={`rounded px-2 py-1 text-[11px] transition-colors duration-150 ${
                tab === t.id
                  ? "bg-[var(--bg-2)] text-[var(--text)]"
                  : "text-[var(--text-muted)] hover:text-[var(--text)]"
              }`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          </Tip>
        ))}
      </div>

      <div className="scrollbar-thin min-h-0 flex-1 overflow-auto p-3">
        {tab === "context" ? (
          <div className="space-y-3">
            <div className="label-caps">Bound datasets</div>
            {boundDatasets.length ? (
              <ul className="space-y-1">
                {boundDatasets.map((d, i) => (
                  <li
                    key={d.id}
                    className="flex items-center justify-between gap-2 rounded border border-[var(--border)] bg-[var(--bg-1)] px-2 py-1.5 text-[11px]"
                  >
                    <span className="truncate text-[var(--text)]">
                      <span className="font-mono text-[var(--text-muted)]">{i === 0 || d.id === primaryDatasetId ? "data" : `data_${i + 1}`}</span>
                      {" · "}
                      {d.name}
                    </span>
                    {(d.id === primaryDatasetId || i === 0) && primaryDatasetId ? (
                      <span className="shrink-0 font-mono text-[10px] text-[var(--primary)]">主</span>
                    ) : (
                      <span className="shrink-0 font-mono text-[10px] text-[var(--text-muted)]">辅</span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-[var(--text-muted)]">未选择 Dataset</p>
            )}
            <div className="label-caps">Primary dataset</div>
            {dataset ? (
              <>
                <div className="text-sm font-medium">{dataset.name}</div>
                <div className="font-mono text-[11px] text-[var(--text-muted)]">
                  {dataset.source_type || "file"} · {dataset.row_count.toLocaleString()} rows · {dataset.col_count} cols
                  {dataset.table_name ? ` · table ${dataset.table_name}` : ""}
                </div>
                <pre className="whitespace-pre-wrap rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-2 text-[11px] leading-5 text-[var(--text-muted)]">
                  {dataset.profile_json?.summary_text || "No profile summary"}
                </pre>
                {dataset.fields?.length ? (
                  <ul className="space-y-1">
                    {dataset.fields.slice(0, 24).map((f) => (
                      <li key={f.id} className="flex justify-between gap-2 font-mono text-[10px] text-[var(--text-muted)]">
                        <span className="truncate text-[var(--text)]">{f.name}</span>
                        <span>{f.inferred_type}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </>
            ) : (
              <p className="text-xs text-[var(--text-muted)]">选择数据集以查看上下文</p>
            )}
          </div>
        ) : null}

        {tab === "node" ? (
          selectedNode ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-medium">{selectedNode.title}</div>
                <span className="font-mono text-[10px] text-[var(--text-muted)]">{selectedNode.id}</span>
              </div>
              <div className="font-mono text-[10px] uppercase text-[var(--text-muted)]">
                {selectedNode.type} · {selectedNode.kind} · {selectedNode.status}
                {selectedNode.stepStatus ? ` · step:${selectedNode.stepStatus}` : ""}
              </div>
              {selectedNode.inputSummary ? (
                <div>
                  <div className="label-caps mb-1">Input</div>
                  <pre className="whitespace-pre-wrap rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-2 text-[11px] leading-5 text-[var(--text-muted)]">
                    {selectedNode.inputSummary}
                  </pre>
                </div>
              ) : null}
              <div>
                <div className="label-caps mb-1">Output</div>
                <pre className="whitespace-pre-wrap rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-2 text-[11px] leading-5 text-[var(--text-muted)]">
                  {selectedNode.outputSummary || selectedNode.summary || "—"}
                </pre>
              </div>
              {selectedNode.summary &&
              selectedNode.outputSummary &&
              selectedNode.summary !== selectedNode.outputSummary ? (
                <div>
                  <div className="label-caps mb-1">Summary</div>
                  <pre className="whitespace-pre-wrap rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-2 text-[11px] leading-5 text-[var(--text-muted)]">
                    {selectedNode.summary}
                  </pre>
                </div>
              ) : null}
            </div>
          ) : (
            <p className="text-xs text-[var(--text-muted)]">在 Canvas 中选中节点查看详情</p>
          )
        ) : null}

        {tab === "agents" ? (
          <div className="space-y-4">
            <div className="font-mono text-[10px] text-[var(--text-muted)]">
              MA={String(collaboration?.enabled ?? "—")} · Critic={String(collaboration?.critic_enabled ?? "—")}
            </div>
            <div>
              <div className="label-caps mb-1">Roster</div>
              {collaboration?.agents_involved?.length ? (
                <ol className="list-decimal space-y-0.5 pl-4 text-[11px] text-[var(--text)]">
                  {collaboration.agents_involved.map((a) => (
                    <li key={a} className="font-mono">
                      {a}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-xs text-[var(--text-muted)]">Run 完成后显示参与角色</p>
              )}
            </div>
            <div>
              <div className="label-caps mb-1">Handoffs</div>
              {collaboration?.handoffs?.length ? (
                <ul className="space-y-2">
                  {collaboration.handoffs.map((h, i) => (
                    <li
                      key={h.id || `${h.from_agent}-${h.to_agent}-${i}`}
                      className="rounded border border-[var(--border)] bg-[var(--bg-1)] px-2 py-1.5 text-[11px]"
                    >
                      <div className="font-mono text-[var(--text)]">
                        {h.from_agent} → {h.to_agent}
                      </div>
                      {h.reason ? <div className="mt-0.5 text-[var(--text-muted)]">{h.reason}</div> : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-[var(--text-muted)]">暂无交接记录</p>
              )}
            </div>
            <div>
              <div className="label-caps mb-1">Blackboard</div>
              <pre className="max-h-48 overflow-auto whitespace-pre-wrap rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-2 font-mono text-[10px] text-[var(--text-muted)]">
                {JSON.stringify(collaboration?.blackboard || {}, null, 2)}
              </pre>
            </div>
            {collaboration?.critic_result ? (
              <div>
                <div className="label-caps mb-1">Critic</div>
                <pre className="whitespace-pre-wrap rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-2 font-mono text-[10px] text-[var(--text-muted)]">
                  {JSON.stringify(collaboration.critic_result, null, 2)}
                </pre>
              </div>
            ) : null}
          </div>
        ) : null}

        {tab === "evidence" ? (
          <div className="space-y-2">
            <ul className="space-y-1">
              {evidences.map((ev) => (
                <li key={ev.id}>
                  <button
                    type="button"
                    className={`w-full rounded px-2 py-1.5 text-left text-[11px] transition-colors duration-150 ${
                      evidence?.id === ev.id ? "bg-[var(--bg-2)]" : "hover:bg-[var(--bg-2)]"
                    }`}
                    onClick={() => onSelectEvidence(ev)}
                  >
                    {ev.claim}
                  </button>
                </li>
              ))}
            </ul>
            {evidence ? (
              <div className="rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-2 text-[11px]">
                <div className="font-medium text-[var(--text)]">{evidence.claim}</div>
                {evidence.payload_json?.code_or_query ? (
                  <pre className="mt-2 overflow-auto rounded bg-[var(--bg-0)] p-2 font-mono text-[10px] text-[var(--success)]">
                    {evidence.payload_json.code_or_query}
                  </pre>
                ) : null}
                <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-[var(--text-muted)]">
                  {JSON.stringify(evidence.payload_json?.result_preview, null, 2)}
                </pre>
              </div>
            ) : (
              <p className="text-xs text-[var(--text-muted)]">观察结果产生后可查看证据</p>
            )}
          </div>
        ) : null}

        {tab === "charts" ? (
          <div className="space-y-3">
            {charts.map((c) => (
              <ChartView key={c.id} title={c.title} option={c.option_json} />
            ))}
            {!charts.length ? <p className="text-xs text-[var(--text-muted)]">暂无图表</p> : null}
          </div>
        ) : null}

        {tab === "report" ? (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <div className="label-caps">Report</div>
              {runId && report ? (
                <a
                  className="text-[11px] text-[var(--primary)] underline"
                  href={api.reportPdfUrl(runId)}
                  target="_blank"
                  rel="noreferrer"
                >
                  PDF
                </a>
              ) : null}
            </div>
            {report ? (
              <pre className="whitespace-pre-wrap rounded-md border border-[var(--border)] bg-[var(--bg-1)] p-2 text-[11px] leading-5 text-[var(--text-muted)]">
                {report}
              </pre>
            ) : (
              <p className="text-xs text-[var(--text-muted)]">分析完成后生成 Markdown 报告</p>
            )}
          </div>
        ) : null}
      </div>
    </aside>
  );
}
