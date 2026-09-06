# DataMind Agent — V7 Requirements

> 基线：V1–V6 + UI Optimize（已实现）  
> 本阶段：**V7 — MCP（Model Context Protocol）集成**  
> 语法：EARS  
> 状态：**已确认**（D1–D6 按建议锁定）

---

## 0. 阶段定位

| 已完成 | 本阶段 | 明确另开 |
|--------|--------|----------|
| V1–V5 分析 / 企业切片 | **MCP Client：接入外部 MCP Server 工具** | Multi-Agent 编排 |
| V6 RAG Knowledge | **可选薄 MCP Server：对外暴露精选能力** | SSO / 行级权限 |
| UI Optimize | | 完整 MCP 市场 / OAuth 远程托管 |

`PROJECT_DESIGN` 在 RAG 之后的扩展项为 **MCP**。本切片目标：让 DataMind Agent 能消费外部 MCP Tools，并（可选）以 MCP Server 身份把核心能力提供给 Cursor 等宿主。

---

## 1. 阶段目标

1. **MCP Client**：配置并连接 ≥1 个 MCP Server（优先 **stdio**；可选 SSE/HTTP）。  
2. **工具桥接**：将 MCP `tools/list` 映射为 Agent 可调用 Tool（经现有 registry / LangChain StructuredTool）。  
3. **安全边界**：连接与调用可开关；工具名加前缀防冲突；调用写入 audit / tool_calls。  
4. **薄 MCP Server（P1）**：对外暴露精选只读能力（如 `knowledge_search`、`dataset_schema`）。  
5. **可回归**：无真实外部 Server 时用 **mock MCP server** 跑通 CI。

**非目标**：MCP Resources/Prompts 全协议面、OAuth 远程 MCP 市场、任意危险系统命令代理、Multi-Agent 工作流引擎。

---

## 2. 范围

### 2.1 In Scope

| 模块 | 内容 |
|------|------|
| Config | `MCP_ENABLED`、server 列表（JSON/文件） |
| Client | stdio 连接、initialize、tools/list、tools/call |
| Bridge | MCP tool → DataMind Tool；前缀 `mcp_<server>_` |
| Agent | Supervisor/Picker 提示词提及 MCP 工具；运行时动态挂载 |
| API / UI | 列表 servers、状态、工具目录；可选启用/禁用 |
| Mock | 内存/脚本 mock server 供 pytest |
| Server（P1） | 标准 MCP server 入口暴露 2–3 个只读 tool |

### 2.2 Out of Scope

| 项 | 去向 |
|----|------|
| Multi-Agent / Workflow | V8+ |
| MCP Resources 完整浏览 UI | 更后 |
| 远程 OAuth MCP Hosting | 更后 |
| 把任意 Shell/文件系统无限制暴露 | 永不默认开启 |

---

## 3. 功能需求

### 3.1 配置与连接

**REQ-V7-CFG-001**  
THE SYSTEM SHALL 支持配置项至少：`MCP_ENABLED`（默认 `false`）、`MCP_CONFIG_PATH`（指向 JSON，列出 servers）。

**REQ-V7-CFG-002**  
WHEN MCP config 中声明 server，THE SYSTEM SHALL 支持类型 `stdio`（command + args + env）；可选支持 `sse` URL（P1）。

**REQ-V7-CFG-003**  
IF `MCP_ENABLED=false`，THEN THE SYSTEM SHALL 不连接任何 MCP Server，且不向 Agent 注册 MCP 工具。

---

### 3.2 Client 与工具桥接

**REQ-V7-CLI-001**  
WHEN MCP 启用且 server 可达，THE SYSTEM SHALL 完成握手并拉取 `tools/list`。

**REQ-V7-CLI-002**  
THE SYSTEM SHALL 将每个 MCP tool 注册为 Agent 可调用工具，名称带稳定前缀（如 `mcp_<server_id>_<tool>`），避免与内置 tool 冲突。

**REQ-V7-CLI-003**  
WHEN Agent 调用 MCP 桥接工具，THE SYSTEM SHALL 转发 `tools/call`，返回结构化结果；超时受 `TOOL_TIMEOUT_SEC` 约束。

**REQ-V7-CLI-004**  
IF server 连接失败或调用失败，THEN THE SYSTEM SHALL 返回可读错误并写入 audit，不得拖垮整个 Agent Run（该次 tool 失败即可）。

**REQ-V7-CLI-005**  
THE SYSTEM SHALL 在 mock 模式下提供本地假 Server，至少暴露 1 个 tool（如 `echo` 或 `add`），供 CI 验证桥接。

---

### 3.3 API / UI

**REQ-V7-API-001**  
THE SYSTEM SHALL 提供 API：列出 MCP servers 与连接状态、列出已桥接 tools、可选 reload 配置。

**REQ-V7-UI-001**  
THE SYSTEM SHALL 提供前端页或 Settings 区块 `/mcp`：展示 server 状态与工具目录（只读为主）；写操作遵循现有 admin/API Key 门禁。

**REQ-V7-UI-002**  
TopBar SHALL 增加 MCP 导航入口（或挂在 Settings 下；推荐独立 `/mcp`）。

---

### 3.4 MCP Server（P1）

**REQ-V7-SRV-001**  
THE SYSTEM SHALL 提供可选进程入口（如 `python -m server.mcp_server`），以 stdio 对外提供至少：`knowledge_search`、`dataset_schema`（只读）。

**REQ-V7-SRV-002**  
IF MCP Server 启用，THEN THE SYSTEM SHALL 不在默认路径暴露写操作或任意代码执行。

---

## 4. 非功能

**REQ-V7-NFR-001**  
默认 `MCP_ENABLED=false`，保证现有 Demo / `pytest` 无 MCP 依赖时行为不变。

**REQ-V7-NFR-002**  
`pytest` 在 mock MCP 下必须覆盖：list tools、call tool、桥接到 registry。

**REQ-V7-NFR-003**  
依赖写入 `requirements.txt`（如官方/社区 MCP Python SDK）；版本需在 README 注明。

---

## 5. 验收标准

1. `MCP_ENABLED=true` + mock server：Agent/API 可见桥接 tool 并可成功调用。  
2. `MCP_ENABLED=false`：无 MCP 工具，现有用例全绿。  
3. `/mcp` 页可看到 server 状态与工具列表。  
4. （P1）`python -m server.mcp_server` 可被 MCP 客户端列出只读 tools。  
5. 失败路径有明确错误，不 500 拖垮 Run。

---

## 6. 待确认决策

| # | 决策项 | 建议默认 |
|---|--------|----------|
| D1 | 下一阶段是否做 **MCP（本文件）**？ | **是** |
| D2 | 优先 Client 还是 Server？ | **Client 为主；Server 为 P1** |
| D3 | 传输 | **stdio 必需**；SSE 可选 P1 |
| D4 | Python SDK | **官方 `mcp` SDK**（若安装受阻可自研 JSON-RPC 最小子集） |
| D5 | 配置格式 | **`storage/mcp_servers.json`**（gitignore 样例放 `mcp_servers.example.json`） |
| D6 | 是否同期 Multi-Agent？ | **否**（V8） |

---

## 7. 确认方式

请回复：

- **`确认需求`** — 按 D1–D6 建议默认锁定，进入 `design.md` / `tasks.md`  
- **`确认需求：…`** — 修改决策（例如先做 Multi-Agent、或 Server 优先）  

**未确认前不编写 design 以外的业务代码；未回复「开始执行」前不改实现。**
