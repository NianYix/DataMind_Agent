# DataMind Agent — V7 Architecture Design

> 对应：`specs/v7/requirements.md`（**已确认**，D1–D6 按建议锁定）  
> 基线：V6 RAG + UI Optimize  
> 状态：**已确认并已实现**（待回归勾选）
> 基线：V6 RAG + UI Optimize  
> 非目标：Multi-Agent / OAuth 远程 MCP 市场 / Resources 完整 UI / 无限制 Shell

**实现备注**：本地包名为 `mcp_host/`（避免与 PyPI `mcp` 冲突）；传输为 Content-Length JSON-RPC 最小子集。

---

## 1. 目标

```text
mcp_servers.json
        │
        ▼
  MCP Manager (Client)
   ├─ stdio session(s)
   ├─ tools/list
   └─ tools/call
        │
        ▼
  Bridge → registry / LC StructuredTool
   name: mcp_<server_id>_<tool>
        │
        ▼
  Agent Run + audit / tool_calls
        │
        ▼
  GET /api/mcp/*  +  /mcp UI

P1 (optional process):
  python -m server.mcp_server  ──stdio──► Cursor / other hosts
     tools: knowledge_search, dataset_schema  (readonly)
```

---

## 2. 已锁定决策

| # | 取值 |
|---|------|
| D1 | 做 **MCP（本阶段）** |
| D2 | **Client 为主**；**Server 为 P1** |
| D3 | **stdio 必需**；SSE 可选 P1（本切片可不实现 SSE） |
| D4 | 优先官方 **`mcp` Python SDK**；若安装/API 受阻则自研 JSON-RPC 最小子集（initialize / tools/list / tools/call） |
| D5 | 配置：`MCP_CONFIG_PATH` 默认 **`./storage/mcp_servers.json`**；样例 **`mcp_servers.example.json`**（可放仓库根或 `storage/`） |
| D6 | **不做** Multi-Agent（V8） |

---

## 3. 配置

`server/core/config.py` + `.env.example`：

| 键 | 默认 | 说明 |
|----|------|------|
| `MCP_ENABLED` | `false` | 总开关；false 时不连接、不注册 MCP 工具 |
| `MCP_CONFIG_PATH` | `./storage/mcp_servers.json` | Server 列表 JSON |
| （复用）`TOOL_TIMEOUT_SEC` | 现有 | MCP `tools/call` 超时上限 |

### 3.1 `mcp_servers.json` 形状

```json
{
  "servers": [
    {
      "id": "demo",
      "enabled": true,
      "transport": "stdio",
      "command": "python",
      "args": ["-m", "mcp_demo.server"],
      "env": {}
    }
  ]
}
```

- `id`：稳定短名，用于工具前缀 `mcp_<id>_`。  
- 文件缺失且 `MCP_ENABLED=true`：视为空列表 + 可观测 warning，不 500。  
- 样例文件入库；真实 `storage/mcp_servers.json` 可 gitignore（与 chroma/knowledge 类似）。

---

## 4. 模块划分

```text
mcp/
  types.py           # ServerConfig, ToolDescriptor, CallResult
  config_loader.py   # 读 JSON → list[ServerConfig]
  client.py          # stdio session：connect / list_tools / call_tool / close
  manager.py         # 生命周期：startup/reload、按 server 状态、聚合 tools
  bridge.py          # MCP tool → DataMind 可调用入口（统一 payload）
  mock_server.py     # CI：假 Server，暴露 echo（或 add）

server/services/mcp_service.py
server/api/mcp.py
server/mcp_server.py          # P1：对外 MCP Server 入口

tools/registry.py             # 动态挂载 mcp_* 或 run_tool 委托 manager
agent/lc/tools.py             # build_tools 时 append MCP StructuredTools
agent prompts / picker        # 提及可用 mcp_* 工具（动态摘要）

apps/web/app/mcp/page.tsx
apps/web/lib/api.ts           # mcp helpers
apps/web/components/shell/TopBar.tsx
```

### 4.1 Client 会话

- 使用官方 SDK 的 stdio client（或等价最小 JSON-RPC over stdin/stdout）。  
- **懒连接或进程启动时 connect**：建议 `manager.ensure_started()` 在 API reload / 首次 `list_bridged_tools` / Agent `build_tools` 时触发；进程退出 `atexit`/FastAPI lifespan 关闭子进程。  
- 每个 server 独立子进程；一个失败不影响其他 server。

### 4.2 Bridge 约定

| 项 | 约定 |
|----|------|
| 工具名 | `mcp_{server_id}_{sanitize(tool_name)}`；sanitize：非 `[a-zA-Z0-9_]` → `_` |
| 入参 | MCP `inputSchema` → 动态 pydantic 或 `dict` 透传；LC 侧可用宽松 `arguments: dict` |
| 出参 | `{ success, content, is_error?, raw? }`；文本/JSON content 尽量 flatten |
| 超时 | `min(TOOL_TIMEOUT_SEC, per-call)`；超时 → success=false |
| 审计 | 与现有 tool_calls 一致写入 run step |

与内置 tool **同名冲突**：MCP 侧必须带前缀，永不覆盖 `sql_query` 等。

### 4.3 Registry / LangChain

两种等价策略（实现选一，推荐 A）：

- **A（推荐）**：`run_tool` 识别 `name.startswith("mcp_")` → 解析 server/tool → `manager.call(...)`；`list_tools()` 合并静态 + 动态 MCP 描述。  
- **B**：仅在 `agent/lc/tools.py` 的 `build_tools` 动态 append StructuredTool，legacy registry 不感知。

为兼容 `AGENT_ENGINE=legacy`，**优先 A**。

### 4.4 Mock Server（P0）

- `mcp/mock_server.py`：可 `python -m mcp.mock_server` stdio 进程。  
- Tool：`echo` — 入参 `{ "text": string }`，返回原样。  
- pytest：写临时 `mcp_servers.json` 指向该模块，`MCP_ENABLED=true`，断言 list + call + bridge 名。

### 4.5 MCP Server（P1）

- `python -m server.mcp_server`：stdio，工具仅：
  - `knowledge_search`（query / knowledge_base_id? / top_k?）
  - `dataset_schema`（需约定：通过 env/参数指定 dataset，或仅返回「需 DataMind API」说明 — **建议**：P1 仅暴露 `knowledge_search` + 一个 `ping`，`dataset_schema` 若缺运行时上下文则返回明确错误文案）  
- **修订（可落地）**：P1 对外工具定为 **`ping`**、**`knowledge_search`**；`dataset_schema` 若无法在无会话上下文安全调用则文档标明 defer，或要求 env `MCP_DEFAULT_DATASET_PATH`（可选）。需求 REQ-V7-SRV-001 的 `dataset_schema` 以「有合理上下文时可用」为准。

---

## 5. API

挂载 `server/main.py`，前缀 `/api/mcp`，鉴权与现有 admin/API Key 一致。

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/mcp/status` | `enabled`、各 server：id/状态/error/tool_count |
| GET | `/api/mcp/tools` | 已桥接工具列表（name、server_id、description、schema） |
| POST | `/api/mcp/reload` | 重读配置并重连（admin） |
| POST | `/api/mcp/call` | 可选调试：直接 call 某桥接 tool（P1，非必须） |

错误：连接失败 → 200/状态字段 `error`，或 503 仅对 reload；**不**在 list status 时抛未捕获异常导致 500。

---

## 6. 前端

- 路由：`/mcp`（暗色 IDE 风格，与 `/knowledge`、`/prompts` 一致）。  
- 展示：总开关只读（来自 API；改 `.env` 提示）；server 卡片：状态、错误、工具表。  
- TopBar：`MCP` 导航。  
- 无卡片堆砌：一页一职——「MCP 连接与工具目录」。

---

## 7. Agent 提示词

- Supervisor / ToolPicker（及 LC system 摘要）：当存在桥接工具时，追加简短目录（name + one-line description），截断至 N 条（如 20）防爆上下文。  
- `MCP_ENABLED=false` 时零增量。

---

## 8. 依赖与版本

- `requirements.txt`：`mcp`（官方 SDK；锁定兼容版本并在 README 注明）。  
- 若 SDK 与当前 Python 冲突：实现 `mcp/jsonrpc_stdio.py` 最小子集，README 说明 fallback。

---

## 9. 生命周期（FastAPI）

```text
startup (optional): if MCP_ENABLED → manager.start_all()
shutdown: manager.stop_all()
reload API: stop → load config → start
```

子进程泄漏：每个 session 跟踪 Popen；stop 发 terminate + timeout kill。

---

## 10. 测试

| 用例 | 期望 |
|------|------|
| disabled | 无 mcp_ 工具；status.enabled=false |
| mock connect | status connected；tools 含 `mcp_demo_echo`（或配置 id） |
| call echo | success + 回显 |
| bad command | 该 server error；其他仍可用；Agent 单次 tool 失败不拖垮（既有行为） |
| 前缀不覆盖 | `sql_query` 仍为内置 |

---

## 11. 风险与缓解

| 风险 | 缓解 |
|------|------|
| SDK API 变动 | 隔离在 `mcp/client.py`；单测 mock |
| 子进程挂起 | 超时 + shutdown kill |
| 工具爆炸占上下文 | 提示词截断；UI 分页 |
| 危险外部 tool | 默认 MCP off；文档强调只接可信 Server |

---

## 12. 实现顺序（对应 tasks）

V7-0 Config/deps → V7-1 Client+Mock → V7-2 Bridge+Agent → V7-3 API → V7-4 UI → V7-5 Server P1 → V7-6 README/pytest

---

## 确认方式

请回复：

- **`确认设计`** — 锁定本设计，可再出/已同步 `tasks.md`  
- **`确认设计：…`** — 修改点  

收到 **`开始执行`** 后按 `tasks.md` 改代码。
