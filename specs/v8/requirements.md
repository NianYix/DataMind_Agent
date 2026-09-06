# DataMind Agent — V8 Requirements

> 基线：V1–V7 + UI Optimize（已实现）  
> 本阶段：**V8 — Multi-Agent 协作增强**  
> 语法：EARS  
> 状态：**已确认**（D1–D6 按建议锁定）

---

## 0. 阶段定位

| 已完成 | 本阶段 | 明确另开 |
|--------|--------|----------|
| LangGraph Supervisor + 节点流水线 | **一等公民 Agent 角色 / 交接 / 黑板** | AI Workflow 可视化编排器 |
| MCP / RAG / 企业切片 | **可选 Critic 复核**；角色级 Prompt | SSO / 行级权限 |
| Logic Canvas（Trace 只读） | **按 Agent 角色着色的时间线 / 交接边** | 任意 Swarm / 开放式 Agent 市场 |

`PROJECT_DESIGN` 已定义 Supervisor + Specialized Agents；当前实现偏「节点流水线」。本切片目标：在**不推翻现有 LangGraph**的前提下，把多角色协作做成可观测、可配置、可回归的能力。

---

## 1. 阶段目标

1. **Agent Roster**：固定角色集合（Planner / Supervisor / Tool / Analyst / Insight / Report / Critic），每次 Run 记录参与角色。  
2. **Handoff 记录**：角色切换写入结构化 `handoffs`（from → to、reason、summary），进入 Trace / API / Canvas。  
3. **Blackboard**：Run 级共享草稿板（key-value / 短文本），供角色读写；Inspector 可见。  
4. **Critic（可开关）**：Insight 之后、Report 之前可选复核；不通过则回 Supervisor 或标注风险。  
5. **角色 Prompt**：关键角色可从 Prompts 表解析（与 V5 Prompt 机制对齐）；缺省回落内置。  
6. **可回归**：默认行为兼容 V7；Critic 默认关；pytest 覆盖 handoff / blackboard / critic mock。

**非目标**：拖拽 Workflow 编辑器、人工审批闸门（HITL）完整产品、无限并行 Agent Swarm、跨 Run 长期记忆多智能体。

---

## 2. 范围

### 2.1 In Scope

| 模块 | 内容 |
|------|------|
| Config | `MULTI_AGENT_ENABLED`（默认 `true` 增强开）、`CRITIC_ENABLED`（默认 `false`） |
| State | `handoffs[]`、`blackboard{}`、`agents_involved[]` |
| Graph | Critic 节点；节点进出写 handoff；blackboard 读写约定 |
| Prompts | 解析 `system_planner` / `system_insight` / `system_critic` 等（有则用） |
| API | Run 详情含 handoffs / blackboard / agents_involved |
| UI | Canvas/Inspector：角色时间线与交接；黑板只读面板 |
| Tests | mock LLM 或确定性路径验证 handoff 与 critic 开关 |

### 2.2 Out of Scope

| 项 | 去向 |
|----|------|
| AI Workflow DAG 编辑器 | V9+ |
| HITL 审批 / 人工改写节点 | 更后 |
| 多租户 Agent 市场 | 更后 |
| 改变默认 `AGENT_ENGINE=langchain` | 否 |

---

## 3. 功能需求

### 3.1 Roster 与状态

**REQ-V8-ST-001**  
THE SYSTEM SHALL 为每次 Agent Run 维护 `agents_involved: string[]`（去重、按首次出现排序）。

**REQ-V8-ST-002**  
WHEN 控制流从一个角色节点进入另一角色节点，THE SYSTEM SHALL append 一条 handoff：  
`{ id, from_agent, to_agent, reason, summary?, at }`。

**REQ-V8-ST-003**  
THE SYSTEM SHALL 维护 Run 级 `blackboard: object`（JSON 可序列化）；Analyst/Insight/Critic 可写入约定键（如 `risks`、`open_questions`、`key_metrics`）。

**REQ-V8-ST-004**  
IF `MULTI_AGENT_ENABLED=false`，THEN THE SYSTEM SHALL 保持与 V7 等价的主路径（可不写 handoffs/blackboard，或写空结构），不得破坏现有 API 契约。

---

### 3.2 Critic Agent

**REQ-V8-CR-001**  
WHEN `CRITIC_ENABLED=true`，THE SYSTEM SHALL 在 Insight 完成后进入 Critic：输出 `{ pass: bool, issues: string[], suggestions: string[] }`。

**REQ-V8-CR-002**  
IF Critic `pass=false`，THEN THE SYSTEM SHALL 将 issues 写入 blackboard，并在 Report/最终答案中标注风险摘要（或回 Supervisor 最多 1 次再进入 Insight——实现选一，默认：**标注风险并继续 Report**，避免死循环）。

**REQ-V8-CR-003**  
IF `CRITIC_ENABLED=false`，THEN THE SYSTEM SHALL 跳过 Critic 节点（Insight → Report）。

---

### 3.3 Prompt 解析

**REQ-V8-PR-001**  
THE SYSTEM SHALL 对至少 `system_planner`、`system_insight`、`system_critic` 尝试从 Prompt 存储解析激活版本；缺失则使用内置常量。

**REQ-V8-PR-002**  
THE SYSTEM SHALL 在 README / Prompts 页说明可覆盖的角色 Prompt 名称。

---

### 3.4 API / UI

**REQ-V8-API-001**  
THE SYSTEM SHALL 在 Run 详情（或等价 analysis 结果）中返回 `handoffs`、`blackboard`、`agents_involved`。

**REQ-V8-UI-001**  
Logic Canvas 或 Inspector SHALL 展示角色时间线 / 交接边（只读）；黑板以只读 JSON/键值展示。

**REQ-V8-UI-002**  
Settings 或 Execution 区域 SHALL 只读展示 `CRITIC_ENABLED` / `MULTI_AGENT_ENABLED`（改 `.env`；热更新非必须）。

---

## 4. 非功能

**REQ-V8-NFR-001**  
默认 `CRITIC_ENABLED=false`，保证 Demo 延迟与 V7 接近。

**REQ-V8-NFR-002**  
`pytest` 必须在无真实 LLM 或 mock 下验证：handoff 结构、blackboard 读写、critic 开关分支。

**REQ-V8-NFR-003**  
不得引入新的默认破坏性 API 删除；新增字段向后兼容。

---

## 5. 验收标准

1. 一次完整分析 Run 的 API/Trace 可见 ≥2 条 handoff 与 `agents_involved`。  
2. `CRITIC_ENABLED=true` 时 Run 含 Critic 步骤；`false` 时无 Critic。  
3. Inspector/Canvas 能看到角色交接或时间线。  
4. `MULTI_AGENT_ENABLED=false` 时主路径仍可完成分析。  
5. 全量 `pytest` 绿；前端类型检查通过。

---

## 6. 待确认决策

| # | 决策项 | 建议默认 |
|---|--------|----------|
| D1 | 下一阶段是否做 **Multi-Agent 增强（本文件）**？ | **是** |
| D2 | Critic 不通过策略 | **标注风险并继续 Report**（不循环） |
| D3 | `MULTI_AGENT_ENABLED` 默认 | **`true`**（写 handoff/blackboard；Critic 仍默认关） |
| D4 | 并行 fan-out 多 Specialist | **否（本切片）**；留给 Workflow |
| D5 | HITL 人工审批 | **否** |
| D6 | 是否同期做 Workflow 编辑器？ | **否**（V9） |

---

## 7. 确认方式

请回复：

- **`确认需求`** — 按 D1–D6 建议默认锁定，进入 `design.md` / `tasks.md`  
- **`确认需求：…`** — 修改决策（例如先做 Workflow、或 Critic 默认开）  

**未确认前不编写 design 以外的业务代码；未回复「开始执行」前不改实现。**
