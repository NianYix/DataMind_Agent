# DataMind Agent — V5 Architecture Design

> 对应：`specs/v5/requirements.md`（**已确认**，D1–D6 锁定）  
> 前置：UI Optimize 已完成（暗色 Token / AppShell）  
> 状态：待审阅  
> 非目标：RAG / MCP / SSO / 行级权限

---

## 1. 目标

在现有 Agent + 暗色工作台之上增加企业切片：

```text
Auth (JWT, optional)
   │
DataSource (MySQL/PG) ──► Dataset(source_type=mysql|postgresql)
   │                              │
Prompt Store (active version)     ▼
   │                         SQL Tool (readonly + remote exec)
   ▼
Agent Runtime ◄── http_request / web_search(opt)
   │
Audit + Metrics
```

**兼容**：`AUTH_ENABLED=false`（默认）时行为与 V4 一致（可选 `APP_API_KEY`）。

---

## 2. 配置增量

`server/core/config.py` + `.env.example`：

| 键 | 默认 | 说明 |
|----|------|------|
| `AUTH_ENABLED` | `false` | 多用户总开关 |
| `JWT_SECRET` | 随机/开发默认 | HS256 密钥 |
| `JWT_EXPIRE_MIN` | `10080` | 7 天 |
| `SEED_ADMIN_USER` / `SEED_ADMIN_PASSWORD` | `admin` / `admin` | 仅 AUTH 开启且无用户时种子 |
| `HTTP_URL_ALLOWLIST` | `https://httpbin.org/,https://api.github.com/` | 逗号分隔前缀 |
| `HTTP_MAX_RESPONSE_BYTES` | `65536` | 响应截断 |
| `WEB_SEARCH_ENABLED` | `false` | 注册 web_search |
| `DB_CONNECT_TIMEOUT_SEC` | `8` | 外部库连接超时 |

Settings UI 可热更新：`http_url_allowlist`、`web_search_enabled`、`http_max_response_bytes`（写入 `settings.json` HOT_FIELDS）。

---

## 3. 数据模型

### 3.1 `data_sources`

| 字段 | 类型 | 说明 |
|------|------|------|
| id | uuid PK | |
| workspace_id | FK | |
| name | str | |
| db_type | `mysql` \| `postgresql` | |
| host / port / database / username | | |
| password_enc | str | Fernet 或简单 XOR+base64 **开发级**加密；响应永不回明文 |
| ssl | bool | |
| created_by | user_id 可空 | |
| created_at | | |

### 3.2 Dataset 扩展

- `source_type`: 新增 `mysql` / `postgresql`  
- `connection_id`: FK → `data_sources.id`（可空；文件源为空）  
- `table_name`: 远程表/视图名  
- `file_path`: 远程源可存占位路径如 `remote://{connection_id}/{table}`（工具层用 connection_id 解析）

SQLite migrate：`ALTER TABLE datasets ADD COLUMN connection_id ...`（仿 V2 migrate）。

### 3.3 `prompt_templates`

| 字段 | 说明 |
|------|------|
| id | uuid |
| name | 如 `system_analyst` |
| role | `system` |
| content | text |
| version | int |
| is_active | bool |
| created_at / created_by | |

约束：同 `name` 至多一个 `is_active=true`（应用层保证）。

### 3.4 `users` / `workspace_members`

```text
users: id, username, email?, password_hash, global_role(admin|analyst), created_at
workspace_members: id, workspace_id, user_id, role(admin|analyst), unique(workspace_id,user_id)
```

---

## 4. Auth

### 4.1 库

- `PyJWT`、`passlib[bcrypt]`（或 `bcrypt` 直接）

### 4.2 流程

```text
POST /api/auth/login {username,password} → {access_token, token_type, user}
GET  /api/auth/me  Authorization: Bearer …
POST /api/auth/register  （AUTH 开启且允许；首期可仅 admin 创建用户，或开放注册 analyst）
```

### 4.3 依赖

```python
def get_current_user_optional(...)  # AUTH off → None
def require_user(...)               # AUTH on → 401 if missing
def require_admin(...)              # JWT admin OR valid APP_API_KEY
```

**门禁映射**

| 操作 | AUTH off | AUTH on |
|------|----------|---------|
| 读分析/数据集 | 开放 | 须登录 + workspace 成员 |
| Settings PUT / Prompt 写 / DataSource 凭证写 / Eval POST | API Key 或开放 | **admin** 或 API Key |
| 登录/健康检查 | 开放 | 开放 |

Workspace 列表：AUTH on 时仅返回成员工作区；种子管理员自动加入默认 workspace。

---

## 5. Data Source 服务

`server/services/datasource_service.py`  
`connectors/mysql.py` / `connectors/postgres.py`（或 `data/connectors/`）

统一接口：

```python
class DbConnector(Protocol):
    def test_connection(cfg) -> dict  # {ok, error?, server_version?}
    def list_tables(cfg) -> list[str]
    def profile_table(cfg, table, sample_rows) -> dict  # 复用 profiler 字段形状
    def execute_readonly(cfg, sql, max_rows) -> dict
```

实现：

- PostgreSQL：`psycopg[binary]` 或 `psycopg2-binary`  
- MySQL：`pymysql`  

**无真实库时**：`connectors/mock.py` 实现同接口，供 pytest（D6）。

SQL 路径：

1. `validate_readonly_sql`（现有）  
2. 若 `source_type in {mysql,postgresql}` → connector.execute_readonly  
3. 否则 → 现有 DuckDB 文件/SQLite 路径  

`tools/sql_query.py` / `registry` / `statistics._load_df`：对远程源，抽样 `SELECT * LIMIT N` 进 pandas（受 `sql_max_rows` / profile sample 限制），禁止全表无界拉取。

---

## 6. Prompt Management

`server/services/prompt_service.py`

- `list_prompts` / `create_version` / `activate(name, version)` / `get_active(name)`  
- Agent：`agent/lc/nodes.py`（及 legacy 若仍用）在 understand/plan 构建 messages 时注入 `get_active("system_analyst")` 或等价名；无则用现有硬编码默认。

审计：`prompt_create` / `prompt_activate`。

---

## 7. Tools

### 7.1 `http_request`

```text
args: method(GET|POST), url, headers?, body?, timeout?
checks: method allow; url startswith any allowlist prefix
exec: httpx / urllib
result: {status, headers_subset, body_truncated, truncated:bool}
```

注册进 `tools/registry.py` + LangChain StructuredTool。

### 7.2 `web_search`（骨架）

- 仅当 `WEB_SEARCH_ENABLED`  
- 首期实现：调用可配置 Search API URL（若未配置则返回明确 “not configured”），或固定 mock 结果在测试中  
- 生产级搜索引擎对接不强制本切片完成

审计：`tool_http` / `tool_web_search`。

---

## 8. API 路由

| Method | Path | 鉴权 |
|--------|------|------|
| POST | `/api/auth/login` | 无 |
| POST | `/api/auth/register` | AUTH on；策略见上 |
| GET | `/api/auth/me` | Bearer |
| GET/POST | `/api/data-sources` | 写：admin |
| POST | `/api/data-sources/{id}/test` | 成员/admin |
| GET | `/api/data-sources/{id}/tables` | 成员 |
| POST | `/api/data-sources/{id}/datasets` | 成员；body: `{table_name, name?}` |
| GET/POST | `/api/prompts` | 写：admin |
| POST | `/api/prompts/{name}/activate` | admin |
| GET/POST/DELETE | `/api/workspaces/{id}/members` | workspace admin / global admin |

现有 workspaces/datasets 路由：AUTH on 时加成员校验。

---

## 9. 前端（沿用暗色 AppShell）

| 页面 | 路径 | 内容 |
|------|------|------|
| Data Sources | `/data-sources` | CRUD 表单、测试连接、选表注册 Dataset |
| Prompts | `/prompts` | 列表、新建版本、激活 |
| Auth | `/login` | 登录；TopBar 显示用户 / Logout |
| Members | `/settings` 内嵌或 `/members` | 简单成员列表（P1） |

TopBar 增加 Data Sources / Prompts 导航。  
AgentPanel：外部库 Dataset 与文件 Dataset 同一列表（已有 `source_type` 展示）。

`lib/api.ts`：auth header 从 `localStorage.token` 注入；AUTH off 时不送。

---

## 10. 依赖

`requirements.txt` 增加：

```text
PyJWT
passlib[bcrypt]
bcrypt
httpx
pymysql
psycopg[binary]
cryptography  # 可选 Fernet
```

---

## 11. 测试

| 测项 | 方式 |
|------|------|
| SQL guard + remote mock execute | unit |
| http_request allow/deny | unit |
| prompt activate 单 active | unit + db |
| auth JWT + require_admin | TestClient |
| AUTH off 回归 evaluation mock | 现有 test_evaluation |
| datasource mock list/register | TestClient |

---

## 12. 实施顺序

```text
V5-0  Config + ORM + migrate
V5-1  Auth JWT + seed + gate
V5-2  Connectors + DataSource API + sql_query remote
V5-3  Prompt service + Agent 注入
V5-4  http_request + web_search stub
V5-5  Frontend pages + api.ts
V5-6  Tests + README
```

---

## 13. 风险

| 风险 | 缓解 |
|------|------|
| 驱动安装失败 | 可选依赖 + mock 测试；README 说明 |
| 密码存储 | 脱敏 API + 开发级加密；文档标明非 HSM |
| AUTH 破坏 Demo | 默认关闭 |
| 远程全表扫描 | LIMIT / max_rows / timeout |

---

## 14. 确认方式

回复 **`确认设计`** 或 **`开始执行`**（后者视为设计与任务锁定并开工）。
