# DataMind Agent — Architecture Design

> 对应需求：`specs/requirements.md`（已确认）  
> 范围：V1 MVP  
> 状态：待审阅

---

## 1. 设计目标

实现可演示、可观测、可扩展的 AI 数据分析 Agent：

1. **真实计算**：数值结论必须来自 Python 工具执行，禁止 LLM 臆造数字。
2. **自主下钻**：Plan → Execute → Observe → RePlan，在步数上限内完成根因分析。
3. **可追溯**：结论绑定 Evidence；全过程写入 Agent Trace。
4. **先跑通再抽象**：核心 Loop 自研、清晰；Gateway / Storage 预留生产演进接口。

---

## 2. 已锁定技术决策

| 层 | 选型 |
|----|------|
| Frontend | Next.js (App Router) + TypeScript + Tailwind CSS + ECharts |
| Backend | Python 3.11+ / FastAPI / Pydantic v2 / SQLAlchemy 2.x |
| Agent | 自研 State Machine（同步状态 + 异步事件流） |
| Data compute | Pandas（V1）；接口预留 DuckDB |
| DB（dev） | SQLite |
| Files（dev） | 本地目录 `storage/uploads/` |
| LLM | Gateway + OpenAI-compatible Provider；默认 DeepSeek |
| Sandbox | 受限子进程（timeout / 白名单 import / 无网络） |
| 包管理 | Backend: `uv` 或 `pip` + `requirements.txt`；Frontend: `pnpm` |

---

## 3. 系统架构

```text
┌─────────────────────────────────────────────────────────────┐
│  apps/web (Next.js)                                         │
│  Workspace · Upload · Chat(SSE) · Trace · Charts · Report   │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼────────────────────────────────┐
│  server (FastAPI)                                           │
│  api/ → services/ → repositories/                           │
└────────┬───────────────────┬───────────────────┬────────────┘
         │                   │                   │
         ▼                   ▼                   ▼
   agent/runtime      llm/gateway         tools/ + sandbox/
   (state machine)    (providers)         (python, chart, …)
         │                                       │
         └──────────────────┬────────────────────┘
                            ▼
              storage/ (SQLite + local files)
              data/ (parser + profiler)
```

### 3.1 请求主路径（分析）

```text
POST /api/conversations/{id}/messages
        ↓
ChatService.create_user_message()
        ↓
AgentRuntime.run(state)  ──SSE──► 前端
        │
        ├─ UNDERSTAND（注入 Profile + Memory）
        ├─ PLAN（Planner）
        ├─ EXECUTE（Python Tool → Sandbox）
        ├─ OBSERVE（Analysis）
        ├─ REPLAN / DRILL（条件）
        ├─ INSIGHT
        ├─ CHART
        └─ REPORT / FINAL
        ↓
持久化 agent_runs / agent_steps / tool_calls / charts / evidence
```

---

## 4. 目录结构

```text
AIDataAnalysis/
├── specs/
│   ├── requirements.md
│   ├── design.md
│   └── tasks.md
├── apps/
│   └── web/                      # Next.js 前端
│       ├── app/
│       ├── components/
│       ├── lib/api/
│       └── package.json
├── server/
│   ├── main.py                   # FastAPI 入口
│   ├── api/                      # 路由
│   ├── services/
│   ├── repositories/
│   ├── models/                   # SQLAlchemy ORM
│   ├── schemas/                  # Pydantic DTO
│   └── core/                     # config, db, logging
├── agent/
│   ├── state.py                  # AgentState
│   ├── runtime.py                # State Machine 主循环
│   ├── events.py                 # SSE 事件类型
│   ├── planner.py
│   ├── analyst.py
│   ├── insight.py
│   ├── reporter.py
│   └── prompts/
├── tools/
│   ├── registry.py
│   ├── dataset.py                # schema / preview
│   ├── python_exec.py
│   ├── statistics.py
│   ├── anomaly.py
│   └── chart.py
├── sandbox/
│   ├── executor.py               # 子进程执行
│   └── security.py               # 白名单 / timeout
├── data/
│   ├── parser.py                 # Excel/CSV → DataFrame
│   └── profiler.py
├── llm/
│   ├── gateway.py
│   ├── types.py
│   └── providers/
│       └── openai_compatible.py
├── storage/
│   ├── database/                 # migrations / sqlite file
│   └── uploads/                  # 本地文件
├── samples/                      # sales 样例数据
├── tests/
├── .env.example
├── pyproject.toml                # 或 requirements.txt
└── README.md
```

说明：仓库根即项目根，逻辑模块与 `PROJECT_DESIGN.md` 对齐，便于面试展示。

---

## 5. 核心模块设计

### 5.1 Agent State Machine

**状态枚举**

```text
INIT → UNDERSTAND → PLAN → EXECUTE → OBSERVE
                         ↑_______↓
                      (need_more && steps < MAX)
                              ↓
                    INSIGHT → VISUALIZE → REPORT → DONE
                              ↘ ERROR / CANCELLED
```

**AgentState（内存 + 可序列化 JSON）**

```python
class AgentState(BaseModel):
    run_id: str
    conversation_id: str
    question: str
    dataset_id: str
    schema: dict
    profile_summary: str
    memory: dict                 # {month, region, product, ...}
    plan: list[PlanStep]
    current_step: int
    observations: list[Observation]
    tool_results: list[ToolResult]
    charts: list[ChartSpec]
    insights: list[Insight]
    evidences: list[Evidence]
    errors: list[str]
    final_answer: str | None
    status: Literal["running","done","error","cancelled"]
    step_count: int
```

**循环伪代码**

```text
while state.status == running and state.step_count < MAX_STEPS:
    emit(trace_event)
    if no plan: plan = Planner(state)
    step = next pending step or RePlan(state)
    code = PythonAgent.generate(step, state)
    result = Sandbox.execute(code, dataset_path)
    if failed: Reflection.fix → retry once
    obs = Analyst.observe(result, state)
    attach Evidence
    if Analyst.should_drill(obs): Planner.append_drill_steps()
    else if Analyst.is_complete(state): break
Insight → Charts → Report → final_answer → DONE
```

**边界**

| 参数 | 默认 |
|------|------|
| `MAX_AGENT_STEPS` | 20 |
| `MAX_TOOL_RETRIES` | 2 |
| `TOOL_TIMEOUT_SEC` | 30 |
| `RUN_TIMEOUT_SEC` | 300 |

### 5.2 LLM Gateway

```text
LLMGateway.chat(messages, *, model?, temperature?, response_format?)
    → ChatResult(content, usage{input_tokens, output_tokens}, raw)
```

- Provider：`OpenAICompatibleProvider`（`base_url` + `api_key` + `model`）
- V1 默认：DeepSeek（OpenAI 兼容）
- Prompt 集中在 `agent/prompts/`，禁止散落硬编码长 prompt

### 5.3 Tools（V1）

| Tool | 职责 |
|------|------|
| `dataset_schema` | 返回字段与类型 |
| `dataset_preview` | 返回前 N 行 |
| `python_execute` | 在 Sandbox 执行代码 |
| `statistics` | 常用描述统计快捷封装（可选，内部可调 Pandas） |
| `anomaly_detection` | 简单异常检测快捷封装 |
| `generate_chart` | 产出 ECharts option JSON |
| `report_generate` | 组装 Markdown 报告 |

SQL Tool：**V1 不做**。

### 5.4 Sandbox（受限子进程）

1. 将代码写入临时文件；注入只读 `df`（由服务端加载 Dataset）。
2. `subprocess` 运行，`timeout=TOOL_TIMEOUT_SEC`。
3. `security.py`：AST 扫描禁止 `import os/sys/subprocess/socket` 等；仅允许 `pandas/numpy/math/json/datetime` 等白名单。
4. 捕获 stdout / 结构化 `result` 变量 / stderr。
5. 失败返回 `success=false, error=...` 供 Reflection。

### 5.5 Dataset Profiler

输入：解析后的 DataFrame  
输出：`DatasetProfile`

- 基础：rows、cols、时间范围  
- 字段：name、inferred_type、null_ratio、nunique、样本值  
- 质量：重复行、数值异常（IQR）、分类基数  
- 分类：time / numeric / categorical 字段列表  

Profile 文本摘要注入 Planner / Python Agent 的 system context。

### 5.6 Evidence

每条重要结论：

```json
{
  "claim": "华东地区销售下降 24.7%",
  "tool_name": "python_execute",
  "code_or_query": "...",
  "result_ref": "tool_call_id",
  "result_preview": "..."
}
```

前端「查看证据」按 `evidence_id` 拉取。

### 5.7 Memory（对话级）

存在 `conversations.context_json`：

```json
{ "dataset_id": "...", "filters": { "month": "2026-08", "region": "华东" } }
```

追问时合并更新 filters，并传入 AgentState.memory。

---

## 6. 数据模型（SQLite / SQLAlchemy）

V1 表（对齐需求，精简用户体系）：

| 表 | 用途 |
|----|------|
| `workspaces` | id, name, created_at |
| `datasets` | id, workspace_id, name, file_path, row_count, col_count, profile_json, status |
| `dataset_fields` | id, dataset_id, name, inferred_type, null_ratio, nunique, meta_json |
| `conversations` | id, workspace_id, dataset_id, title, context_json |
| `messages` | id, conversation_id, role, content, created_at |
| `agent_runs` | id, conversation_id, question, status, model, input_tokens, output_tokens, latency_ms, error |
| `agent_steps` | id, run_id, seq, agent_name, input_summary, output_summary, status, latency_ms |
| `tool_calls` | id, run_id, step_id, tool_name, arguments, result, success, error, duration_ms |
| `charts` | id, run_id, chart_type, title, option_json |
| `insights` | id, run_id, payload_json |
| `evidences` | id, run_id, claim, tool_call_id, payload_json |
| `reports` | id, run_id, markdown, created_at |

不做 `users` 多租户（V1 单机默认 Workspace）。

---

## 7. API 设计（V1）

| Method | Path | 说明 |
|--------|------|------|
| GET/POST | `/api/workspaces` | 列表 / 创建 |
| POST | `/api/workspaces/{id}/datasets` | 上传 Excel/CSV |
| GET | `/api/datasets/{id}` | 详情 + Profile |
| GET | `/api/datasets/{id}/preview` | 预览行 |
| POST | `/api/workspaces/{id}/conversations` | 创建对话（绑定 dataset） |
| GET | `/api/conversations/{id}/messages` | 消息历史 |
| POST | `/api/conversations/{id}/messages` | 发问题；`Accept: text/event-stream` 时 SSE |
| GET | `/api/agent-runs/{id}` | Run 状态 |
| GET | `/api/agent-runs/{id}/trace` | Trace 步骤 |
| GET | `/api/evidences/{id}` | 证据详情 |
| GET | `/api/agent-runs/{id}/report` | Markdown 报告 |
| GET | `/api/health` | 健康检查 |

### SSE 事件（示例）

```text
event: step
data: {"type":"plan","steps":[...]}

event: step
data: {"type":"tool","tool":"python_execute","status":"ok"}

event: observation
data: {"summary":"华东下降 24.7%","evidence_id":"..."}

event: chart
data: {"chart_id":"...","title":"月销售趋势"}

event: final
data: {"answer":"...","report_id":"..."}

event: error
data: {"message":"..."}
```

---

## 8. 前端信息架构

```text
/                     → 重定向到默认 Workspace
/workspaces           → Workspace 列表
/w/[workspaceId]      → 主分析台
  ├─ 左栏：数据集 / 对话历史
  ├─ 中栏：Chat + 流式 Trace 摘要
  └─ 右栏/下方：Charts · Report · Evidence Drawer
```

组件要点：

- `ChatPanel`：消息 + SSE 消费  
- `AgentTracePanel`：步骤时间线  
- `ChartView`：ECharts  
- `EvidenceDrawer`：结论 → 证据  
- `DatasetProfileCard`：Profile 摘要  

视觉：跟随现有产品工具感，清晰层级即可；不另开营销落地页。

---

## 9. 样例数据

`samples/sales.csv`（或 xlsx）需支持 Demo：

- 字段建议：`date, region, product, category, sales, quantity, customer_id, channel`
- 时间覆盖约 2026-01 ~ 2026-08
- 8 月整体下降；华东更显著；SKU-A 大跌；1–2 个核心客户 8 月采购归零  

便于验收 REQ-DEMO-001/002。

---

## 10. 配置与依赖

### 10.1 环境变量（`.env.example`）

```text
APP_ENV=dev
DATABASE_URL=sqlite:///./storage/database/datamind.db
UPLOAD_DIR=./storage/uploads
LLM_BASE_URL=https://api.deepseek.com
LLM_API_KEY=
LLM_MODEL=deepseek-chat
MAX_AGENT_STEPS=20
TOOL_TIMEOUT_SEC=30
```

### 10.2 主要 Python 依赖

`fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `aiosqlite`, `pandas`, `openpyxl`, `python-multipart`, `httpx`, `sse-starlette`, `python-dotenv`

### 10.3 主要前端依赖

`next`, `react`, `typescript`, `tailwindcss`, `echarts`, `echarts-for-react`

---

## 11. 安全与风险（V1）

| 风险 | 缓解 |
|------|------|
| LLM 生成恶意代码 | AST 白名单 + 子进程超时 + 无网络 |
| Agent 死循环 | MAX_AGENT_STEPS + RUN_TIMEOUT |
| 大文件 OOM | V1 限制上传大小（如 20MB）；提示 Future DuckDB |
| 密钥泄露 | `.env` gitignore；仅 Gateway 读取 |
| 幻觉数字 | Prompt + 架构约束：必须引用 tool_results |

---

## 12. 测试策略

| 层 | 内容 |
|----|------|
| Unit | Profiler、Sandbox 安全拒绝、Evidence 关联 |
| Integration | 上传 → Profile →（mock LLM）→ Run 状态机转移 |
| E2E Demo | 真实 LLM（可选 CI skip）：sales 下降根因链路 |
| Contract | SSE 事件 schema |

---

## 13. 演进接口（不实现，仅预留）

- `tools/sql.py` + DB Source  
- `sandbox` → Docker/gVisor  
- `evaluation/` 指标任务  
- `users` / RBAC  
- Storage dialect 切换 PostgreSQL + S3/MinIO  

---

## 14. 与需求映射（摘要）

| 需求组 | 设计落点 |
|--------|----------|
| REQ-WS | workspaces API + 前端左栏 |
| REQ-DS/DP | parser + profiler + datasets 表 |
| REQ-AA/PL/PY/AN/IN/RP | AgentRuntime + 各 Agent 模块 |
| REQ-VZ | chart tool + ECharts |
| REQ-EV/TR/ST | evidences / agent_steps / AgentState |
| REQ-MM/RF/ER | context_json + Reflection + limits |
| REQ-LLM | llm/gateway |
| REQ-DEMO | samples/sales + E2E 脚本 |

---

## 15. 确认方式

请回复：

- `确认设计` — 继续（若尚未生成则生成）/ 审阅 `tasks.md`
- 或指出需修改的章节

**回复「开始执行」后才开始写业务代码。**
