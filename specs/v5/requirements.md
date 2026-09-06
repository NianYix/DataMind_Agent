# DataMind Agent — V5 Requirements

> 基线：V1–V4 + LangChain/LangGraph Runtime（已实现）  
> 本阶段：**V5 — 企业级能力（第一切片）**  
> 语法：EARS  
> 状态：**已确认**（用户确认需求；D1–D6 锁定）  
> 执行顺序：UI Optimize 已完成 → 本阶段  
> 前置：`specs/ui_optimize/`（已完成）

---

## 0. 阶段定位

| 已完成 | 本阶段 | 明确另开 |
|--------|--------|----------|
| V1–V4 + UI Optimize | **外部库连接 + Prompt 管理 + 扩展 Tool + 轻量多用户** | 完整 RAG / MCP |
| | | 行级数据权限、实时协作 |

### 已锁定决策（用户确认意向）

| # | 决策 | 取值 |
|---|------|------|
| D1 | V5 切片范围 | 连接器 + Prompt + HTTP Tool + 轻量多用户 |
| D2 | Web Search | 可选开关，默认关（骨架） |
| D3 | 鉴权 | JWT Bearer |
| D4 | UI_Optimize | **先做**（本文件之后执行） |
| D5 | RAG / MCP | 不纳入 V5 |
| D6 | DB 验收 | 允许 mock 连接层 + 契约测试 |

`PROJECT_DESIGN` §37 列出的企业能力全集过大，本切片目标是：**把「文件上传」升级为「可连企业库」，并把 Agent 工具与配置管理推到可演示的平台级**，为后续 RAG/MCP/完整 RBAC 打底。

---

## 1. 阶段目标

1. **外部数据源**：支持只读连接 **MySQL**、**PostgreSQL**，注册为 Dataset，供 SQL Tool / Profiler 使用。  
2. **Prompt Management**：系统 Prompt / 分析策略可版本化配置与切换（非仅改代码）。  
3. **扩展 Tool**：增加受控 **HTTP API Tool**；可选 **Web Search Tool**（开关 + 白名单/配额）。  
4. **轻量多用户**：User + Workspace 成员 + 角色（`admin` / `analyst`）；敏感写操作按角色鉴权（在现有 API Key 之上）。  
5. **审计扩展**：数据源连接、Prompt 变更、外部 Tool 调用写入 `audit_events`。

**非目标（V5 本切片不做）**：向量 RAG、MCP Server/Client、完整 RBAC/SSO/OIDC、行级/列级数据权限、团队实时协作、远程对象存储、生产级密钥保险箱（可用环境变量 + 脱敏展示）。UI 皮肤以 UI Optimize 成果为基线，V5 仅增量页面套用同一 Token。

---

## 2. 范围

### 2.1 In Scope

| 模块 | 内容 |
|------|------|
| Data Source | MySQL / PostgreSQL 连接配置、测试连接、选表/视图注册为 Dataset |
| Prompt Mgmt | 命名 Prompt 模板、版本、激活版本；Agent 启动时加载 |
| Tools | `http_request`（URL 白名单）；可选 `web_search`（feature flag） |
| Auth Lite | `users`、`workspace_members`、登录签发 token（或 session）；角色门禁 |
| Audit | 连接/Prompt/外部调用审计 |
| UI | 数据源页、Prompt 管理页、用户/成员简单管理；分析台可选数据源 |

### 2.2 Out of Scope（→ V5.1 / V6 / 另开）

| 项 | 去向 |
|----|------|
| RAG（文档入库 + 检索增强） | V5.1 或 V6 |
| MCP | 另开阶段 |
| SSO / OIDC / SCIM | 更后 |
| 行级数据权限 | 更后 |
| UI Optimize | **前置阶段**（`specs/ui_optimize/`），不在本切片重复 |

---

## 3. 功能需求

### 3.1 外部数据源

**REQ-V5-DS-001**  
WHEN 管理员创建数据源，THE SYSTEM SHALL 支持类型 `mysql` 与 `postgresql`，字段至少含：name、host、port、database、user、password（存储须脱敏展示）、可选 SSL 开关。

**REQ-V5-DS-002**  
WHEN 用户请求「测试连接」，THE SYSTEM SHALL 在超时内验证连通性并返回成功或可读错误；不得在错误中回显明文密码。

**REQ-V5-DS-003**  
WHEN 用户从数据源选择表或视图注册 Dataset，THE SYSTEM SHALL 创建 `source_type` 为 `mysql`/`postgresql` 的 Dataset，并记录 `connection_id` + `table_name`（或等价元数据）。

**REQ-V5-DS-004**  
WHEN Agent 对外部库 Dataset 调用 SQL Tool，THE SYSTEM SHALL 仅允许只读查询（沿用/扩展现有 SQL Guard），并施加行数与超时上限。

**REQ-V5-DS-005**  
IF 数据源连接失败或只读校验失败，THEN THE SYSTEM SHALL 将失败写入审计并不泄漏凭证。

---

### 3.2 Prompt Management

**REQ-V5-PM-001**  
THE SYSTEM SHALL 允许创建/更新 Prompt 模板（至少：`id`/`name`、`role` 如 system、`content`、`version`、`is_active`）。

**REQ-V5-PM-002**  
WHEN 激活某版本，THE SYSTEM SHALL 保证同名模板至多一个 active 版本，并使后续 Agent Run 使用该内容。

**REQ-V5-PM-003**  
WHEN Prompt 被创建或激活变更，THE SYSTEM SHALL 记录 audit（操作者、模板名、版本）。

**REQ-V5-PM-004**  
IF 无任何 active Prompt，THEN THE SYSTEM SHALL 回退到内置默认 Prompt（与当前行为兼容）。

---

### 3.3 扩展 Tool

**REQ-V5-TOOL-001**  
THE SYSTEM SHALL 向 Agent 注册 `http_request` Tool：方法限于 GET/POST，URL 必须匹配可配置白名单前缀；响应体截断到配置上限。

**REQ-V5-TOOL-002**  
WHEN `WEB_SEARCH_ENABLED=true`（或 Settings 等价项），THE SYSTEM SHALL 注册 `web_search` Tool；否则不暴露该 Tool。

**REQ-V5-TOOL-003**  
WHEN 外部 Tool 执行，THE SYSTEM SHALL 记录 tool_calls + audit，并计入现有 Metrics / Evaluation 的工具成功率统计。

**REQ-V5-TOOL-004**  
IF URL 不在白名单或方法不允许，THEN THE SYSTEM SHALL 拒绝调用并返回明确错误（不得静默成功）。

---

### 3.4 轻量多用户与权限

**REQ-V5-AUTH-001**  
THE SYSTEM SHALL 支持用户注册或种子管理员（至少：email/username、password hash、role 默认 `analyst`）。

**REQ-V5-AUTH-002**  
WHEN 用户登录成功，THE SYSTEM SHALL 签发可校验的访问令牌（JWT 或服务端 session），后续 API 可携带该令牌。

**REQ-V5-AUTH-003**  
WHEN 请求修改 Settings、Prompt、数据源凭证或启动 Evaluation，THE SYSTEM SHALL 要求 `admin` 角色（或现有 `APP_API_KEY` 作为兼容后门，须在文档标明）。

**REQ-V5-AUTH-004**  
WHEN 用户加入 Workspace，THE SYSTEM SHALL 支持成员表（user_id、workspace_id、role）；分析读写默认限于其成员 Workspace。

**REQ-V5-AUTH-005**  
IF 未开启多用户模式（配置开关），THEN THE SYSTEM SHALL 保持 V4 单租户行为（仅可选 API Key），以保证本地 Demo 零摩擦。

---

### 3.5 API / UI

**REQ-V5-API-001**  
THE SYSTEM SHALL 提供数据源 CRUD / 测试连接 / 注册表 API（路径前缀建议 `/api/data-sources`）。

**REQ-V5-API-002**  
THE SYSTEM SHALL 提供 Prompt 模板列表、创建版本、激活 API（`/api/prompts`）。

**REQ-V5-API-003**  
THE SYSTEM SHALL 提供 auth：注册（可选）、登录、当前用户、Workspace 成员管理 API。

**REQ-V5-UI-001**  
THE SYSTEM SHALL 提供前端页面或区块：Data Sources、Prompts、（简单）Users/Members；导航可从分析台进入。

**REQ-V5-UI-002**  
WHEN 创建分析会话，THE SYSTEM SHALL 允许选择文件 Dataset 或外部库 Dataset。

---

## 4. 非功能

**REQ-V5-NFR-001**  
凭证不得写入前端日志或 Trace 明文；API 响应中密码仅可显示掩码。

**REQ-V5-NFR-002**  
外部 DB 与 HTTP 调用必须有超时；默认拒绝非白名单出站。

**REQ-V5-NFR-003**  
未启用多用户时，现有 `pytest` 与 `python -m evaluation --mode mock` 行为不得被破坏。

**REQ-V5-NFR-004**  
新增依赖须写入 `requirements.txt`；MySQL/PG 驱动按需可选安装说明写入 README。

---

## 5. 验收标准（阶段完成定义）

1. 可配置并测试 MySQL 或 PostgreSQL 连接，并将一张表注册为 Dataset 完成一次自然语言 SQL 分析（可用本地 Docker 库）。  
2. 可在 UI/API 切换 Prompt 版本并在后续 Run 中生效。  
3. `http_request` 在白名单内可被 Agent 调用；白名单外被拒绝。  
4. 多用户开关打开时：非 admin 无法改 Settings/数据源；关闭时 Demo 路径与 V4 一致。  
5. `pytest -q` 全绿（含数据源/SQL guard/Prompt/auth 的单元或集成 mock 测）。

---

## 6. 决策（已锁定）

| # | 决策项 | 取值 |
|---|--------|------|
| D1 | V5 切片范围 | 连接器 + Prompt + HTTP Tool + 轻量多用户 |
| D2 | Web Search | 可选开关，默认关（骨架） |
| D3 | 鉴权 | JWT Bearer |
| D4 | UI_Optimize | 前置已完成 |
| D5 | RAG / MCP | 不纳入 V5 |
| D6 | DB 验收 | 允许 mock 连接层 + 契约测试 |

---

## 7. 确认方式

需求已确认。请审阅 `design.md` / `tasks.md` 后回复：

- **`确认设计`** — 锁定方案  
- **`开始执行`** — 锁定并开工

**未回复「开始执行」前不修改 V5 业务代码。**
