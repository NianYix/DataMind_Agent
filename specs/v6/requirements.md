# DataMind Agent — V6 Requirements

> 状态：**已确认**（用户确认需求；D1–D6 按推荐锁定）  
> 基线：V1–V5 + UI Optimize（已实现）  
> 本阶段：**V6 — RAG Knowledge（文档知识增强）**  
> 语法：EARS

---

## 0. 阶段定位

| 已完成 | 本阶段 | 明确另开 |
|--------|--------|----------|
| V1–V4 分析 / Evaluation | **Workspace 级知识库 + 检索 Tool + Agent 引用** | MCP |
| UI Optimize 暗色工作台 | | SSO / OIDC、完整 RBAC |
| V5 连接器 / Prompt / HTTP / Auth lite | | 行级数据权限、实时协作、多 Agent 编排 |

`PROJECT_DESIGN` 后续扩展以 **RAG** 为首项。本切片目标：让分析 Agent 在结构化数据之外，能检索业务文档（制度、口径、历史报告）并在结论中标注引用来源。

---

## 1. 阶段目标

1. **知识库**：按 Workspace 管理文档集合（上传 PDF / Markdown / TXT / 纯文本）。  
2. **入库管线**：切分（chunk）→ 向量化（embedding）→ 持久化索引。  
3. **检索 Tool**：向 Agent 注册 `knowledge_search`（top-k、可选过滤）。  
4. **可追溯**：检索结果进入 Trace / Evidence；最终回答可展示引用片段。  
5. **可回归**：无真实 Embedding API 时可用 **mock / 本地 hash embedding** 跑通 CI。

**非目标**：MCP Server/Client、跨租户知识联邦、精排重写大模型、完整 PDF OCR 复杂版面、商业向量云托管强依赖、SSO。

---

## 2. 范围

### 2.1 In Scope

| 模块 | 内容 |
|------|------|
| Knowledge Base | CRUD 集合；文档上传与状态（pending/ready/error） |
| Ingest | 文本提取、chunk、embedding、upsert |
| Store | 本地向量存储（推荐 Chroma 或 SQLite+numpy 简易方案，见决策） |
| Tool | `knowledge_search(query, top_k)` |
| Agent | Planner/Supervisor 可选用该 Tool；Insight/Report 可带 citations |
| API | `/api/knowledge-*` |
| UI | `/knowledge` 页（暗色 AppShell）：上传、列表、试检索 |
| Eval（轻量） | 可选 1–2 个 case：问口径类问题须命中文档关键词 |

### 2.2 Out of Scope

| 项 | 去向 |
|----|------|
| MCP | V7 / 另开 |
| 多模态图片理解 / 复杂 OCR | 更后 |
| 自动从 Dataset 生成知识文档 | 更后 |
| 企业 AD/SSO | 更后 |

---

## 3. 功能需求

### 3.1 知识库与文档

**REQ-V6-KB-001**  
WHEN 用户在 Workspace 创建知识库，THE SYSTEM SHALL 支持名称与描述，并归属该 Workspace。

**REQ-V6-KB-002**  
WHEN 用户上传文档，THE SYSTEM SHALL 接受至少：`.md`、`.txt`、`.pdf`；单文件大小受现有上传限额约束。

**REQ-V6-KB-003**  
WHEN 文档入库完成，THE SYSTEM SHALL 将状态标为 `ready`，并记录 chunk 数量；失败时标为 `error` 且错误信息可读、不泄漏密钥。

---

### 3.2 切分与向量化

**REQ-V6-ING-001**  
THE SYSTEM SHALL 将文档切分为重叠 chunk（可配置 chunk_size / overlap），并持久化原文片段。

**REQ-V6-ING-002**  
WHEN 执行 embedding，THE SYSTEM SHALL 使用可配置提供者：`openai_compatible`（复用 LLM base_url/key）或 `mock`（确定性伪向量，用于 CI）。

**REQ-V6-ING-003**  
IF Embedding API 不可用且未选 mock，THEN THE SYSTEM SHALL 失败并写入文档 error 状态，不得静默空索引。

---

### 3.3 检索与 Agent

**REQ-V6-RET-001**  
THE SYSTEM SHALL 提供 `knowledge_search` Tool：输入 query、可选 knowledge_base_id、top_k；返回片段文本、文档名、score。

**REQ-V6-RET-002**  
WHEN Agent 调用该 Tool，THE SYSTEM SHALL 记录 tool_calls，并可将片段写入 Evidence（claim=引用摘要）。

**REQ-V6-RET-003**  
WHEN 用户问题偏「口径/定义/制度/历史结论」，Supervisor/Tool 选择路径 SHALL 允许优先或可选调用 `knowledge_search`（提示词增量即可，不强制改整图架构）。

**REQ-V6-RET-004**  
IF Workspace 无 ready 文档，THEN `knowledge_search` SHALL 返回明确空结果说明，不得抛未处理异常。

---

### 3.4 API / UI

**REQ-V6-API-001**  
THE SYSTEM SHALL 提供：知识库 CRUD、文档上传/列表/删除、触发（或自动）ingest、试检索 API。

**REQ-V6-API-002**  
WHEN `AUTH_ENABLED=true`，写操作 SHALL 要求成员或 admin（与 V5 门禁风格一致）；`AUTH_ENABLED=false` 时保持 Demo 可用。

**REQ-V6-UI-001**  
THE SYSTEM SHALL 提供 `/knowledge` 页面：选择 Workspace、上传、查看状态、试检索结果列表。

**REQ-V6-UI-002**  
TopBar SHALL 增加 Knowledge 导航入口。

---

## 4. 非功能

**REQ-V6-NFR-001**  
向量与原文默认落在本地 `storage/`（gitignore），不得提交密钥或用户文档到仓库。

**REQ-V6-NFR-002**  
`pytest` 在 `EMBEDDING_PROVIDER=mock` 下必须全绿；不得依赖外网 Embedding。

**REQ-V6-NFR-003**  
检索延迟在本地小库（≤1000 chunks）下应可接受（目标 P95 &lt; 2s，尽力而为）。

---

## 5. 验收标准

1. 上传一份含「华东口径」说明的 `.md`，ingest 成功为 ready。  
2. 试检索能返回相关 chunk。  
3. Agent 分析会话中调用 `knowledge_search` 可见 Trace/Evidence。  
4. mock embedding 下 `pytest -q` 全绿。  
5. 无知识库时 Tool 返回空结果而非 500。

---

## 6. 决策（已锁定）

| # | 决策项 | 取值 |
|---|--------|------|
| D1 | 做 RAG Knowledge | **是** |
| D2 | 向量库 | **Chroma → `storage/chroma`** |
| D3 | Embedding | 默认 **openai_compatible**；CI **mock** |
| D4 | PDF | **pypdf** 抽文本（无 OCR） |
| D5 | MCP | **否**（V7） |
| D6 | Evaluation 知识库 suite | **P1** 轻量 1–2 case |

---

## 7. 确认方式

需求已确认。请审阅 `design.md` / `tasks.md` 后回复：

- **`确认设计`** — 锁定方案  
- **`开始执行`** — 锁定并开工

**未回复「开始执行」前不修改业务代码。**
