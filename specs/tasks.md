# DataMind Agent — Implementation Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 范围：V1 MVP  
> 执行门槛：仅当用户明确回复 **「开始执行」** 后，方可改业务代码

---

## 使用说明

- 任务按依赖顺序排列；标注 `[P0]` / `[P1]`。
- 完成标准可勾选；建议按 Phase 顺序交付。
- 每完成一个 Phase，应能本地运行并验证该 Phase 的验收点。

---

## Phase 0 — 工程骨架 `[P0]`

### T0.1 仓库骨架与配置
- [ ] 创建目录结构（`apps/web`, `server`, `agent`, `tools`, `sandbox`, `data`, `llm`, `storage`, `samples`, `tests`）
- [ ] 添加 `.gitignore`（`.env`, `storage/uploads/*`, `*.db`, `node_modules` 等）
- [ ] 添加 `.env.example`（按 design §10.1）
- [ ] 添加根 `README.md`（启动前后端的最短说明）
- **验收**：目录与配置文件齐全，无业务逻辑也可 clone 后看懂结构

### T0.2 Backend 可启动
- [ ] FastAPI `server/main.py` + `/api/health`
- [ ] `core/config.py` 读取环境变量
- [ ] `core/db.py` SQLAlchemy + SQLite 初始化
- [ ] `requirements.txt` 或 `pyproject.toml` 锁定依赖
- **验收**：`uvicorn` 启动后 `GET /api/health` 返回 ok

### T0.3 Frontend 可启动
- [ ] 初始化 Next.js App Router + TS + Tailwind
- [ ] 基础布局壳（左栏 / 主区占位）
- [ ] `lib/api` 封装 baseURL
- **验收**：`pnpm dev` 可打开首页

---

## Phase 1 — Workspace & 数据上传 `[P0]`

### T1.1 Workspace API + 持久化
- [ ] ORM：`workspaces`
- [ ] `GET/POST /api/workspaces`
- [ ] 启动时确保存在默认 Workspace
- **验收**：可创建并列出 Workspace

### T1.2 文件上传与解析
- [ ] ORM：`datasets`
- [ ] `POST /api/workspaces/{id}/datasets`（multipart）
- [ ] `data/parser.py` 支持 csv / xlsx
- [ ] 文件落到 `storage/uploads/`
- [ ] 上传大小限制（如 20MB）与格式校验
- **验收**：上传样例文件后 DB 有记录且文件存在

### T1.3 前端上传与列表
- [ ] Workspace 切换 / 列表
- [ ] 数据集上传与列表展示
- **验收**：浏览器完成上传并看到数据集名称

---

## Phase 2 — Dataset Profiler `[P0]`

### T2.1 Profiler 引擎
- [ ] `data/profiler.py`：规模、类型推断、缺失、重复、nunique、时间范围、IQR 异常计数
- [ ] ORM：`dataset_fields`；`datasets.profile_json`
- [ ] 上传成功后自动 Profile
- **验收**：`GET /api/datasets/{id}` 返回完整 Profile

### T2.2 Profile UI
- [ ] `DatasetProfileCard`（行数、字段、质量摘要）
- [ ] 字段表预览入口 `GET /api/datasets/{id}/preview`
- **验收**：UI 可见 Profile 与预览行

### T2.3 样例数据
- [ ] 生成 `samples/sales.csv`（含 8 月下降 / 华东 / SKU-A / 客户流失特征）
- **验收**：用该文件 Profile 合理，可供后续 Demo

---

## Phase 3 — LLM Gateway & Chat 基础 `[P0]`

### T3.1 LLM Gateway
- [ ] `llm/types.py`、`llm/gateway.py`
- [ ] `providers/openai_compatible.py`（DeepSeek 默认）
- [ ] 记录 usage tokens
- **验收**：独立脚本能完成一次 chat 调用

### T3.2 Conversation / Message API
- [ ] ORM：`conversations`, `messages`
- [ ] 创建对话（绑定 dataset）
- [ ] 拉取消息历史
- [ ] 发送用户消息（先回显，Agent 可先占位）
- **验收**：对话 CRUD 可用

### T3.3 Chat UI + SSE 骨架
- [ ] `ChatPanel` 发送消息
- [ ] SSE 客户端解析框架（可先推送 mock 事件）
- **验收**：发送后看到用户消息；能消费至少一种 SSE 事件

---

## Phase 4 — Python Tool & Sandbox `[P0]`

### T4.1 受限执行器
- [ ] `sandbox/security.py` AST 白名单
- [ ] `sandbox/executor.py` 子进程 + timeout + 注入 `df`
- [ ] 结构化返回 stdout / `result` / error
- **验收**：合法聚合代码成功；危险 import 被拒绝；超时可中断

### T4.2 python_execute Tool
- [ ] `tools/python_exec.py` + `tools/registry.py`
- [ ] `dataset_schema` / `dataset_preview` Tool
- **验收**：给定 dataset_id + 代码，API/服务内可执行并返回结果

---

## Phase 5 — Planner + Agent Loop 核心 `[P0]`

### T5.1 AgentState 与 Runtime
- [ ] `agent/state.py`
- [ ] `agent/events.py`（SSE 事件模型）
- [ ] `agent/runtime.py`：INIT→…→DONE，步数上限
- [ ] ORM：`agent_runs`, `agent_steps`, `tool_calls`
- **验收**：mock Planner/Tool 时可完整走完状态机并落库

### T5.2 Planner Agent
- [ ] `agent/planner.py` + prompts
- [ ] 输出结构化 plan（goal + steps）
- [ ] Trace 记录 Planner 步骤
- **验收**：对「为什么 8 月销售下降？」生成 ≥5 步合理计划

### T5.3 Python 代码生成 + 执行接入 Loop
- [ ] 在 EXECUTE 阶段生成 Pandas 代码并调用 Sandbox
- [ ] Observation 写入 state
- **验收**：至少完成「月度销售趋势 / 环比」真实计算

### T5.4 Analysis + RePlan 下钻
- [ ] `agent/analyst.py`：解释结果、判断是否下钻
- [ ] 自动追加地区 / 商品 / 客户类步骤
- **验收**：一次 Run 内出现多次 Execute，并定位到主要下降维度

### T5.5 对话 API 接入真实 Runtime（SSE）
- [ ] `POST .../messages` 流式推送 plan/tool/observation/final
- **验收**：前端流式看到分析过程

---

## Phase 6 — Reflection、Memory、错误边界 `[P1]`

### T6.1 Reflection / Retry
- [ ] 执行失败时带 schema 与 error 重新生成代码
- [ ] `MAX_TOOL_RETRIES` 限制
- **验收**：故意错误字段名可自动修复（或明确失败并停止）

### T6.2 Memory
- [ ] `conversations.context_json` 读写
- [ ] 追问「只看华东」更新 filters 并影响后续计划/代码
- **验收**：多轮追问上下文保持

### T6.3 错误处理
- [ ] 空结果 / JSON 解析失败 / 超时 / 达最大步数的用户可见提示
- [ ] Run status = error/done 与部分结论返回
- **验收**：异常路径不导致服务崩溃

---

## Phase 7 — 图表、洞察、报告、Evidence、Trace `[P0/P1]`

### T7.1 自动图表 `[P0]`
- [ ] `tools/chart.py` 生成 ECharts option
- [ ] ORM：`charts`
- [ ] 前端 `ChartView`
- **验收**：分析后至少出现趋势图与分类对比图

### T7.2 Insight Agent `[P0]`
- [ ] `agent/insight.py`：Observation / Evidence / Reason / Impact / Recommendation
- [ ] ORM：`insights`
- **验收**：最终洞察结构化且引用真实数字

### T7.3 Report Agent `[P1]`
- [ ] `agent/reporter.py` → Markdown
- [ ] ORM：`reports`；`GET .../report`
- [ ] 前端报告面板
- **验收**：报告含 Summary / Findings / Root Cause / Recommendations / Evidence

### T7.4 Evidence 链 `[P0]`
- [ ] ORM：`evidences`；结论绑定 tool_call
- [ ] `GET /api/evidences/{id}`
- [ ] `EvidenceDrawer`
- **验收**：点击关键结论可看到代码与执行结果

### T7.5 Agent Trace UI `[P0]`
- [ ] `GET /api/agent-runs/{id}/trace`
- [ ] `AgentTracePanel` 时间线
- **验收**：可回放 Planner → Tools → Drill → Insight → Report

---

## Phase 8 — Demo 打磨与质量 `[P0]`

### T8.1 端到端 Demo 验收
- [ ] 使用 `samples/sales.*` 完整跑通 REQ-DEMO-002 全链路
- [ ] 核对：整体下降 → 地区 → SKU → 客户 → 图表 → 洞察 → 报告 → Trace → Evidence
- **验收**：满足 `requirements.md` §6

### T8.2 基础测试
- [ ] Profiler unit tests
- [ ] Sandbox 安全 tests
- [ ] Runtime 状态转移（mock LLM）integration test
- **验收**：`pytest` 关键路径通过

### T8.3 体验体验与 README
- [ ] 一键启动说明（backend + frontend + env）
- [ ] Demo 操作步骤（上传 → 提问话术）
- **验收**：按 README 可从零复现 Demo

---

## 明确不做（本 V1 任务集）

- SQL Agent / 数据库数据源
- Docker 级 Sandbox
- Evaluation Dashboard
- 多用户权限 / RBAC
- PDF/Excel 导出
- LangGraph 接入
- Redis / MinIO / PostgreSQL 生产部署（仅保留接口与配置位）

---

## 建议实施顺序（压缩视图）

```text
T0 → T1 → T2 → T3 → T4 → T5 → T7(图表/洞察/Evidence/Trace)
                ↓
              T6(Memory/Reflection)
                ↓
              T7.3 Report → T8 Demo
```

---

## 确认与执行

1. 审阅本任务分解；若需调整 Phase/优先级，直接指出任务编号。  
2. 回复 **`确认任务`** 或 **`开始执行`**：  
   - `确认任务`：仅锁定任务清单  
   - `开始执行`：按 Phase 0 起修改业务代码并实现  

**未收到「开始执行」前，不修改业务代码。**
