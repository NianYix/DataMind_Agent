# DataMind Agent — V10 Architecture Design

> 对应：`specs/v10/requirements.md`（**已确认**，D1–D7 按建议锁定）  
> 基线：V9 Workflow + BL-002/003  
> 状态：**已确认并已实现**  
> 非目标：Workflow 多源、跨 Workspace 联邦、自动 JOIN 键、合并上传向导

---

## 1. 目标

```text
Workspace UI: 多选 Dataset + 主表
        │
        ▼
Conversation.dataset_id = primary
context_json.dataset_ids = [primary, ...]  (有序、去重、≤5)
        │
        ▼
stream_analysis → AgentState.datasets[] + aliases
        │
        ├─ Prompt：多表 schema 摘要 + 别名约定
        └─ ToolContext.sources[]
                │
                ├─ SQL DuckDB：REGISTER/VIEW data, data_2, …
                └─ Python sandbox：df, df_2, …
                │
                ▼
Evidence / tool payload 可选 source（表名）
```

单 Dataset 时整条链路与 V9 等价（仅 `data` / `df`）。

---

## 2. 已锁定决策

| # | 取值 |
|---|------|
| D1 | 做 **Multi-Dataset 同 Run（BL-001）** |
| D2 | **`dataset_ids[]` + `primary_dataset_id`**；响应保留 `dataset_id` = primary |
| D3 | SQL：**`data` + `data_2`…`data_N`** |
| D4 | Python：**`df` + `df_2`…`df_N`**（与 SQL 序号对齐；`df` ≡ primary ≡ `data`） |
| D5 | 存储：**`Conversation.dataset_id` = primary** + **`context_json.dataset_ids`**（有序列表，首项=primary） |
| D6 | **不做** Workflow analyze 多源 |
| D7 | 上限 **5**（`MAX_DATASETS_PER_CONVERSATION = 5`；可选 Settings） |

**UI 绑定策略（REQ-V10-UI-004）**：改选 Dataset 集合后，**清空当前 `conversationId`**；下次提问 **新建** Conversation 写入新绑定。不改写历史 Run / 旧会话的 `context_json`。

---

## 3. 配置

`server/core/config.py` + `.env.example`：

| 键 | 默认 | 说明 |
|----|------|------|
| `MAX_DATASETS_PER_CONVERSATION` | `5` | 单会话绑定上限 |

代码常量可与 Settings 同步；超限 API 返回 400。

---

## 4. 数据模型与契约

### 4.1 Conversation（无新表）

| 字段 | 约定 |
|------|------|
| `dataset_id` | **primary**（FK，必填于可分析会话） |
| `context_json` | 至少含：`dataset_ids: string[]`（有序，`[0]==dataset_id`）、`filters`（既有 memory）；可冗余 `primary_dataset_id` |

创建时规范化：

```text
input: dataset_id? | dataset_ids? | primary_dataset_id?
  → resolve list (兼容只传 dataset_id)
  → dedupe preserve order
  → primary = primary_dataset_id or list[0]
  → ensure primary in list; move primary to index 0
  → len in [1, MAX]
  → all belong to workspace
```

### 4.2 API Schema

`ConversationCreate`：

```json
{
  "dataset_id": "可选，兼容",
  "dataset_ids": ["可选，优先"],
  "primary_dataset_id": "可选",
  "title": "可选"
}
```

`ConversationOut`：增加 `dataset_ids`、`primary_dataset_id`；`dataset_id` 仍为 primary。

**不新增 PATCH Conversation**（本阶段）：换绑 = 新会话（与现网改 Dataset 清 `conversationId` 一致，并扩展为多选集合变化也清会话）。

### 4.3 AgentState / GraphState

扩展（向后兼容单字段）：

```text
dataset_id, dataset_path, source_type, table_name, …  # primary，保留
datasets: list[{
  id, alias,           # alias: "data" | "data_2" | …
  path, source_type, table_name, connection_id,
  name?, row_count?, profile_summary?
}]
```

别名规则：primary → `data`；其余按 `dataset_ids` 顺序（跳过 primary 已占位）→ `data_2` … `data_N`。  
Python 帧：`df` ↔ `data`；`df_k` ↔ `data_k`（k≥2）。

### 4.4 ToolContext

```text
ToolContext:
  # 兼容：primary 单路径字段保留
  dataset_path, source_type, table_name, profile, …
  sources: list[ToolSource]   # 同上结构 + alias
```

`run_tool` / handlers：无 `table`/`alias` 参数时默认 primary；`dataset_schema` / `dataset_preview` 接受可选 `alias`（如 `data_2`）。

### 4.5 Evidence（轻量）

工具成功返回的 payload / Evidence `payload_json` 增加可选 `source: { alias, dataset_id }`。不强制改 UI Evidence 列表结构；Inspector 展示时若存在则显示。

---

## 5. 模块划分

```text
server/
  schemas/__init__.py      # ConversationCreate/Out 扩展
  services/chat_service.py # 绑定校验 + create；stream 装载多 Dataset
  services/dataset_binding.py  # 新建：normalize_dataset_ids / load_sources
  core/config.py           # MAX_DATASETS_PER_CONVERSATION
  main.py                  # version 0.10.0

agent/
  state.py / lc/state.py   # datasets[]
  runtime.py / lc/nodes.py # ToolContext.sources
  prompts / understand     # 多表摘要注入（找现有 schema 注入点）

tools/
  registry.py              # ToolContext.sources；schema/preview alias
  sql_query.py             # 多 VIEW/register
sandbox/
  executor.py              # 多 CSV → df / df_2…
  python_runner.py         # 传 sources 或扩展 API
  sql_runner.py            # 透传 sources

apps/web/
  lib/api.ts               # Conversation 类型；createConversation(ids)
  components/agent/AgentPanel.tsx  # 多选 + 主表
  app/page.tsx             # selectedDatasetIds + primary；ensureConversation
  components/inspector/Inspector.tsx  # Context 展示多表绑定
```

**不改**：`workflow/analyze.py` 多源（D6）。

---

## 6. 沙箱行为

### 6.1 SQL（DuckDB 文件类）

对每个 source：

- `data`：保持现有 `read_csv_auto` / Excel register / SQLite VIEW 逻辑  
- `data_k`：同样方式注册对应 path  

远程 MySQL/PG：若现网是单连接单表，本阶段 **仅支持多个已物化为 file/sqlite Dataset**；若 secondary 为 remote 且无法进 DuckDB，创建会话或 stream 启动时 **显式 400/错误**（NFR-V10-001），不静默丢表。

优先验收路径：**双 CSV / Excel file Dataset**。

### 6.2 Python

`execute_python` 启动脚本改为加载多文件：

```python
df = <primary>
df_2 = <second>   # 若存在
…
# 可选：dfs = {"data": df, "data_2": df_2, ...}
```

单表时仅注入 `df`（与现网一致，不强制注入空的 `df_2`）。

### 6.3 内存降级（NFR-V10-002）

- Prompt / schema：**优先用 profile 字段摘要**，避免为提示加载全表。  
- 工具调用：**按需** load 被引用表；SQL/Python 执行时再读文件（与现网一致）。  
- 不在 stream 开始时把所有表全量进进程内存（除非现网已如此）；多表时循环 load 注册即可。

---

## 7. Prompt / Agent

在现有「注入 schema / profile」位置：

- 单表：文案不变。  
- 多表：列出每张表 `alias`、显示名、行列、字段名类型摘要；明确：

```text
SQL tables: data (primary), data_2, …
Python: df, df_2, …
Join across tables when the question needs it.
```

---

## 8. 前端

### AgentPanel Datasets

- Checkbox / 多选行；点击「设为主表」或第一选中为 primary。  
- 展示 `主` 徽标。  
- `onSelectionChange({ datasetIds, primaryId })`。

### page.tsx

- State：`datasetIds: string[]`、`primaryDatasetId: string`（替换或扩展单一 `datasetId`）。  
- 选择变化 → `setConversationId("")`。  
- `ensureConversation` → `createConversation({ dataset_ids, primary_dataset_id 或 dataset_id })`。  
- Inspector Context：列出绑定表（主/辅）；主表详情可仍用 primary 的 profile。

### api.ts

- `Conversation` 增加 `dataset_ids?`、`primary_dataset_id?`。  
- `createConversation(workspaceId, { datasetId } | { datasetIds, primaryDatasetId })`。

---

## 9. 测试计划

| 用例 | 断言 |
|------|------|
| API 只传 `dataset_id` | 创建成功；`dataset_ids` 长度 1 |
| API 传 2 ids + primary | `context_json.dataset_ids` 正确；`dataset_id`=primary |
| 超限 6 | 400 |
| 跨 workspace id | 400 |
| SQL JOIN `data` ⋈ `data_2` | fixture 两 CSV，`run_sql` success |
| Python 读 `df` 与 `df_2` | `python_execute` 返回双行数 |
| 单 Dataset 回归 | 既有 analysis/tool 测试仍绿 |
| health | version `0.10.0` |

---

## 10. 版本与文档

- `server/main.py` + health → **0.10.0**  
- README：功能一览增加 V10 多 Dataset；specs 链接  
- `specs/backlog.md` BL-001 → 已完成后勾选  

---

## 11. 风险

| 风险 | 缓解 |
|------|------|
| 远程多表无法进 DuckDB | 本阶段验收以 file 为主；remote 多源直接报错 |
| Prompt 过长 | 字段摘要截断（每表 top N 列） |
| 旧前端只传 `dataset_id` | 兼容路径保留 |

---

## 12. 确认与下一步

设计已按锁定决策写好。请回复：

- **`开始执行`** — 按 `tasks.md` 实现  
- 或指出设计需改点后再执行  

**未回复「开始执行」前不改业务代码。**
