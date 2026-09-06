# DataMind Agent — V4 Requirements

> 基线：V1–V3 + LangChain/LangGraph Runtime  
> 本阶段：**V4 — Agent Evaluation（能力量化）**  
> 语法：EARS  
> 状态：待确认

---

## 0. 阶段定位

| 已完成 | 下一阶段 |
|--------|----------|
| V1 MVP 分析链路 | **V4 Evaluation** |
| V2 Supervisor / SQL / Trace | （`UI_Optimize.md` 视觉大改另开阶段，不纳入 V4） |
| V3 Settings / Audit / Metrics / Sandbox | |
| LangChain + LangGraph 重构 | |

V3 的 `/api/metrics` 提供粗聚合；V4 目标是：**可复跑的评测集 + 分项指标 + 评测面板**，用于量化 Agent 真实能力（面试/工程展示重点之一）。

---

## 1. 阶段目标

1. **评测数据集**：内置销售分析任务集（含期望要点 / 关键数值线索）。  
2. **评测执行器**：对每个 case 跑 Agent（可 mock 或真实 LLM），采集 Trace / Tool / 结论。  
3. **指标计算**：Task / Tool / Python / SQL 成功率、Latency、Token、Cost；计算与洞察的启发式准确率。  
4. **Evaluation API + Dashboard**：展示与 `PROJECT_DESIGN` 中 Evaluation 面板一致的核心数字。  
5. **可回归**：`pytest` 或 CLI 可在 CI 用 mock LLM 跑通评测管线。

**非目标**：完整人工标注平台、幻觉率精标、多用户权限、UI_Optimize 全量暗色重构、远程 MySQL 数据源。

---

## 2. 范围

### 2.1 In Scope

| 模块 | 内容 |
|------|------|
| Eval Cases | JSON/YAML 任务集（question、dataset、expects） |
| Runner | 批量执行 → 落 `eval_runs` / `eval_case_results` |
| Metrics | Task Success、Tool Success、Python/SQL Success、Avg Steps/Latency/Tokens/Cost；Calculation / Insight 启发式分 |
| API | 触发评测、查询结果、汇总 |
| UI | Evaluation 面板页（数字卡片 + case 列表） |
| CLI | `python -m evaluation.run --suite sales`（可选但推荐） |

### 2.2 Out of Scope（→ V5 / 另开）

- 多租户、RBAC、团队协作  
- RAG / MCP  
- `UI_Optimize.md` 工作台视觉重做  
- 人工打分工作流 / 标注工具  

---

## 3. 功能需求

### 3.1 评测集

**REQ-V4-CASE-001**  
THE SYSTEM SHALL 提供至少一套内置评测集（如 `evaluation/datasets/sales_suite.json`），覆盖：趋势、地区下钻、商品、异常、追问过滤等 ≥5 个 case。

**REQ-V4-CASE-002**  
WHEN 定义 case，THE SYSTEM SHALL 支持字段：`id`、`question`、`dataset`（相对 samples 路径）、`expect`（含 `must_mention`、`tool_ Prefer`、`max_steps` 等）。

---

### 3.2 执行

**REQ-V4-RUN-001**  
WHEN 用户或 CLI 触发评测，THE SYSTEM SHALL 按 suite 逐 case 执行 Agent（引擎遵循 `AGENT_ENGINE`），并记录每次结果。

**REQ-V4-RUN-002**  
IF 配置 `EVAL_MODE=mock`，THEN THE SYSTEM SHALL 允许不调用真实 LLM，使用脚本化假 Trace 验证管线（CI 友好）。

**REQ-V4-RUN-003**  
WHEN case 执行结束，THE SYSTEM SHALL 持久化：status、steps、tool 成功数、tokens、latency、final_answer、评分明细。

---

### 3.3 指标

**REQ-V4-MET-001**  
THE SYSTEM SHALL 计算并展示至少：

- Task Success Rate（final_answer / expect 启发式通过）  
- Tool Success Rate  
- Python Success Rate  
- SQL Success Rate（若有 SQL 调用）  
- Avg Steps、Avg Latency、Avg Tokens、Avg Cost  

**REQ-V4-MET-002**  
WHEN expect 含关键数值或关键词，THE SYSTEM SHALL 给出 Calculation/Insight 启发式得分（0–1），不得假装人工精标。

**REQ-V4-MET-003**  
Hallucination Rate 在 V4 可用「结论数字未出现在任何 tool_result 中」的启发式近似；须在 UI 标注为 *heuristic*。

---

### 3.4 API / UI

**REQ-V4-API-001**  
THE SYSTEM SHALL 提供：`POST /api/evaluations`（启动）、`GET /api/evaluations`、`GET /api/evaluations/{id}`、`GET /api/evaluations/{id}/summary`。

**REQ-V4-API-002**  
WHEN 配置了 `APP_API_KEY`，THE SYSTEM SHALL 要求启动评测携带 `X-API-Key`。

**REQ-V4-UI-001**  
THE SYSTEM SHALL 提供前端 Evaluation 页，展示汇总卡片与 case 明细（通过/失败、耗时、工具成功率）。

---

## 4. 非功能

**REQ-V4-NFR-001**  
真实 LLM 评测默认不进 CI；mock 管线必须 `pytest` 可绿。

**REQ-V4-NFR-002**  
评测不得破坏现有分析台 API 契约。

**REQ-V4-NFR-003**  
文档说明：如何加 case、如何跑 suite、指标含义与局限。

---

## 5. 已确认决策

> 状态：**已确认**（按推荐方案 · V4 Evaluation）  
> 确认时间：2026-09-04

| # | 项 | 结论 |
|---|----|------|
| 1 | 任务格式 | JSON suite，`evaluation/datasets/` |
| 2 | 存储 | 表 `eval_runs`、`eval_case_results`（SQLite） |
| 3 | 成功判定 | 关键词 + 可选数值容差；不做 LLM-as-judge |
| 4 | 前端路由 | `/evaluation` |
| 5 | 与 Metrics | 保留 V3 `/api/metrics`；Evaluation 独立 |
| 6 | UI 风格 | 沿用现有视觉；不做 UI_Optimize 暗色大改 |

未选 A/B/C 并行议题；本阶段仅 V4 Evaluation。

---

## 6. 验收场景

**REQ-V4-DEMO-001**  
WHEN 以 mock 模式跑 `sales_suite`，THE SYSTEM SHALL 产出 summary 且 Task Success 可计算。

**REQ-V4-DEMO-002**  
WHEN 配置真实 LLM 后手动跑评测，THE SYSTEM SHALL 在 `/evaluation` 看到分项指标与 case 列表。

**REQ-V4-DEMO-003**  
WHEN 查看 Hallucination / Insight 指标，THE SYSTEM SHALL 标明 heuristic。

---

## 7. 下一步

需求已确认 → 见 `specs/v4/design.md` / `specs/v4/tasks.md`。

**仅当你明确回复「开始执行」后，才可修改业务代码。**
