# DataMind Agent — V9 Architecture Design

> 对应：`specs/v9/requirements.md`（**已确认**，D1–D6 按建议锁定）  
> 基线：V8 Multi-Agent  
> 状态：**已确认并已实现**  
> 基线：V8 Multi-Agent  
> 非目标：拖拽编排器 / Cron / HITL / 并行 fan-out

---

## 1. 目标

```text
Workflow graph (JSON)
  start → analyze → [condition?] → end
        │
        ▼
  workflow.engine.run(db, workflow, overrides)
        │
        ├─ WorkflowRun + WorkflowRunStep[]
        └─ analyze → Agent facade.run_stream（或 mock）
        │
        ▼
  /api/workflows*  +  /workflows UI（JSON 编辑）
```

---

## 2. 已锁定决策

| # | 取值 |
|---|------|
| D1 | 做 **AI Workflow** |
| D2 | 编辑体验：**JSON + 节点列表**（不做完整拖拽） |
| D3 | `analyze`：**复用现有 Agent Runtime**；CI 用 mock |
| D4 | 条件：`path` + `op`（`eq` / `contains` / `truthy`）+ 可选 `value` |
| D5 | **仅 if/else 单路径**（不并行 fan-out） |
| D6 | **不做** HITL / Cron |

---

## 3. 配置

`server/core/config.py` + `.env.example`：

| 键 | 默认 | 说明 |
|----|------|------|
| `WORKFLOW_MOCK_ANALYZE` | `false` | true 时 analyze 不调 LLM，返回固定答案 |
| `WORKFLOW_TIMEOUT_SEC` | `600` | 单次 Workflow Run 墙钟上限 |

节点数硬上限：`MAX_WORKFLOW_NODES = 30`（代码常量即可）。

---

## 4. 数据模型

### `workflows`

| 字段 | 说明 |
|------|------|
| id / workspace_id | |
| name / description | |
| version | int，更新 graph 时 +1（可选） |
| enabled | bool |
| graph_json | `{ nodes, edges }` |
| is_template | 内置模板标记；用户复制后为 false |
| created_at | |

### `workflow_runs`

| 字段 | 说明 |
|------|------|
| id / workflow_id / workspace_id | |
| status | `running` \| `done` \| `error` \| `cancelled` |
| context_json | 运行时上下文（question、dataset_id、final_answer…） |
| error | |
| started_at / finished_at | |

### `workflow_run_steps`

| 字段 | 说明 |
|------|------|
| run_id / seq / node_id / node_type | |
| status | `pending` \| `running` \| `done` \| `error` \| `skipped` |
| input_json / output_json / error | |
| agent_run_id | analyze 产生时回填 |

### Graph 约定

```json
{
  "nodes": [
    {"id": "s1", "type": "start", "config": {"question": "为什么 8 月销售下降？", "dataset_id": null}},
    {"id": "a1", "type": "analyze", "config": {}},
    {"id": "c1", "type": "condition", "config": {"path": "final_answer", "op": "contains", "value": "下降"}},
    {"id": "e1", "type": "end", "config": {"label": "matched"}},
    {"id": "e2", "type": "end", "config": {"label": "other"}}
  ],
  "edges": [
    {"from": "s1", "to": "a1"},
    {"from": "a1", "to": "c1"},
    {"from": "c1", "to": "e1", "when": "true"},
    {"from": "c1", "to": "e2", "when": "false"}
  ]
}
```

校验：恰好 1 个 `start`；≥1 个 `end`；边端点存在；节点 ≤30；未知 type 拒绝。

---

## 5. 模块划分

```text
workflow/
  __init__.py
  types.py           # Graph / Node / Edge TypedDict 或 pydantic
  validate.py        # validate_graph(graph) -> errors | ok
  conditions.py      # eval_condition(context, config) -> bool
  templates.py       # BUILTIN_TEMPLATES（内存；可 seed 到 DB）
  engine.py          # run_workflow(db, workflow_id, overrides)
  analyze.py         # mock 或 facade 同步跑 Agent

server/models        # Workflow / WorkflowRun / WorkflowRunStep（已有桩）
server/services/workflow_service.py
server/api/workflows.py
server/main.py       # include router；version 0.9.0

apps/web/app/workflows/page.tsx
apps/web/lib/api.ts
apps/web/components/shell/TopBar.tsx

tests/test_workflow.py
```

### 5.1 Engine 流程

1. `validate_graph`；失败 → 400 / run error  
2. 创建 `WorkflowRun`（status=running，context=overrides ∪ start.config）  
3. 自 start 沿边行走；每节点写 Step（running→done/error）  
4. **start**：把 config 的 question/dataset_id 写入 context（overrides 优先）  
5. **analyze**：  
   - mock：`final_answer="[mock] analysis complete"`，`agent_run_id=null`  
   - 真实：解析 dataset → 建临时 Conversation（或复用）→ `create_runtime(db).run_stream(AgentState)` 同步消费至 `final` → 写 `final_answer`、`agent_run_id`  
6. **condition**：`eval_condition` → 选出边 `when=="true"|"false"`；缺边则 error  
7. **end**：status=done，finished_at=now  
8. 任意节点异常：Run=`error`，停止  

超时：循环中检查 `WORKFLOW_TIMEOUT_SEC`。

### 5.2 条件语义

| op | 行为 |
|----|------|
| `eq` | `str(get(path)) == str(value)` |
| `contains` | `str(value) in str(get(path))` |
| `truthy` | bool(get(path))（忽略 value） |

`path`：点分路径，如 `final_answer`、`meta.flag`（仅一层点分即可）。

### 5.3 模板

内置至少：

1. **标准分析**：start → analyze → end  
2. （可选同批）**含条件**：start → analyze → condition → end×2  

`GET /api/workflow-templates` 返回内存模板；`POST /api/workflows` 可带 `template_id` 复制。

---

## 6. API

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/workflows?workspace_id=` | 列表（不含纯系统模板或含 is_template） |
| GET | `/api/workflow-templates` | 内置模板 |
| POST | `/api/workflows` | 创建（body: name, graph, workspace_id, template_id?） |
| GET/PUT/DELETE | `/api/workflows/{id}` | 读写删；写操作走 admin/API Key |
| POST | `/api/workflows/{id}/runs` | `{ question?, dataset_id? }` → 同步执行并返回 run |
| GET | `/api/workflow-runs/{id}` | |
| GET | `/api/workflow-runs/{id}/steps` | |

本切片 Run **同步**执行（请求内跑完）；超时则 error。异步队列留给更后。

---

## 7. 前端

- 路由 `/workflows`：workspace 选择、列表、从模板新建、graph JSON textarea、节点只读列表、触发 Run、展示 steps。  
- TopBar：`Workflows`。  
- 风格对齐 `/knowledge`、`/mcp`（暗色 IDE）。

---

## 8. 测试与版本

| 用例 | 期望 |
|------|------|
| validate | 缺 start / 坏边 → 错误 |
| condition | eq/contains/truthy |
| mock engine | start→analyze→end；context 有 final_answer |
| condition 分支 | true/false 走到不同 end |
| API | CRUD + mock run |

API `version` → **0.9.0**；README 增 V9 节。

---

## 9. 实现顺序

V9-0 收尾 config/ORM → V9-1 engine/mock → V9-2 service/API → V9-3 UI → V9-4 README/pytest

---

## 确认方式

请回复：

- **`确认设计`** — 锁定本设计  
- **`确认设计：…`** — 修改点  
- **`开始执行`** — 按 `tasks.md` 改代码（可与确认设计同条）
