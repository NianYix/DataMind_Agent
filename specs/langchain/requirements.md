# DataMind Agent — LangChain 重构需求

> 基线：当前为 **自研 Agent State Machine**（非 LangChain / LangGraph）  
> 本阶段：**用 LangChain 生态重构 Agent 运行时**  
> 语法：EARS  
> 状态：待确认

---

## 0. 当前框架说明（现状）

| 层 | 当前选型 |
|----|----------|
| Web | Next.js + TypeScript + Tailwind + ECharts |
| API | FastAPI + Pydantic + SQLAlchemy |
| Agent | **自研** `agent/runtime.py` + `supervisor.py` + `llm_ops.py` |
| LLM | 自研 `llm/gateway.py`（OpenAI-compatible HTTP） |
| Tools | 自研 `tools/registry.py` + Sandbox |
| 数据 | Pandas / DuckDB |

设计文档原建议是「自研 State Machine 为主，可用 LangGraph 辅助」。V1/V2 **未引入** LangChain。

---

## 1. 重构目标

1. **Agent 编排**改为 LangChain 生态可维护实现，保留产品行为：Plan → Tool → Observe → RePlan → Insight → Report。  
2. **Tool Calling** 使用 LangChain Tools / bind_tools，替代手写 tool schema 拼装（可保留现有工具函数体）。  
3. **LLM** 使用 LangChain Chat Model（OpenAI-compatible，继续对接 DeepSeek 等）。  
4. **对外 API / 前端 / DB / Sandbox 安全策略尽量不变**，降低回归成本。  
5. 保持原则：**数值结论必须来自工具真实执行**。

---

## 2. 范围

### 2.1 In Scope

| 模块 | 内容 |
|------|------|
| LLM 适配 | `ChatOpenAI`（或等价）替换自研 Gateway 的主路径 |
| Tools | 现有 python/sql/statistics/… 包装为 LangChain `@tool` / `StructuredTool` |
| Agent Loop | 用 **LangGraph** StateGraph 实现 Supervisor 循环（推荐；纯 Chain 难以表达 RePlan） |
| Trace / SSE | 从 Graph 事件或节点回调映射到现有 SSE / `agent_steps` / `tool_calls` |
| 配置 | API Key、model、base_url 仍走现有 Settings / `.env` |
| 测试 | 核心图可 mock LLM；Sandbox 单测保留 |

### 2.2 Out of Scope

- 前端大改 / `UI_Optimize.md`  
- 更换 FastAPI / Next.js  
- LangSmith 云端强制依赖（可选后续）  
- 一次性删除全部旧 `llm_ops`（可先并存，标记 deprecated）  

---

## 3. 功能需求

**REQ-LC-001**  
WHEN 系统调用大模型，THE SYSTEM SHALL 通过 LangChain Chat Model（OpenAI-compatible）发起请求，并统计 token usage（若提供方返回）。

**REQ-LC-002**  
THE SYSTEM SHALL 将至少以下能力注册为 LangChain Tools：`dataset_schema`、`dataset_preview`、`python_execute`、`sql_query`、`statistics`、`anomaly_detection`、`generate_chart`。

**REQ-LC-003**  
WHEN 用户发起分析 Run，THE SYSTEM SHALL 由 LangGraph（或等价 LC Agent 图）驱动节点执行，覆盖：understand/plan/tool/observe/replan/insight/report。

**REQ-LC-004**  
WHEN 图执行过程中，THE SYSTEM SHALL 继续通过 SSE 推送 step/observation/chart/final，并持久化 Trace / Evidence（字段兼容现有 API）。

**REQ-LC-005**  
WHEN Tool 执行失败，THE SYSTEM SHALL 支持有限次 Reflection/重试，且不超过 `MAX_AGENT_STEPS` / `RUN_TIMEOUT_SEC` / 取消标志。

**REQ-LC-006**  
THE SYSTEM SHALL 保持 Sandbox 安全基线（Python AST 白名单、SQL 只读）；Tool 内部仍调用现有 sandbox 实现。

**REQ-LC-007**  
IF LangChain 路径异常，THEN THE SYSTEM SHALL 返回明确错误；V1 不要求静默回退到旧 Runtime（可配置开关 `AGENT_ENGINE=langchain|legacy` 作为过渡，推荐默认 langchain）。

**REQ-LC-008**  
THE SYSTEM SHALL 在 README / requirements 中声明 LangChain / LangGraph 版本依赖。

---

## 4. 已确认决策

> 状态：**已确认**（按推荐方案）  
> 确认时间：2026-09-04

| # | 项 | 结论 |
|---|----|------|
| 1 | 编排 | **LangGraph** StateGraph（Supervisor + tools 节点） |
| 2 | LLM | `langchain-openai` `ChatOpenAI` + `base_url`（DeepSeek 兼容） |
| 3 | Tools | `langchain_core.tools` StructuredTool，复用 `tools/registry.py` |
| 4 | 包 | `langchain-core`、`langchain-openai`、`langgraph` |
| 5 | 过渡 | `AGENT_ENGINE=langchain` 默认；保留 `legacy` 开关 |
| 6 | 观测 | 先用现有 Trace/SSE；LangSmith 默认关闭 |

---

## 5. 非功能

**REQ-LC-NFR-001**  
重构后 `pytest` 现有 Sandbox / SQL guard 单测仍通过；新增 Graph 单元测试（mock LLM）。

**REQ-LC-NFR-002**  
对外 REST 路径与前端契约保持兼容（允许新增字段，不删已有必需字段）。

---

## 6. 验收

**REQ-LC-DEMO-001**  
WHEN 上传 `samples/superstore_clean.csv`（或 `sales.csv`）并提问销售相关问题，THE SYSTEM SHALL 在 `AGENT_ENGINE=langchain` 下完成分析并展示 Trace（可见 plan/tool/insight）。

**REQ-LC-DEMO-002**  
WHEN Trace 中出现 tool 步骤，THE SYSTEM SHALL 能对应到 LangChain Tool 调用且结果来自真实执行。

---

## 7. 与进行中 V3 的关系

- V3 工程化（Audit/Settings/Metrics）与 LangChain 重构可并行，但 **Agent 内核以本需求为准重写**。  
- 建议顺序：先落地 LangChain/LangGraph Runtime 兼容现有 API → 再继续未完成的 V3 工程项。  

---

## 8. 下一步

需求已确认 → 见 `specs/langchain/design.md` / `specs/langchain/tasks.md`。

**仅当你明确回复「开始执行」后，才可修改业务代码。**
