# DataMind Agent — V8 Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 状态：**已执行**  
> 决策：D1–D6 建议默认已锁定

---

## Phase V8-0 — 基础 `[P0]`

### T0.1 Config
- [x] Settings：`MULTI_AGENT_ENABLED`（默认 true）、`CRITIC_ENABLED`（默认 false）
- [x] `.env.example`；ops/settings 只读返回两字段
- **验收**：配置可读

---

## Phase V8-1 — Collaboration 核心 `[P0]`

### T1.1 Helpers + State
- [x] `agent/lc/collaboration.py`
- [x] `GraphState` 扩展 handoffs / blackboard / agents_involved / critic_result
- **验收**：单元测试 helpers

---

## Phase V8-2 — Graph + Critic `[P0]`

### T2.1 节点打点
- [x] understand/plan/supervisor/tools/observe/insight/report 入口 touch + 边界 handoff
- [x] blackboard 约定键由 Analyst/Insight/Critic 写入

### T2.2 Critic 节点
- [x] `critic_node` + `CRITIC_SYSTEM`；`graph.py` 条件边
- [x] 不通过：写 blackboard，继续 Report
- **验收**：开关两条路由可测

---

## Phase V8-3 — Prompts `[P0]`

### T3.1 角色 Prompt 解析
- [x] `resolve_role_system`；insight/critic/planner 接入
- [x] Prompts 页说明可覆盖名称
- **验收**：无 DB 覆盖时用内置

---

## Phase V8-4 — 持久化与 API `[P0]`

### T4.1 state_json + collaboration API
- [x] runtime 写入 `multi_agent` 块
- [x] `GET /api/agent-runs/{id}/collaboration`
- **验收**：TestClient 有字段

---

## Phase V8-5 — 前端 `[P1]`

### T5.1 Inspector + flowModel
- [x] Inspector「Agents」Tab；api helper
- [x] flowModel 识别 critic；Settings 只读开关展示
- **验收**：手工可见 handoff/blackboard

---

## Phase V8-6 — 文档与回归 `[P0]`

### T6.1 README / pytest / version
- [x] `tests/test_multi_agent.py`
- [x] README V8；API version `0.8.0`
- **验收**：`pytest -q` 全绿；`tsc` 通过

---

## 确认与执行

已收到 **「开始执行」** 并完成 V8 主路径。
