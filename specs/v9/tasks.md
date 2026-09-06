# DataMind Agent — V9 Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 状态：**已执行**  
> 决策：D1–D6 建议默认已锁定

---

## Phase V9-0 — 基础 `[P0]`

### T0.1 Config / ORM 收尾
- [x] Settings：`WORKFLOW_MOCK_ANALYZE`、`WORKFLOW_TIMEOUT_SEC`
- [x] ORM：`Workflow` / `WorkflowRun` / `WorkflowRunStep`；forward-ref
- [x] `.env.example`
- **验收**：import + create_all 成功

---

## Phase V9-1 — Engine `[P0]`

### T1.1 validate / conditions / templates
- [x] `workflow/validate.py`、`conditions.py`、`templates.py`

### T1.2 engine + mock analyze
- [x] `workflow/engine.py`、`analyze.py`
- **验收**：start→analyze→end；condition 分支

---

## Phase V9-2 — API `[P0]`

### T2.1 service + router
- [x] `workflow_service.py`、`server/api/workflows.py`；main 0.9.0
- **验收**：TestClient CRUD + mock run

---

## Phase V9-3 — 前端 `[P1]`

### T3.1 `/workflows` + TopBar
- [x] page + api.ts + TopBar
- **验收**：tsc 通过

---

## Phase V9-4 — 文档与回归 `[P0]`

### T4.1 README / pytest / version
- [x] `tests/test_workflow.py`；README V9；API **0.9.0**
- **验收**：`pytest -q` 全绿

---

## 确认与执行

已收到 **「开始执行」** 并完成 V9 主路径。
