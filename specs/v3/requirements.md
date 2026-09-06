# DataMind Agent — V3 Requirements

> 产品：DataMind Agent  
> 基线：V1 + V2（已实现）见 `specs/`、`specs/v2/`  
> 本阶段：**V3 — 工程化（Demo → Production-ready）**  
> 语法：EARS  
> 状态：待确认

---

## 1. 阶段目标

V2 已具备 Supervisor / Tool Calling / SQL / Cancel / Cost / PDF。V3 目标是把系统从「可演示」推进到「可稳定运行、可配置、可审计」：

1. **Sandbox 工程化**：Python / SQL 执行路径统一加固（超时、只读、资源边界、审计）。  
2. **可观测与审计**：结构化日志落盘/落库，Run/Tool 可追溯导出。  
3. **Settings 可配置**：模型与运行参数可在 UI/API 调整（密钥脱敏），无需改代码。  
4. **轻量访问控制**：对敏感写操作增加 API Key（单租户，非完整 RBAC）。  
5. **大数据友好**：较大 CSV 优先走 DuckDB 路径，降低 Pandas 全量加载风险。  
6. **运维指标**：聚合 Run 成功率、平均耗时、Token、工具成功率（为 V4 Evaluation 打底）。

**非目标（本阶段不做）**：Docker/gVisor 容器沙箱、完整多用户 RBAC、Evaluation 评分面板（V4）、远程 MySQL/PostgreSQL 业务数据源、RAG/MCP。

---

## 2. 与 V2 的边界（已有 vs 本阶段新增）

| 能力 | V2 现状 | V3 增量 |
|------|---------|---------|
| Retry / Timeout / Cancel / Cost | 已有 | 配置可热更新；审计记录完整化 |
| SQL 只读校验 / DuckDB | 已有 | 正式 SQL Sandbox 模块 + 统一执行审计 |
| Python 子进程 + AST 白名单 | 已有 | 资源限制（尽力而为）、执行档案、失败分类 |
| 日志 | 控制台为主 | 文件轮转 + `audit_events` 表 |
| Settings | 仅 `.env` | Settings API + 前端设置页 |
| Permission | 无 | 可选 `API_KEY` 保护写接口 |
| Evaluation | 无 | 仅提供聚合 Metrics API（面板留给 V4） |

---

## 3. 范围

### 3.1 In Scope（V3）

| 模块 | 内容 |
|------|------|
| Python Sandbox Hardening | 执行档案、超时/失败分类、可选内存限制、禁止危险能力保持 |
| SQL Sandbox | 统一入口、只读策略、行数/耗时上限、审计 |
| Audit & Logging | `audit_events` + 滚动日志文件 |
| Settings | LLM / Agent 限额 / 单价 的读写（密钥脱敏） |
| Permission (lite) | `X-API-Key` 保护 Settings 修改与可选危险操作 |
| Large Data Path | 超过阈值时 Profile/Preview/SQL 优先 DuckDB |
| Ops Metrics | `/api/metrics` 聚合历史 Run/Tool 指标 |
| Trace Export | 导出单次 Run 的 JSON（steps/tools/evidences） |

### 3.2 Out of Scope（→ V4 / V5）

- Evaluation Dashboard（任务集打分、幻觉率标注）  
- Docker 级隔离 Sandbox  
- 多用户、角色、数据权限、团队协作  
- 远程 MySQL / PostgreSQL 作为分析数据源  
- RAG / MCP / Web Search  

---

## 4. 功能需求

### 4.1 Python Sandbox

**REQ-V3-PY-001**  
WHEN Python 代码提交执行，THE SYSTEM SHALL 经统一 `sandbox.python` 入口执行，并记录：run_id（若有）、耗时、成功与否、错误类型。

**REQ-V3-PY-002**  
WHEN 代码违反 AST 白名单或超时，THE SYSTEM SHALL 拒绝/中断执行，并返回可分类错误码（`SECURITY` / `TIMEOUT` / `RUNTIME` / `OUTPUT`）。

**REQ-V3-PY-003**  
WHEN 配置了内存限制且运行环境支持，THE SYSTEM SHALL 尽力施加内存上限；IF 平台不支持（如部分 Windows 场景），THEN THE SYSTEM SHALL 跳过并在日志中标注 `memory_limit=unsupported`，不得导致服务崩溃。

**REQ-V3-PY-004**  
THE SYSTEM SHALL 保持禁止任意网络、任意文件写入与危险模块导入的安全基线（不低于 V2）。

---

### 4.2 SQL Sandbox

**REQ-V3-SQL-001**  
WHEN 执行 `sql_query`，THE SYSTEM SHALL 经统一 `sandbox.sql` 入口：只读校验 → 执行 → 截断结果行数 → 审计。

**REQ-V3-SQL-002**  
WHEN SQL 超过配置的执行超时或返回行数上限，THE SYSTEM SHALL 截断或中止，并返回明确错误/截断标记。

**REQ-V3-SQL-003**  
THE SYSTEM SHALL 拒绝写操作与多语句（延续 V2 `sql_guard` 策略）。

---

### 4.3 Audit & Logging

**REQ-V3-AUD-001**  
WHEN 发生 Agent Run 开始/结束、Tool 调用、Sandbox 拒绝、Settings 变更、Cancel，THE SYSTEM SHALL 写入 `audit_events`（至少含：time、event_type、run_id、payload 摘要）。

**REQ-V3-AUD-002**  
THE SYSTEM SHALL 将结构化应用日志写入可轮转日志文件（如 `storage/logs/datamind.log`）。

**REQ-V3-AUD-003**  
WHEN 用户请求导出某次 Run 的 Trace 包，THE SYSTEM SHALL 返回 JSON（run、steps、tool_calls、evidences、charts 元数据、report markdown）。

---

### 4.4 Settings

**REQ-V3-SET-001**  
THE SYSTEM SHALL 提供 Settings 读取 API：当前模型名、base_url（可显示）、api_key 脱敏、MAX_AGENT_STEPS、超时、token 单价等。

**REQ-V3-SET-002**  
WHEN 用户更新 Settings，THE SYSTEM SHALL 持久化（`.env` 或 `settings.json`），并使后续 LLM/Agent 调用尽快生效（进程内刷新缓存）。

**REQ-V3-SET-003**  
THE SYSTEM SHALL 提供前端 Settings 页，用于查看/修改上述配置（api_key 输入框写后不明文回显）。

---

### 4.5 Permission（lite）

**REQ-V3-PERM-001**  
WHEN 配置了 `APP_API_KEY`，THE SYSTEM SHALL 要求修改 Settings、导出审计敏感操作携带正确 `X-API-Key`。

**REQ-V3-PERM-002**  
IF 未配置 `APP_API_KEY`，THEN THE SYSTEM SHALL 在开发模式下允许本地无密钥访问，并在启动日志提示生产环境应配置密钥。

**REQ-V3-PERM-003**  
分析对话与数据集上传在 V3 默认可保持开放（单机场景）；权限深化留给 V5。

---

### 4.6 Large Data Path

**REQ-V3-DATA-001**  
WHEN 上传文件大小超过配置阈值（默认如 30MB）或行数探测超过阈值，THE SYSTEM SHALL 对 Profile/Preview 采用抽样或 DuckDB 路径，避免默认全量 Pandas 导致 OOM。

**REQ-V3-DATA-002**  
WHEN 使用大文件路径，THE SYSTEM SHALL 在 Dataset Profile 中标记 `engine=duckdb|sample` 以便排查。

---

### 4.7 Ops Metrics

**REQ-V3-MET-001**  
WHEN 请求 `/api/metrics`，THE SYSTEM SHALL 返回聚合指标，至少包括：Run 总数、按 status 分布、平均 latency、平均 tokens、Tool 成功率、Python/SQL 调用成功率。

**REQ-V3-MET-002**  
THE SYSTEM SHALL 在前端提供简易 Metrics 面板（数字卡片即可，非 V4 Evaluation 评分体系）。

---

## 5. 非功能需求

**REQ-V3-NFR-001**  
THE SYSTEM SHALL 保持「数值结论必须来自工具真实执行」原则。

**REQ-V3-NFR-002**  
V3 默认仍支持 SQLite 业务库；Settings/Audit 表结构变更须可自动迁移。

**REQ-V3-NFR-003**  
新增能力须有单测：SQL sandbox 拒绝写、Settings 脱敏、Metrics 聚合、Audit 写入。

**REQ-V3-NFR-004**  
文档（README）须说明：API Key、日志位置、大文件阈值、Settings 用法。

---

## 6. 验收场景

**REQ-V3-DEMO-001**  
WHEN 使用 `samples/superstore_clean.csv`（或 `sales.csv`）完成一次分析，THE SYSTEM SHALL 产生可查询的 audit 事件与可导出 Trace JSON。

**REQ-V3-DEMO-002**  
WHEN 在 Settings 修改 `MAX_AGENT_STEPS` 或模型名，THE SYSTEM SHALL 在后续 Run 中体现新配置（在 API Key 策略满足时）。

**REQ-V3-DEMO-003**  
WHEN 提交危险 Python（如 `import os`）或写 SQL，THE SYSTEM SHALL 被 Sandbox 拒绝并留下审计记录。

**REQ-V3-DEMO-004**  
WHEN 打开 Metrics 面板，THE SYSTEM SHALL 展示基于历史 Run 的聚合统计。

---

## 7. 已确认决策

> 状态：**已确认**（按推荐方案）  
> 确认时间：2026-09-04

| # | 项 | 结论 |
|---|----|------|
| 1 | Settings 存储 | `storage/settings.json` 覆盖可热更新项；密钥不进 git |
| 2 | API Key | 可选 `APP_API_KEY`；保护 Settings 写与 Trace/Audit 导出 |
| 3 | 日志 | `RotatingFileHandler` → `storage/logs/` |
| 4 | 内存限制 | Linux 尽力；Windows 标注 unsupported；不引入 Docker |
| 5 | 大文件阈值 | 默认 30MB / 或 20 万行抽样 Profile |
| 6 | Metrics | 基于 `agent_runs` / `tool_calls` SQL 聚合 |
| 7 | 前端 | 增加 `/settings` 与 Metrics；**不**按 `UI_Optimize.md` 重做分析台（UI 大改另开阶段） |

---

## 8. 优先级

| 优先级 | 需求 |
|--------|------|
| P0 | PY-001/002/004、SQL-*、AUD-001/003、SET-001/002、MET-001、DEMO-001/003、NFR |
| P1 | AUD-002、SET-003、PERM-*、MET-002、DATA-*、DEMO-002/004、PY-003 |
| P2 | 更细错误码国际化、日志检索 UI |

---

## 9. 下一步

需求已确认 → 见 `specs/v3/design.md` / `specs/v3/tasks.md`。

**仅当你明确回复「开始执行」后，才可修改业务代码。**
