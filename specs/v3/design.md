# DataMind Agent — V3 Architecture Design

> 对应需求：`specs/v3/requirements.md`（已确认）  
> 基线：V2 Runtime / Tools / 前端分析台  
> 状态：待审阅

---

## 1. 设计目标

在不重写 Agent Loop 的前提下，完成工程化闭环：

1. Sandbox 统一入口 + 错误分类 + 审计  
2. Settings 可热更新 + 可选 API Key  
3. 日志落盘 + Trace JSON 导出  
4. 大文件 DuckDB/抽样 Profile  
5. Metrics 聚合 API + 简易前端面板  

**说明**：`specs/UI_Optimize.md` 的深色工作台大改不在 V3；V3 仅增量 Settings / Metrics UI。

---

## 2. 架构增量

```text
                    Frontend (+ /settings, Metrics)
                              │
                              ▼
                         FastAPI
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
         SettingsSvc     Audit/Metrics    Agent/Chat (V2)
              │               │               │
              ▼               ▼               ▼
     settings.json      audit_events     sandbox.python
     (hot reload)       + log files      sandbox.sql
```

---

## 3. Settings

### 3.1 存储

- 路径：`storage/settings.json`（gitignore）  
- 启动：`.env` 为默认；若存在 settings.json 则覆盖可热更新字段  
- 字段示例：

```json
{
  "llm_base_url": "...",
  "llm_api_key": "...",
  "llm_model": "...",
  "max_agent_steps": 20,
  "tool_timeout_sec": 30,
  "run_timeout_sec": 300,
  "llm_input_price_per_1k": 0,
  "llm_output_price_per_1k": 0,
  "large_file_mb": 30,
  "profile_sample_rows": 200000
}
```

### 3.2 服务

`server/services/settings_service.py`：

- `get_public_settings()` → api_key 脱敏（`sk-***last4`）  
- `update_settings(patch, api_key_header)` → 写文件 + `get_settings.cache_clear()` + 重建 LLM gateway 单例  

### 3.3 API

| Method | Path | 鉴权 |
|--------|------|------|
| GET | `/api/settings` | 无（脱敏） |
| PUT | `/api/settings` | 若配置了 `APP_API_KEY` 则需 `X-API-Key` |

---

## 4. Permission（lite）

`server/core/security.py`：

```python
def require_api_key(header: str | None) -> None
```

- `APP_API_KEY` 空：开发模式放行，启动 warn  
- 保护：`PUT /settings`、`GET .../export`、可选 `GET /api/audit`  

分析上传/对话默认仍开放（单机）。

---

## 5. Sandbox 工程化

### 5.1 目录

```text
sandbox/
  python_runner.py   # 包装现有 executor + 错误分类
  sql_runner.py      # 包装 sql_query + 行数/超时
  errors.py          # SandboxError(code=SECURITY|TIMEOUT|RUNTIME|OUTPUT)
  audit_hook.py      # 写 audit_events
```

### 5.2 Python

- 继续 AST 白名单 + 子进程超时  
- 返回统一结构：`{success, code, error, error_code, duration_ms, result}`  
- 内存限制：`resource.setrlimit`（非 Windows）；Windows → log `unsupported`

### 5.3 SQL

- 强制走 `sql_guard`  
- `max_rows` / `timeout_sec` 来自 Settings  
- 结果带 `truncated: true` 标记  

`tools/registry.py` 改为调用 sandbox runners，避免双路径。

---

## 6. Audit & Logging

### 6.1 表 `audit_events`

| 字段 | 类型 |
|------|------|
| id | str PK |
| created_at | datetime |
| event_type | str（run_start/run_end/tool_call/sandbox_reject/settings_update/cancel） |
| run_id | str nullable |
| level | str |
| message | str |
| payload_json | JSON |

### 6.2 日志

`server/core/logging_setup.py`：RotatingFileHandler → `storage/logs/datamind.log`（10MB × 5）

### 6.3 Trace Export

`GET /api/agent-runs/{id}/export` → JSON bundle：

```json
{ "run": {...}, "steps": [...], "tool_calls": [...], "evidences": [...], "charts": [...], "report": "..." }
```

需 API Key（若已配置）。

---

## 7. Large Data Path

`data/profiler.py` / preview：

- 若文件 size > `large_file_mb` 或快速行数估计 > `profile_sample_rows`：  
  - DuckDB `read_csv_auto` 抽样 / `SUMMARIZE`  
  - `profile_json.engine = "duckdb_sample"`  
- 否则保持 Pandas  

上传流程在 `dataset_service` 分支调用。

---

## 8. Metrics

`GET /api/metrics`：

```json
{
  "runs_total": 12,
  "runs_by_status": {"done": 10, "error": 1, "cancelled": 1},
  "avg_latency_ms": 12345,
  "avg_input_tokens": 8000,
  "avg_output_tokens": 2000,
  "tool_success_rate": 0.94,
  "python_success_rate": 0.91,
  "sql_success_rate": 0.96
}
```

实现：SQLAlchemy 聚合查询 `agent_runs` / `tool_calls`。

前端：首页或独立区块展示数字卡片；Settings 页可同屏。

---

## 9. 前端增量

| 路由/区块 | 内容 |
|-----------|------|
| `/settings` | 表单：model、base_url、api_key、steps、timeouts、单价、API Key 输入（写操作用） |
| 分析台旁栏或顶栏 | Metrics 摘要 +「导出 Trace」按钮 |
| 导航 | 分析台 ↔ Settings |

不引入 `UI_Optimize.md` 的全量暗色重构。

---

## 10. 配置新增（`.env.example`）

```text
APP_API_KEY=
LARGE_FILE_MB=30
PROFILE_SAMPLE_ROWS=200000
LOG_DIR=./storage/logs
SETTINGS_PATH=./storage/settings.json
```

---

## 11. 迁移

`init_db` 增加 `audit_events` 表；既有 SQLite `ALTER` 兼容策略延续 V2。

---

## 12. 测试

| 用例 | 断言 |
|------|------|
| sql sandbox | DELETE 被拒 + audit |
| python sandbox | `import os` → SECURITY |
| settings | 脱敏；update 后 cache 刷新 |
| metrics | 空库返回零值结构 |
| export | JSON 含 steps |

---

## 13. 需求映射

| 需求 | 落点 |
|------|------|
| PY/SQL | `sandbox/*` + registry |
| AUD | `audit_events` + logging + export API |
| SET | settings_service + `/settings` |
| PERM | `require_api_key` |
| DATA | profiler/dataset_service 分支 |
| MET | metrics API + UI 卡片 |

---

## 14. 确认方式

请回复 **`确认设计`** 或指出修改；任务清单见 `tasks.md`。  
**「开始执行」后才改业务代码。**
