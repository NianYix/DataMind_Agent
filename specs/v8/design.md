# DataMind Agent — V8 Architecture Design

> 对应：`specs/v8/requirements.md`（**已确认**，D1–D6 按建议锁定）  
> 基线：V7 MCP + LangGraph Supervisor  
> 状态：**已确认并已实现**  
> 基线：V7 MCP + LangGraph Supervisor  
> 非目标：Workflow DAG 编辑器 / HITL / 并行 fan-out Swarm

---

## 1. 目标

```text
understand → plan → supervisor ⇄ tools → observe
                         │
                         ↓
                      insight
                         │
              ┌──────────┴──────────┐
              │ CRITIC_ENABLED?     │
              ↓                     ↓
           critic                (skip)
              │                     │
              └──────────┬──────────┘
                         ↓
                      report → END

Alongside every role transition:
  handoffs[] + agents_involved[] + blackboard{}
        │
        ▼
  AgentRun.state_json + GET /agent-runs/{id}/collaboration
        │
        ▼
  Canvas agent labels + Inspector「Agents」tab
```

---

## 2. 已锁定决策

| # | 取值 |
|---|------|
| D1 | 做 Multi-Agent 增强 |
| D2 | Critic 不通过 → **标注风险并继续 Report**（不循环） |
| D3 | `MULTI_AGENT_ENABLED` 默认 **`true`** |
| D4 | 不做并行 fan-out |
| D5 | 不做 HITL |
| D6 | Workflow 编辑器 → V9 |

---

## 3. 配置

`server/core/config.py` + `.env.example`：

| 键 | 默认 | 说明 |
|----|------|------|
| `MULTI_AGENT_ENABLED` | `true` | 写 handoff / blackboard / agents_involved |
| `CRITIC_ENABLED` | `false` | Insight 后插入 Critic 节点 |

Settings 热更新非必须；Settings UI 只读展示（可挂 ops `/api/settings` 只读字段，P1）。

---

## 4. 状态模型

### 4.1 `GraphState` 增量

```python
handoffs: list[dict]          # {id, from_agent, to_agent, reason, summary?, at}
blackboard: dict[str, Any]    # risks, open_questions, key_metrics, critic_issues, ...
agents_involved: list[str]    # 去重、首次出现序
critic_result: dict | None    # {pass, issues, suggestions}
```

### 4.2 持久化

写入现有 `AgentRun.state_json`（`agent/lc/runtime.py` 结束时扩展），不新增表：

```json
{
  "multi_agent": {
    "enabled": true,
    "critic_enabled": false,
    "agents_involved": ["Understand", "Planner", "Supervisor", "Tools", "Analyst", "Insight", "Report"],
    "handoffs": [...],
    "blackboard": {...},
    "critic_result": null
  }
}
```

`MULTI_AGENT_ENABLED=false`：可不写或写空结构；主路径节点不变（无 Critic）。

### 4.3 Roster 命名（稳定）

| Graph 节点 | agent 名（handoff / steps） |
|------------|------------------------------|
| understand | `Understand` |
| plan | `Planner` |
| supervisor | `Supervisor` |
| tools | `Tools`（或具体 tool 名作 summary） |
| observe | `Analyst` |
| insight | `Insight` |
| critic | `Critic` |
| report | `Report` |

---

## 5. 模块划分

```text
agent/lc/collaboration.py   # record_handoff, touch_agent, merge_blackboard, snapshot
agent/lc/state.py           # 字段扩展
agent/lc/nodes.py           # 各节点调用 collaboration；新增 critic_node
agent/lc/graph.py           # insight → (critic?) → report
agent/prompts/__init__.py   # CRITIC_SYSTEM；with_mcp 无关
server/services/prompt_service.py  # resolve_role_system(name, fallback)
server/api/analysis.py      # GET .../collaboration
server/schemas              # CollaborationOut（或裸 dict）
apps/web/lib/flowModel.ts   # critic 着色；可选 handoff 边标注
apps/web/components/inspector/Inspector.tsx  # Agents tab
apps/web/lib/api.ts
tests/test_multi_agent.py
```

### 5.1 `collaboration` 辅助

```python
def touch_agent(state, name: str) -> dict
def record_handoff(state, *, from_agent, to_agent, reason, summary=None) -> dict
def patch_blackboard(state, updates: dict) -> dict
def collaboration_snapshot(state, settings) -> dict
```

各 node **入口** `touch_agent`；**路由切换前/后** `record_handoff`（例如 plan→supervisor、supervisor→tools、insight→critic/report）。

### 5.2 Critic 节点

- 输入：question、observations 摘要、insights、blackboard。  
- 输出结构化：`{ "pass": bool, "issues": [], "suggestions": [] }`。  
- `pass=false`：`blackboard["critic_issues"]=issues`，`blackboard["risks"]` 合并；Report/Insight 最终答案前缀或附录风险摘要（Report prompt 注入 blackboard.risks）。  
- **不**回 Supervisor（D2）。

路由：

```text
insight → route_after_insight → critic | report
critic → report
```

### 5.3 Prompt 解析

扩展 `prompt_service`：

| Prompt name | 用途 | fallback |
|-------------|------|----------|
| `system_analyst`（已有） | Planner | `PLANNER_SYSTEM` |
| `system_insight` | Insight | `INSIGHT_SYSTEM` |
| `system_critic` | Critic | `CRITIC_SYSTEM` |

`resolve_role_system(db, name, fallback)`；Planner 继续用现有 `resolve_planner_system`（可内部委托）。

---

## 6. API

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/agent-runs/{run_id}/collaboration` | 返回 `multi_agent` 快照；无则空默认 |

可选：`AgentRunOut` 增加可选字段 `agents_involved`（从 state_json 投影）——非必须，有专用 endpoint 即可。

SSE：可选发 `collaboration` 事件（P1）；本切片以 Run 结束后拉取为主，Trace 中已有 Critic/AgentStep。

---

## 7. 前端

- **Inspector** 新 Tab `Agents`：agents_involved 列表、handoffs 时间线、blackboard 只读 JSON。  
- **flowModel**：`critic` → kind `ai`；title 映射友好；handoff 不强制改布局（Trace 顺序边已表达交接）。  
- Settings 页或 ExecutionBar 旁只读 chip：`MA on/off` · `Critic on/off`（读 `/api/settings` 或 health 扩展）——建议扩展 `ops` settings 只读返回两布尔。

---

## 8. Legacy 引擎

`AGENT_ENGINE=legacy`：尽量在 `agent/runtime.py` 结束时写空/最小 `multi_agent` 块；Critic **仅 langchain 路径**实现（文档注明）。验收以 langchain 默认引擎为准。

---

## 9. 测试

| 用例 | 期望 |
|------|------|
| unit collaboration helpers | handoff 追加、agents 去重序 |
| graph route | critic off → insight 直连 report；on → 经 critic |
| critic fail | blackboard 含 issues；仍到 report |
| API collaboration | 结构字段存在 |
| MULTI_AGENT false | 主路径仍可（mock/轻量） |

Critic LLM：单测用 monkeypatch 节点或 structured 假返回，避免真 LLM。

---

## 10. 风险

| 风险 | 缓解 |
|------|------|
| handoff 过多噪声 | 仅角色边界记录，不在 tool 循环每步记 Supervisor↔Tools 超过合理次数时可合并 reason |
| Critic 增延迟 | 默认关 |
| state_json 变大 | 截断 summary 字段（如 500 字） |

Supervisor↔Tools 循环：每次进入 tools / 回到 supervisor **各记一条** handoff（可接受）；若过长，P1 再节流。

---

## 11. 实现顺序

V8-0 Config → V8-1 collaboration helpers + state → V8-2 nodes/graph Critic → V8-3 prompts → V8-4 persist/API → V8-5 UI → V8-6 tests/README

---

## 确认方式

请回复：

- **`确认设计`** — 锁定本设计（`tasks.md` 已同步）  
- **`确认设计：…`** — 修改点  

收到 **`开始执行`** 后按 `tasks.md` 改代码。
