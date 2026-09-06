# DataMind Agent — Requirements Specification

> 产品：DataMind Agent（AI 智能数据分析师）
> 来源：`PROJECT_DESIGN.md`
> 范围：以 **V1 MVP** 为核心交付边界；后续版本需求单独标注为 Future。
> 语法：EARS（Easy Approach to Requirements Syntax）

---

## 1. 文档目的

本文档将 `PROJECT_DESIGN.md` 中的产品设计转化为可确认、可验收的系统需求，作为后续 `design.md` / `tasks.md` 与实现的唯一需求基线。

---

## 2. 范围定义

### 2.1 In Scope（V1 MVP）

- Excel / CSV 数据上传与解析
- Dataset Profiler（数据理解）
- Workspace 基础管理
- 自然语言分析对话（含流式输出）
- Planner → Python Tool → Analysis → Chart → Insight → Answer 主链路
- Agent Trace 与 Evidence 证据链（基础可观察性）
- 示例电商销售数据集与 Demo 场景：「为什么 8 月销售下降？」

### 2.2 Out of Scope（V1，标注为 Future）

- MySQL / PostgreSQL / SQLite / REST API 等数据库与外部数据源
- 完整 Supervisor 多 Agent 调度（V2）
- 生产级 Python Sandbox 资源隔离（V3，V1 可用受限执行器）
- Agent Evaluation Dashboard（V4）
- 多用户权限、团队协作、审计、MCP、RAG（V5）
- PDF / Excel 报告导出（V1 仅 Markdown 报告）

---

## 3. 术语

| 术语 | 定义 |
|------|------|
| Workspace | 独立管理数据集、对话、分析任务、图表与报告的工作空间 |
| Dataset Profile | 数据集规模、字段类型、质量与统计摘要，作为 Agent Context |
| Agent Loop | Plan → Execute → Observe → RePlan 的自主分析循环 |
| Evidence | 将 AI 结论关联到 Tool Call、代码/SQL 与真实执行结果 |
| Agent Trace | Agent 执行步骤的可观察记录 |

---

## 4. 功能需求

### 4.1 Workspace

**REQ-WS-001**  
WHEN 用户请求创建工作空间，THE SYSTEM SHALL 创建独立 Workspace，并为其分配唯一标识。

**REQ-WS-002**  
WHEN Workspace 已创建，THE SYSTEM SHALL 允许用户在该 Workspace 内管理数据集、对话、分析记录、图表与报告，且不同 Workspace 的数据相互隔离。

**REQ-WS-003**  
WHEN 用户请求列出或切换 Workspace，THE SYSTEM SHALL 返回当前用户可访问的 Workspace 列表并允许切换当前上下文。

---

### 4.2 Data Source（V1）

**REQ-DS-001**  
WHEN 用户在 Workspace 中上传 `.xlsx`、`.xls` 或 `.csv` 文件，THE SYSTEM SHALL 接收并持久化该文件，并创建对应 Dataset 记录。

**REQ-DS-002**  
WHEN 上传文件格式不受支持，THE SYSTEM SHALL 拒绝上传并返回明确错误信息。

**REQ-DS-003**  
WHEN Dataset 创建成功，THE SYSTEM SHALL 解析文件内容为可分析的表格数据，并记录行数与列数。

**REQ-DS-004**（Future — V2）  
WHEN 用户配置 MySQL / PostgreSQL / SQLite 连接，THE SYSTEM SHALL 支持将数据库表注册为数据源。

---

### 4.3 Dataset Profiler

**REQ-DP-001**  
WHEN 新 Dataset 上传并解析成功，THE SYSTEM SHALL 自动执行 Dataset Profiler，无需用户额外操作。

**REQ-DP-002**  
WHEN Profiler 运行，THE SYSTEM SHALL 识别并输出：数据集名称、记录数、字段数、各字段推断类型。

**REQ-DP-003**  
WHEN 数据中存在可识别时间字段，THE SYSTEM SHALL 计算并输出时间范围。

**REQ-DP-004**  
WHEN Profiler 运行，THE SYSTEM SHALL 检测并输出至少以下质量信息：缺失值比例、重复行数、数值字段异常值数量、分类字段唯一值数量、数值分布摘要。

**REQ-DP-005**  
WHEN Profile 生成完成，THE SYSTEM SHALL 将 Dataset Profile 持久化，并作为后续 Agent 分析的基础 Context。

**REQ-DP-006**  
WHEN 用户查看 Dataset，THE SYSTEM SHALL 展示 Profile 摘要与字段列表。

---

### 4.4 AI Analysis / Chat

**REQ-AA-001**  
WHEN 用户在已绑定 Dataset 的对话中输入自然语言问题，THE SYSTEM SHALL 启动一次 Agent 分析 Run。

**REQ-AA-002**  
WHEN Agent 正在执行，THE SYSTEM SHALL 通过流式方式向客户端推送执行进度与阶段性输出。

**REQ-AA-003**  
WHEN 用户在同一对话中继续追问，THE SYSTEM SHALL 使用该对话的上下文（含当前 Dataset 与已确认的过滤条件）继续分析。

**REQ-AA-004**  
IF 对话未绑定 Dataset，THEN THE SYSTEM SHALL 提示用户先选择或上传数据集，且不启动分析 Run。

---

### 4.5 Planner Agent

**REQ-PL-001**  
WHEN 用户提出分析问题，THE SYSTEM SHALL 由 Planner 将问题转换为结构化分析计划（含 goal 与有序 steps）。

**REQ-PL-002**  
WHEN 分析计划生成完成，THE SYSTEM SHALL 将该计划写入 Agent State，并在 Trace 中可见。

**REQ-PL-003**  
WHEN Observation 表明需要进一步下钻，THE SYSTEM SHALL 允许 Planner / RePlan 更新后续步骤并继续执行。

---

### 4.6 Python Tool / Code Execution

**REQ-PY-001**  
WHEN 分析步骤需要数据计算、聚合、趋势、统计或异常检测，THE SYSTEM SHALL 生成 Python 代码并通过执行器对 Dataset 执行，而非由 LLM 直接编造数值结果。

**REQ-PY-002**  
WHEN Python 代码执行成功，THE SYSTEM SHALL 将真实执行结果返回给 Analysis 流程。

**REQ-PY-003**  
WHEN Python 代码执行失败，THE SYSTEM SHALL 捕获错误信息，并触发 Reflection / 重试机制（在最大步数限制内）。

**REQ-PY-004**  
WHEN 代码执行器运行，THE SYSTEM SHALL 施加至少以下边界：执行超时、禁止任意网络访问（V1 最低要求）、限制可导入模块范围。

**REQ-PY-005**（Future — V3）  
WHEN 生产级 Sandbox 启用，THE SYSTEM SHALL 额外限制文件访问、进程创建、CPU 与内存用量。

---

### 4.7 Analysis / Insight / Report

**REQ-AN-001**  
WHEN Tool 返回执行结果，THE SYSTEM SHALL 由 Analysis 流程解释结果，识别趋势、异常或主要贡献维度。

**REQ-AN-002**  
WHEN 发现显著异常或主要贡献因素，THE SYSTEM SHALL 优先触发自动下钻（如地区 → 商品 → 客户），直至达到步数上限或判断任务完成。

**REQ-IN-001**  
WHEN 核心分析步骤完成，THE SYSTEM SHALL 生成结构化业务洞察，至少包含：Observation、Evidence、Reason、Impact、Recommendation。

**REQ-RP-001**  
WHEN 用户请求或分析完成需要输出报告，THE SYSTEM SHALL 生成 Markdown 分析报告，至少包含：Executive Summary、Key Findings、Root Cause、Recommendations、Data Evidence。

**REQ-RP-002**（Future）  
WHEN 用户选择导出，THE SYSTEM SHALL 支持将报告导出为 PDF 或 Excel。

---

### 4.8 Visualization / Dashboard

**REQ-VZ-001**  
WHEN 分析结果适合可视化，THE SYSTEM SHALL 根据数据场景自动选择图表类型（时间趋势→折线、分类比较→柱状、占比→饼/环、分布→直方图、相关性→散点等）。

**REQ-VZ-002**  
WHEN 图表生成，THE SYSTEM SHALL 将图表元数据与数据持久化，并在分析结果中展示。

**REQ-VZ-003**  
WHEN 一次完整分析结束，THE SYSTEM SHALL 能汇总关键 KPI 与图表形成该次分析的 Dashboard 视图。

---

### 4.9 Evidence

**REQ-EV-001**  
WHEN 系统给出重要数值结论，THE SYSTEM SHALL 将该结论关联到可追溯 Evidence（数据源、Tool/代码、执行结果）。

**REQ-EV-002**  
WHEN 用户请求查看某条结论的证据，THE SYSTEM SHALL 展示对应的代码或查询、执行结果与分析说明。

---

### 4.10 Agent Trace / State / Observability

**REQ-TR-001**  
WHEN Agent Run 执行，THE SYSTEM SHALL 记录完整 Trace（用户问题、计划步骤、Tool 调用、观察结果、下钻决策、洞察与报告）。

**REQ-TR-002**  
WHEN 用户在开发/调试视图打开 Trace，THE SYSTEM SHALL 按时间顺序展示各 Agent Step 的状态与摘要。

**REQ-ST-001**  
THE SYSTEM SHALL 使用统一 Agent State 管理至少以下字段：question、dataset_id、schema、plan、current_step、observations、tool_results、charts、insights、errors、final_answer。

**REQ-ST-002**  
WHEN Agent Run 中断或失败，THE SYSTEM SHALL 保留已有 State，以支持后续排查与有限重试。

---

### 4.11 Memory（多轮上下文）

**REQ-MM-001**  
WHEN 用户在同一对话中追问（例如「只看华东」「再看商品」），THE SYSTEM SHALL 保留并应用已确立的分析上下文（Dataset、时间范围、维度过滤等）。

**REQ-MM-002**  
WHEN 上下文发生更新，THE SYSTEM SHALL 在后续规划与代码生成中使用最新上下文。

---

### 4.12 Reflection / Self-Correction

**REQ-RF-001**  
WHEN Tool 执行因字段名错误、类型错误或类似可修复问题失败，THE SYSTEM SHALL 结合 Dataset Schema 进行 Reflection，修正代码或计划后重新执行。

**REQ-RF-002**  
WHILE Agent Run 未完成，THE SYSTEM SHALL 将单次 Run 的总步数限制在可配置上限内（默认不超过 20），以防止无限循环。

---

### 4.13 Error Handling

**REQ-ER-001**  
WHEN 发生 Python 执行失败、字段不存在、结果为空、LLM 输出格式错误或 Tool 超时，THE SYSTEM SHALL 进行受控处理（重试、回退、校验或终止），并向用户返回可理解状态，而非静默失败。

**REQ-ER-002**  
IF Agent 达到最大步数或超时，THEN THE SYSTEM SHALL 停止执行，并返回当前已获得的部分结论与 Trace。

---

### 4.14 Settings / LLM Gateway

**REQ-LLM-001**  
THE SYSTEM SHALL 通过统一 LLM Gateway 调用模型，使业务代码不直接绑定单一厂商 SDK。

**REQ-LLM-002**  
WHEN 管理员配置模型提供方与密钥，THE SYSTEM SHALL 使用该配置进行后续推理调用。

**REQ-LLM-003**（Future）  
WHEN 配置多个提供方，THE SYSTEM SHALL 支持在 OpenAI / Claude / Gemini / DeepSeek / Qwen / Local LLM 之间切换。

---

### 4.15 Evaluation（Future — V4）

**REQ-EVL-001**（Future）  
WHEN Evaluation 模块启用，THE SYSTEM SHALL 统计 Task Success Rate、Tool Success Rate、Latency、Token、Cost 等指标。

---

## 5. 非功能需求

**REQ-NFR-001**  
THE SYSTEM SHALL 保证数值结论来源于 Python/SQL 等工具的真实执行结果，而不是 LLM 臆造计算。

**REQ-NFR-002**  
THE SYSTEM SHALL 对每次 Agent Run 记录关键延迟与 Token 用量（若提供方返回），以支持后续成本与性能分析。

**REQ-NFR-003**  
THE SYSTEM SHALL 采用前后端分离架构：Web 前端 + FastAPI 后端 + Agent Runtime + Data Layer。

**REQ-NFR-004**  
WHEN 处理小规模表格数据，THE SYSTEM SHALL 优先使用 Pandas（或等价库）完成分析；WHEN 文件显著变大，THE SYSTEM SHALL 允许演进到 DuckDB / Polars（Future 优化路径）。

**REQ-NFR-005**  
THE SYSTEM SHALL 将结构化业务数据存储于 PostgreSQL（V1 可用 SQLite 作为本地开发替代），并将上传文件存于对象存储或本地文件存储。

**REQ-NFR-006**  
THE SYSTEM SHALL 保证前端在桌面与移动宽度下可用地完成：上传数据、提问、查看 Trace/图表/报告的主流程。

---

## 6. V1 Demo 验收场景（完成标准）

**REQ-DEMO-001**  
WHEN 用户上传电商销售样例 `sales.xlsx`（或等价 CSV），THE SYSTEM SHALL 自动完成数据解析与 Profile。

**REQ-DEMO-002**  
WHEN 用户提问「为什么 8 月销售下降？」，THE SYSTEM SHALL 完成以下端到端链路：

1. Planner 生成分析计划  
2. Python Agent 生成并执行分析代码  
3. 识别整体下降趋势  
4. 自动按地区下钻并定位主要下降区域  
5. 继续按商品 / 客户下钻并定位主要贡献因素  
6. 生成图表  
7. 生成业务洞察与 Markdown 报告  
8. 展示完整 Agent Trace  
9. 重要结论可查看 Evidence  

**REQ-DEMO-003**  
WHEN 上述 Demo 链路完整跑通，THE SYSTEM SHALL 被视为达到 V1 核心里程碑。

---

## 7. 技术约束（来自设计文档，需在 design 阶段细化）

| 层级 | V1 约束 |
|------|---------|
| Frontend | React / Next.js / TypeScript / Tailwind / ECharts 或 Recharts |
| Backend | Python / FastAPI / Pydantic / SQLAlchemy |
| Agent | 自研 Agent State Machine 为主；可用 LangGraph 辅助，但核心 Loop 需可理解、可观测 |
| Data | Pandas；可选 Polars / DuckDB |
| Storage | PostgreSQL 或开发用 SQLite；Redis 可选；本地/MinIO 对象存储 |
| 目录结构 | 对齐设计文档中的 `datamind-agent/` 模块划分 |

---

## 8. 需求优先级

| 优先级 | 需求组 |
|--------|--------|
| P0 | REQ-DS、REQ-DP、REQ-AA、REQ-PL、REQ-PY-001~004、REQ-AN、REQ-IN、REQ-VZ-001~002、REQ-EV、REQ-TR、REQ-ST、REQ-ER、REQ-DEMO、REQ-NFR-001 |
| P1 | REQ-WS、REQ-RP-001、REQ-VZ-003、REQ-MM、REQ-RF、REQ-LLM-001~002、REQ-NFR-002~006 |
| P2 / Future | REQ-DS-004、REQ-PY-005、REQ-RP-002、REQ-LLM-003、REQ-EVL、企业级能力 |

---

## 9. 已确认决策

> 状态：**已确认**（按推荐方案）  
> 确认时间：2026-09-03

| # | 决策项 | 结论 |
|---|--------|------|
| 1 | V1 范围 | 以 §2.1 + Demo 验收为准；暂不实现 SQL Agent / 多用户权限 / Evaluation |
| 2 | 存储 | 本地开发：**SQLite + 本地文件系统**；生产再切 PostgreSQL / MinIO |
| 3 | Agent | **自研 Agent State Machine**（不依赖 LangGraph 黑盒） |
| 4 | 前端 | **Next.js App Router + TypeScript + Tailwind + ECharts** |
| 5 | LLM | **统一 LLM Gateway**（OpenAI-compatible）；V1 默认 DeepSeek，可通过配置切换 |
| 6 | Sandbox | V1：**受限子进程执行器**；完整容器隔离后续再做 |

---

## 10. 下一步

需求已确认 → 见 `specs/design.md` / `specs/tasks.md`。

**仅当你明确回复「开始执行」后，才可修改业务代码。**
