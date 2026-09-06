# DataMind Agent — V2 Requirements

> 产品：DataMind Agent  
> 基线：V1 MVP（已实现）见 `specs/requirements.md`  
> 本阶段：**V2 — Agent 强化 + 数据源扩展起步**  
> 语法：EARS  
> 状态：待确认

---

## 1. 阶段目标

在 V1「能跑通销售下降 Demo」之上，达到：

1. **Supervisor 显式调度**：不再是单一线性 Runtime 硬编码，而是由 Supervisor 决定下一步调用哪个 Specialized Agent / Tool。  
2. **真正的 Tool Calling**：LLM 从工具清单中选择并调用（schema / preview / python / sql / statistics / anomaly / chart）。  
3. **SQLite 数据源（V2 数据接入第一步）**：除上传文件外，可注册本地 SQLite 库表为 Dataset。  
4. **可运营性**：Run 成本（Token/耗时）可见、可取消、对话 Memory 更可靠。  
5. **体验闭环**：历史 Run 回看、Evidence 可点选、报告可导出 PDF。

**非目标（本阶段不做）**：MySQL/PostgreSQL 远程库、Docker 级 Sandbox、Evaluation Dashboard、多用户 RBAC、RAG/MCP。

---

## 2. 范围

### 2.1 In Scope（V2）

| 模块 | 内容 |
|------|------|
| Supervisor | 调度 Planner / Python / SQL / Analysis / Insight / Report |
| Tool Calling | 统一 Tool Schema + LLM function/tool calling |
| SQL Tool | 对文件 Dataset 用 DuckDB SQL；对 SQLite 源执行只读 SQL |
| Data Source | 注册 SQLite 文件路径 + 选择表 → Dataset |
| Memory | LLM 辅助更新对话 filters/context |
| Observability | Token/Latency/Cost 汇总；取消 Run |
| UX | Run 历史、Evidence 列表点选、报告 PDF 导出 |
| Hardening | RUN_TIMEOUT 强制中断；结构化日志 |

### 2.2 Out of Scope（→ V3/V4/V5）

- MySQL / PostgreSQL 连接器  
- 容器/gVisor Sandbox  
- Agent Evaluation 指标体系与面板  
- 多用户、权限、审计  
- RAG / MCP / Web Search  

---

## 3. 功能需求

### 3.1 Supervisor Agent

**REQ-V2-SUP-001**  
WHEN 用户发起分析 Run，THE SYSTEM SHALL 由 Supervisor Agent 管理状态机，并在每一步选择下一动作（plan / call_tool / analyze / replan / insight / report / finish）。

**REQ-V2-SUP-002**  
WHEN Supervisor 选择下一动作，THE SYSTEM SHALL 将决策写入 Agent Trace（含理由摘要）。

**REQ-V2-SUP-003**  
IF 步数达到 `MAX_AGENT_STEPS` 或超过 `RUN_TIMEOUT_SEC`，THEN THE SYSTEM SHALL 强制结束 Run，并返回已有部分结论与 Trace。

---

### 3.2 Tool Calling

**REQ-V2-TC-001**  
THE SYSTEM SHALL 向 LLM 暴露统一工具清单，至少包含：`dataset_schema`、`dataset_preview`、`python_execute`、`sql_query`、`statistics`、`anomaly_detection`、`generate_chart`。

**REQ-V2-TC-002**  
WHEN LLM 发出 tool call，THE SYSTEM SHALL 校验参数、执行对应工具，并将真实结果返回对话/状态，禁止跳过执行直接编造工具输出。

**REQ-V2-TC-003**  
WHEN 工具执行失败，THE SYSTEM SHALL 将错误返回给 Agent，并允许 Reflection 后重试（受 `MAX_TOOL_RETRIES` 限制）。

**REQ-V2-TC-004**  
THE SYSTEM SHALL 持久化每次 tool call（名称、参数、成功与否、耗时、结果摘要）。

---

### 3.3 SQL Tool & SQLite Data Source

**REQ-V2-SQL-001**  
WHEN Dataset 来源于上传的 CSV/Excel，THE SYSTEM SHALL 支持通过 DuckDB 对该表执行只读 SQL（`sql_query`）。

**REQ-V2-SQL-002**  
WHEN 用户注册本地 SQLite 文件并选择表，THE SYSTEM SHALL 创建 Dataset，并完成 Profiler（或等价 schema 分析）。

**REQ-V2-SQL-003**  
WHEN Dataset 来源于 SQLite，THE SYSTEM SHALL 允许 `sql_query` 对该库/表执行只读查询（禁止 DROP/DELETE/UPDATE/INSERT/ALTER 等写操作）。

**REQ-V2-SQL-004**  
IF SQL 含写操作或多语句危险模式，THEN THE SYSTEM SHALL 拒绝执行并返回明确错误。

---

### 3.4 Memory

**REQ-V2-MM-001**  
WHEN 用户发送追问，THE SYSTEM SHALL 使用 LLM（或规则+LLM）更新 `conversations.context_json` 中的 filters（时间、地区、商品、客户等）。

**REQ-V2-MM-002**  
WHEN 后续规划或生成代码/SQL，THE SYSTEM SHALL 注入最新 Memory filters。

**REQ-V2-MM-003**  
WHEN 用户显式要求重置范围（如「看全部地区」），THE SYSTEM SHALL 清除对应 filter。

---

### 3.5 Cost / Cancel / Logging

**REQ-V2-OBS-001**  
WHEN Agent Run 结束，THE SYSTEM SHALL 汇总并展示：input_tokens、output_tokens、latency_ms、估算 cost（若可配置单价）。

**REQ-V2-OBS-002**  
WHEN 用户请求取消进行中的 Run，THE SYSTEM SHALL 尽快停止后续步骤，将 status 标为 `cancelled`，并保留已产生 Trace。

**REQ-V2-OBS-003**  
THE SYSTEM SHALL 输出结构化运行日志（run_id、step、tool、latency、error），便于本地排查。

---

### 3.6 UX / Report

**REQ-V2-UX-001**  
WHEN 用户打开某次历史 Agent Run，THE SYSTEM SHALL 可回看 Trace、Charts、Insights、Report、Evidences。

**REQ-V2-UX-002**  
WHEN 用户在结论或 Evidence 列表中点选一条证据，THE SYSTEM SHALL 展示代码/SQL 与执行结果预览。

**REQ-V2-UX-003**  
WHEN 用户请求导出报告，THE SYSTEM SHALL 提供当前 Run 的 PDF 下载（由 Markdown 渲染）。

**REQ-V2-UX-004**  
THE SYSTEM SHALL 在分析进行中展示可取消按钮与阶段性进度（沿用并增强 SSE）。

---

## 4. 非功能需求

**REQ-V2-NFR-001**  
THE SYSTEM SHALL 保持「数值结论必须来自工具真实执行」的 V1 原则。

**REQ-V2-NFR-002**  
SQL 与 Python 执行仍须受超时与安全策略约束；SQLite/DuckDB 默认只读。

**REQ-V2-NFR-003**  
V2 默认仍使用 SQLite 业务库 + 本地文件存储；不强制切换 PostgreSQL。

**REQ-V2-NFR-004**  
新增模块须有基础单测：SQL 写操作拒绝、SQLite Dataset 注册、Supervisor 步数上限。

---

## 5. 验收场景

**REQ-V2-DEMO-001**  
WHEN 用户对 `sales.csv` 提问「为什么 8 月销售下降？」，THE SYSTEM SHALL 在 Trace 中可见 Supervisor 调度与至少一次非 Python 的工具调用（如 `sql_query` 或 `statistics`/`anomaly_detection`），并完成下钻与报告。

**REQ-V2-DEMO-002**  
WHEN 用户注册样例 SQLite（可由 sales 导入生成），THE SYSTEM SHALL 能对该源完成自然语言分析（至少趋势 + 分组聚合）。

**REQ-V2-DEMO-003**  
WHEN 用户在分析中途取消，THE SYSTEM SHALL 停止后续 LLM/工具调用且 UI 显示 cancelled。

**REQ-V2-DEMO-004**  
WHEN 分析完成，THE SYSTEM SHALL 可导出 PDF 报告，并可从历史 Run 回看 Evidence。

---

## 6. 已确认决策

> 状态：**已确认**（按推荐方案）  
> 确认时间：2026-09-03

| # | 项 | 结论 |
|---|----|------|
| 1 | Supervisor | 自研：在现有 State Machine 上增加 Supervisor 决策节点（LLM JSON 决策），不上 LangGraph |
| 2 | Tool Calling | OpenAI-compatible `tools` / `tool_calls`；不支持时 fallback JSON 选工具 |
| 3 | SQL 引擎 | 文件 Dataset → **DuckDB**；SQLite 源 → **只读 sqlite3 / DuckDB attach** |
| 4 | PDF | 服务端 Markdown→PDF，优先少依赖方案 |
| 5 | Cost | `.env` 配置每 1K token 单价；无配置则只显示 tokens |
| 6 | Cancel | 进程内协作取消（Event / run 状态），不做分布式 |

---

## 7. 优先级

| 优先级 | 需求 |
|--------|------|
| P0 | SUP、TC、SQL-001/003/004、MM-001/002、OBS-001/002、UX-001/002/004、DEMO-001/003、NFR |
| P1 | SQL-002、DEMO-002、UX-003 PDF、OBS-003、MM-003 |
| P2 | Cost 精确计费展示美化、多表 SQLite |

---

## 8. 下一步

需求已确认 → 见 `specs/v2/design.md` / `specs/v2/tasks.md`。

**仅当你明确回复「开始执行」后，才可修改业务代码。**
