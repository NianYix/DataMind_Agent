# DataMind Agent — V5 Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 状态：**已执行**

---

## Phase V5-0 — 基础 `[P0]`

### T0.1 Config / deps
- [x] `.env.example` + Settings：`AUTH_ENABLED`、JWT、allowlist、`WEB_SEARCH_ENABLED`
- [x] `requirements.txt`：PyJWT、passlib/bcrypt、httpx、pymysql、psycopg
- **验收**：配置可读

### T0.2 ORM
- [x] `DataSource`、`PromptTemplate`、`User`、`WorkspaceMember`
- [x] Dataset.`connection_id`；sqlite migrate
- **验收**：`init_db` 建表

---

## Phase V5-1 — Auth `[P0]`

### T1.1 JWT + seed
- [x] login / me / register
- [x] `require_admin` = JWT admin ∨ APP_API_KEY
- [x] AUTH off 旁路
- **验收**：JWT roundtrip + 默认 Demo 无阻

### T1.2 Workspace 成员门禁
- [x] 成员表 + 种子 admin 绑定默认 workspace
- **验收**：结构就绪（列表过滤可后续收紧）

---

## Phase V5-2 — Data Sources `[P0]`

### T2.1 Connectors
- [x] mysql / postgresql / mock 统一接口
- **验收**：mock 单测绿

### T2.2 API + SQL 路径
- [x] `/api/data-sources*` CRUD / test / tables / register dataset
- [x] `sql_query` + registry 支持 remote source_type
- [x] 密码脱敏 + audit
- **验收**：mock 注册 Dataset

---

## Phase V5-3 — Prompts `[P0]`

### T3.1 Prompt API + Agent 注入
- [x] CRUD 版本 / activate
- [x] LangChain Planner 加载 active system prompt
- **验收**：activate 单测

---

## Phase V5-4 — Tools `[P0]`

### T4.1 http_request
- [x] 白名单、GET/POST、截断、registry + LC tool
- **验收**：deny 单测

### T4.2 web_search stub
- [x] feature flag；默认不注册
- **验收**：默认 off

---

## Phase V5-5 — Frontend `[P1]`

### T5.1 页面
- [x] `/login`、`/data-sources`、`/prompts`
- [x] `api.ts` Bearer；TopBar 导航
- **验收**：`tsc` 通过

---

## Phase V5-6 — 文档与回归 `[P0]`

### T6.1 README
- [x] V5 用法
- **验收**：文档可复现 mock 路径

### T6.2 pytest
- [x] `pytest -q` 全绿（26 passed）
- **验收**：含 `tests/test_v5.py`

---

## 确认与执行

已收到 **「开始执行」** 并完成 V5 切片。
