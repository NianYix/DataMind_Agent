# DataMind Agent — V9 Requirements

> 基线：V1–V8 + UI Optimize（已实现）  
> 本阶段：**V9 — AI Workflow（可编排分析工作流）**  
> 语法：EARS  
> 状态：**已确认**（D1–D6 按建议锁定）

---

## 0. 阶段定位

| 已完成 | 本阶段 | 明确另开 |
|--------|--------|----------|
| 单次对话 Agent Run（LangGraph） | **可保存/可复用的 Workflow 定义与执行** | 完整拖拽式 n8n 级编辑器 |
| Multi-Agent handoff / Critic | **节点图：顺序 + 条件分支** | HITL 人工审批产品化 |
| MCP / RAG / 企业切片 | **工作流 Run 轨迹与 UI** | SSO / 行级权限 / Agent 市场 |

`PROJECT_DESIGN` 扩展项在 Multi-Agent 之后为 **AI Workflow**。本切片目标：让用户把「绑定数据 → 提问分析 →（可选）分支/导出」固化为可重复执行的流程，而不是每次从零对话。

---

## 1. 阶段目标

1. **Workflow 定义**：Workspace 级 JSON DAG（nodes + edges），可 CRUD、可启用。  
2. **节点类型（首批）**：至少 `start`、`analyze`（调用现有 Agent）、`condition`（简单表达式/字段判断）、`end`；可选 P1：`export`。  
3. **执行引擎**：按拓扑/边执行；写出 `WorkflowRun` + 逐步状态；失败可标记并不拖垮进程。  
4. **模板**：内置 ≥1 个样例（如「标准销售归因分析」：绑定默认问题 + analyze → end）。  
5. **API / UI**：`/workflows` 列表、详情/JSON 编辑、触发 Run、查看 Run 步骤。  
6. **可回归**：无 LLM 时可用 mock analyze 节点跑通 CI。

**非目标**：像素级拖拽编排器、子工作流嵌套、定时调度/Cron、多租户工作流市场、完整 HITL 闸门。

---

## 2. 范围

### 2.1 In Scope

| 模块 | 内容 |
|------|------|
| Config | 无强制新开关；可选 `WORKFLOW_MOCK_ANALYZE`（测试用） |
| ORM | `workflows`、`workflow_runs`、`workflow_run_steps` |
| Engine | 加载定义 → 执行节点 → 持久化步骤 |
| Nodes | `start` / `analyze` / `condition` / `end`（+ P1 `export`） |
| API | CRUD workflow、start run、get run/steps、list templates |
| UI | `/workflows`：列表、编辑定义、运行、Run 详情 |
| Seed | 1 个内置模板 JSON |

### 2.2 Out of Scope

| 项 | 去向 |
|----|------|
| 完整拖拽画布编辑器 | V10+ 或 P2 |
| Cron / Webhook 触发 | 更后 |
| HITL 审批节点产品化 | 更后 |
| 并行 fan-out 多分支同时跑 | P1 最多「条件二选一」 |

---

## 3. 功能需求

### 3.1 定义模型

**REQ-V9-DEF-001**  
THE SYSTEM SHALL 以 JSON 存储 Workflow：`{ id, name, description, workspace_id, version, enabled, graph: { nodes[], edges[] } }`。

**REQ-V9-DEF-002**  
WHEN 创建/更新 Workflow，THE SYSTEM SHALL 校验：恰好一个 `start`、至少一个 `end`、边引用的 node id 均存在、无自环到非法类型（基础校验即可）。

**REQ-V9-DEF-003**  
THE SYSTEM SHALL 支持节点类型至少：
- `start`：入口，可带默认 `question` / `dataset_id` 覆盖项  
- `analyze`：调用现有分析 Agent（同步等待完成或超时），输入 question/dataset  
- `condition`：基于 `context` 字段做简单判断（如 `context.final_answer contains "下降"` 或布尔表达式子集）  
- `end`：终止并汇总输出  

**REQ-V9-DEF-004**  
THE SYSTEM SHALL 提供 ≥1 个内置模板（只读种子或可复制为用户 Workflow）。

---

### 3.2 执行

**REQ-V9-RUN-001**  
WHEN 用户触发 Run，THE SYSTEM SHALL 创建 `WorkflowRun`（status=running|done|error|cancelled），并逐步写入 `WorkflowRunStep`（node_id、status、input/output 摘要、error）。

**REQ-V9-RUN-002**  
WHEN 执行 `analyze` 节点，THE SYSTEM SHALL 复用现有 Agent 能力（langchain 路径）；产出至少写入 context：`final_answer`、`agent_run_id`（若有）。

**REQ-V9-RUN-003**  
WHEN 执行 `condition` 节点，THE SYSTEM SHALL 按 true/false 选择出边（边可带 `label: "true"|"false"` 或 `when`）。

**REQ-V9-RUN-004**  
IF 某节点失败，THEN THE SYSTEM SHALL 将该 Run 标为 `error`，记录失败步骤，停止后续节点（除非未来扩展 retry——本切片不做）。

**REQ-V9-RUN-005**  
IF `WORKFLOW_MOCK_ANALYZE=true`（或测试夹具），THEN `analyze` SHALL 不调用真实 LLM，返回固定 mock 答案以便 CI。

---

### 3.3 API / UI

**REQ-V9-API-001**  
THE SYSTEM SHALL 提供 API：列出/创建/更新/删除 Workflow；列出模板；启动 Run；查询 Run 与 steps。

**REQ-V9-UI-001**  
THE SYSTEM SHALL 提供前端页 `/workflows`：列表、新建（可从模板）、JSON/表单编辑 graph、触发运行、查看最近 Run 与步骤。

**REQ-V9-UI-002**  
TopBar SHALL 增加 Workflows 导航入口。

**REQ-V9-UI-003**  
本切片不要求完整拖拽编辑器；允许 JSON 编辑 + 只读节点列表可视化。

---

## 4. 非功能

**REQ-V9-NFR-001**  
默认对话分析路径（`/` Workspace）行为不变；Workflow 为并行能力。

**REQ-V9-NFR-002**  
`pytest` 必须在 mock analyze 下跑通：创建模板 workflow → run → steps 含 start/analyze/end。

**REQ-V9-NFR-003**  
单 Run 节点数建议上限（如 30），防止滥用；超时沿用 `RUN_TIMEOUT_SEC` 或独立 `WORKFLOW_TIMEOUT_SEC`（默认 600）。

---

## 5. 验收标准

1. 可从模板创建 Workflow 并成功 Run（mock 路径）。  
2. Run 详情可见逐步状态与 `agent_run_id`（真实/ mock）。  
3. condition 节点能按 true/false 走不同 end（单测覆盖）。  
4. `/workflows` 可操作；TopBar 有入口。  
5. 全量 `pytest` 绿；前端 `tsc` 通过；Workspace 对话分析仍可用。

---

## 6. 待确认决策

| # | 决策项 | 建议默认 |
|---|--------|----------|
| D1 | 下一阶段是否做 **AI Workflow（本文件）**？ | **是** |
| D2 | 编辑体验 | **JSON + 节点列表**（不做完整拖拽） |
| D3 | `analyze` 实现 | **复用现有 Agent Runtime**（可 mock） |
| D4 | 条件语法 | **极简**：`field path` + `contains` / `eq` / `truthy` |
| D5 | 并行多分支 | **否**（仅 if/else 单路径） |
| D6 | 是否同期 HITL / Cron？ | **否** |

---

## 7. 确认方式

请回复：

- **`确认需求`** — 按 D1–D6 建议默认锁定，进入 `design.md` / `tasks.md`  
- **`确认需求：…`** — 修改决策（例如先做拖拽画布、或 Cron）  

**未确认前不编写 design 以外的业务代码；未回复「开始执行」前不改实现。**
