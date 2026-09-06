# DataMind Agent — V7 Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 状态：**已执行**  
> 决策：D1–D6 建议默认已锁定

---

## Phase V7-0 — 基础 `[P0]`

### T0.1 Config / deps
- [x] Settings：`MCP_ENABLED`、`MCP_CONFIG_PATH`
- [x] `.env.example`；`mcp_servers.example.json`
- [x] `requirements.txt` 增加 `mcp`（运行时桥接为 `mcp_host` 最小子集）
- **验收**：配置可读；默认 enabled=false

### T0.2 包骨架
- [x] `mcp_host/` 包（避免与 PyPI `mcp` 冲突）
- **验收**：import 通过

---

## Phase V7-1 — Client + Mock `[P0]`

### T1.1 Mock stdio server
- [x] `mcp_host/mock_server.py`：tool `echo`
- **验收**：可手动 stdio 或单测拉起

### T1.2 Client + Manager
- [x] `client.py`：connect / list_tools / call_tool / close
- [x] `manager.py`：start_all / stop_all / reload / status / call
- **验收**：指向 mock 的临时 JSON 可 list + call

---

## Phase V7-2 — Bridge + Agent `[P0]`

### T2.1 Registry 桥接
- [x] `bridge.py` + `run_tool` / list 合并 `mcp_*`
- [x] 前缀与 sanitize；超时与错误结构
- **验收**：`run_tool("mcp_demo_echo", …)` 成功

### T2.2 LangChain + 提示词
- [x] `agent/lc/tools.py`：`build_tools` 包含 MCP 工具
- [x] Supervisor/Picker + `with_mcp_catalog`
- **验收**：enabled 时工具可见；disabled 无增量

---

## Phase V7-3 — API `[P0]`

### T3.1 MCP API + lifespan
- [x] `mcp_service.py`、`server/api/mcp.py`
- [x] GET status / tools；POST reload
- [x] FastAPI lifespan 挂钩 manager
- **验收**：TestClient + mock 全路径

---

## Phase V7-4 — 前端 `[P1]`

### T4.1 `/mcp` + TopBar
- [x] `apps/web/app/mcp/page.tsx`；`api.ts` helpers
- [x] TopBar「MCP」
- **验收**：展示 server 状态与工具列表

---

## Phase V7-5 — MCP Server `[P1]`

### T5.1 对外只读 Server
- [x] `python -m server.mcp_server`：`ping` + `knowledge_search`
- **验收**：可被 client list；无写操作

---

## Phase V7-6 — 文档与回归 `[P0]`

### T6.1 README / pytest
- [x] `tests/test_mcp.py`：disabled / mock list / call / 前缀 / server
- [x] README V7 节；版本号 `0.7.0`
- **验收**：`pytest -q` 全绿；`MCP_ENABLED=false` 行为与 V6 一致

---

## 确认与执行

已收到 **「开始执行」** 并完成 V7 主路径。
