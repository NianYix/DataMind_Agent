# DataMind Agent — V2 Architecture Design

> 对应需求：`specs/v2/requirements.md`（已确认）  
> 基线实现：V1（`agent/runtime.py` 线性 Loop）  
> 状态：待审阅

---

## 1. 设计目标

将 V1 的「硬编码 Plan→Python→Analyze」升级为：

1. **Supervisor 驱动**：每步由 Supervisor 决定下一动作。  
2. **原生 Tool Calling**：LLM 选择并调用注册工具。  
3. **SQL 能力**：DuckDB（文件表）+ 只读 SQLite 源。  
4. **可取消 / 可计费 / 可回看**：Run 生命周期与 UX 闭环。

原则不变：**数值结论必须来自工具真实执行**。

---

## 2. 与 V1 的关系

| V1 | V2 变更 |
|----|---------|
| `AgentRuntime._execute` 固定流水线 | 拆为 `Supervisor` + 动作处理器；保留兼容入口 |
| 仅 `python_execute` 主路径 | 工具清单 + `tool_calls` |
| 仅 CSV/Excel 文件 Dataset | 增加 `source_type=sqlite` |
| Memory 启发式关键词 | LLM 更新 `context_json` |
| 无取消 | `cancel_flags[run_id]` |
| tokens 入库但 UI 弱 | Run 摘要展示 tokens/latency/cost |
| 报告仅 Markdown | 增加 PDF 导出 API |

尽量**增量改造**，避免重写前端壳。

---

## 3. 目标架构

```text
POST /messages (SSE)
        │
        ▼
   ChatService
        │
        ▼
 ┌──────────────────┐
 │ Supervisor Loop  │◄── cancel_flag / MAX_STEPS / RUN_TIMEOUT
 └────────┬─────────┘
          │ decide: plan | tool | analyze | insight | report | finish
          ▼
   ┌──────┴──────┐
   │ LLM Gateway │── tools[] / tool_calls
   └──────┬──────┘
          ▼
   Tool Registry
   ├ dataset_schema / preview
   ├ python_execute (sandbox)
   ├ sql_query (DuckDB / SQLite readonly)
   ├ statistics / anomaly_detection
   └ generate_chart
          │
          ▼
   Persist: agent_steps, tool_calls, evidences, charts, reports
```

---

## 4. Supervisor 设计

### 4.1 动作枚举

```text
understand | plan | call_tool | observe | replan | insight | report | finish | error
```

### 4.2 决策输出（JSON）

```json
{
  "action": "call_tool|plan|insight|report|finish|replan",
  "reason": "short reason",
  "tool_name": "sql_query",
  "tool_args": { "sql": "..." },
  "plan_patch": null
}
```

实现策略（两档，自动降级）：

1. **优先**：`gateway.chat(..., tools=TOOL_SCHEMAS)`，若返回 `tool_calls` 则直接执行。  
2. **Fallback**：Supervisor JSON 决策（当 provider/模型不支持 tools 时）。

### 4.3 主循环伪代码

```text
understand → plan (一次)
while running and steps < MAX and not cancelled and not timed_out:
    decision = supervisor.decide(state)   # or consume pending tool_calls
    emit(trace supervisor)
    match decision.action:
      call_tool → execute tool → append observation raw
      observe   → analyst summarize → evidence
      replan    → append/adjust plan steps
      insight   → break to insight
      report/finish → break
insight → report → done
```

V1 的「按 plan step 生成 Python」可保留为 **Planner 产出步骤 + Supervisor 选工具实现步骤** 的默认策略，避免能力回退。

### 4.4 取消与超时

- 模块 `agent/cancel.py`：`register(run_id)` / `is_cancelled(run_id)` / `request_cancel(run_id)` / `clear(run_id)`  
- API：`POST /api/agent-runs/{id}/cancel`  
- 循环每个动作前检查 cancel + `time.monotonic() - started > RUN_TIMEOUT_SEC`

---

## 5. Tool Calling 与 Gateway 扩展

### 5.1 Gateway API 扩展

```python
ChatResult:
  content: str
  tool_calls: list[{id, name, arguments}] | None
  usage: TokenUsage

LLMGateway.chat(..., tools: list[dict] | None = None, tool_choice: str | dict | None = None)
```

`OpenAICompatibleProvider` 请求体增加 `tools`；解析 `message.tool_calls`。

### 5.2 Tool Schema 注册

`tools/schemas.py`：OpenAI function schema 列表。  
`tools/registry.py`：扩展执行函数，统一签名：

```python
def run_tool(name: str, args: dict, ctx: ToolContext) -> dict
```

`ToolContext`：`dataset_path`, `source_type`, `sqlite_path`, `table_name`, `profile`, `timeout`.

### 5.3 新增 / 强化工具

| Tool | 行为 |
|------|------|
| `sql_query` | 校验只读 → DuckDB 查文件表或 SQLite |
| `statistics` | 对指定列做 describe / group 汇总（Pandas） |
| `anomaly_detection` | IQR 或 z-score 异常行摘要 |
| `generate_chart` | 已有，改为可被 tool call 直接触发 |
| 既有 | `dataset_schema`, `dataset_preview`, `python_execute` |

### 5.4 SQL 安全

`tools/sql_guard.py`：

- 单语句；禁止 `;` 多语句  
- 禁止关键词：`INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/ATTACH/COPY/PRAGMA/EXPORT` 等（白名单思路：仅允许以 `SELECT` 或 `WITH` 开头）  
- `LIMIT` 默认封顶（如 5000）

DuckDB 文件模式：

```sql
SELECT ... FROM read_csv_auto('path')  -- 或先注册 view `data`
```

对用户暴露的表名统一为 `data`（文件源）或实际表名（SQLite 源）。

---

## 6. 数据模型变更

### 6.1 `datasets` 扩展

| 字段 | 说明 |
|------|------|
| `source_type` | `file` \| `sqlite`（默认 `file`） |
| `sqlite_path` | SQLite 文件绝对/相对路径（可与 file_path 复用策略） |
| `table_name` | SQLite 表名 |
| `file_path` | 文件源仍存上传路径；sqlite 源可存库文件路径 |

迁移：SQLite 下用 `create_all` 不足时，启动时执行简单 `ALTER TABLE` 兼容（V2 可接受），或提供 `scripts/migrate_v2.py`。

### 6.2 `agent_runs` 扩展

| 字段 | 说明 |
|------|------|
| `estimated_cost` | float, nullable |
| `cancel_requested` | bool, default false |

（若不想改表，cost 可算完写入 `state_json`；推荐显式字段便于列表查询。）

### 6.3 配置新增（`.env`）

```text
LLM_INPUT_PRICE_PER_1K=0
LLM_OUTPUT_PRICE_PER_1K=0
DUCKDB_ENABLED=true
```

---

## 7. API 变更

| Method | Path | 说明 |
|--------|------|------|
| POST | `/api/workspaces/{id}/datasets/sqlite` | body: `{ path, table_name, name? }` 注册 SQLite 表 |
| GET | `/api/workspaces/{id}/agent-runs` | 历史 Run 列表 |
| GET | `/api/conversations/{id}/agent-runs` | 对话下 Run |
| POST | `/api/agent-runs/{id}/cancel` | 取消 |
| GET | `/api/agent-runs/{id}/report.pdf` | PDF 导出 |
| GET | `/api/agent-runs/{id}/evidences` | Evidence 列表 |

已有 Trace/Report/Charts/Evidence 详情保留。

---

## 8. Memory 设计

`agent/memory.py`：

```text
input: previous context_json + latest user message
output: { filters: {...}, notes: "..." }
```

- 发消息时先跑 Memory 更新，再启动 Supervisor。  
- Prompt 要求：只抽取明确约束；「看全部/取消筛选」则删除对应键。

---

## 9. PDF 导出

- 依赖：`markdown` + `xhtml2pdf`（纯 Python，Windows 友好）  
- 服务：`server/services/report_export.py`：markdown → HTML → PDF bytes  
- 前端：报告区增加「导出 PDF」链接

---

## 10. 前端改动（增量）

1. **取消按钮**：`running` 时显示，调用 cancel API。  
2. **Run 摘要条**：tokens / latency / cost。  
3. **历史 Run**：左栏或对话下拉，选择后加载 trace/charts/report/evidences。  
4. **Evidence 列表**：多条可点选（不仅最后一条）。  
5. **注册 SQLite**：侧栏表单（路径 + 表名）。  
6. SSE：识别 `supervisor` / `cancelled` 事件。

---

## 11. 目录增量

```text
agent/
  supervisor.py      # 决策
  memory.py          # 上下文更新
  cancel.py          # 取消注册表
  runtime.py         # 改为 Supervisor Loop（或 runtime_v2 + 开关）
tools/
  sql_query.py
  sql_guard.py
  statistics.py
  anomaly.py
  schemas.py
llm/
  providers/openai_compatible.py  # tools 支持
samples/
  sales.sqlite       # 由 CSV 生成的样例库
server/services/
  report_export.py
  sqlite_source.py
specs/v2/
  requirements.md
  design.md
  tasks.md
```

---

## 12. 兼容与开关

- 默认启用 V2 Runtime。  
- 若 `LLM` tool calling 连续失败，自动 fallback Supervisor JSON，不阻断分析。  
- 文件 Dataset 行为与 V1 兼容；旧数据 `source_type` 缺省视为 `file`。

---

## 13. 测试计划

| 测试 | 内容 |
|------|------|
| Unit | `sql_guard` 拒绝写 SQL；cancel flag；cost 计算 |
| Unit | DuckDB `SELECT` on sales.csv |
| Integration | mock LLM tool_calls → 执行 sql_query → 落库 |
| Manual Demo | DEMO-001~004 |

---

## 14. 风险

| 风险 | 缓解 |
|------|------|
| 部分国产模型 tools 支持差 | JSON fallback |
| DuckDB 依赖体积 | 可选依赖；无则 SQL 文件源降级提示 |
| 取消无法打断阻塞子进程 | 子进程仍受 timeout；循环层停止调度新步骤 |
| SQLite 路径安全 | 限制在 workspace 允许目录或用户确认的绝对路径（V2：禁止 `..` 逃逸 uploads 外可配置） |

**SQLite 路径策略（推荐）**：仅允许 `storage/` 下路径，或通过上传 `.db` 文件到 uploads 再注册（更安全）。API 采用：**上传 sqlite 文件** 或 **选择已上传的 .db + table_name**，避免任意系统路径。

修订：`POST .../datasets/sqlite` 改为 multipart 上传 `.db/.sqlite` + `table_name`，与文件上传安全模型一致。

---

## 15. 需求映射

| 需求 | 设计落点 |
|------|----------|
| SUP-* | `agent/supervisor.py` + runtime loop |
| TC-* | gateway tools + registry + schemas |
| SQL-* | sql_query + sql_guard + sqlite dataset |
| MM-* | `agent/memory.py` |
| OBS-* | cancel API + cost fields + logging |
| UX-* | 前端历史/Evidence/PDF/取消 |
| DEMO-* | samples/sales.sqlite + 手工验收 |

---

## 16. 确认方式

请回复：

- **`确认设计`** — 继续审阅 / 锁定 `tasks.md`  
- 或指出修改点  

**回复「开始执行」后才改业务代码。**
