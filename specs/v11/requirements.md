# DataMind Agent — V11 Requirements

> 基线：V1–V10（已实现）  
> 本阶段：**V11 — Ollama 本地模型分析**  
> 语法：EARS  
> 状态：**已确认**（D1–D7 按建议锁定）

---

## 0. 阶段定位

| 已完成 | 本阶段 | 明确另开 |
|--------|--------|----------|
| 远程 OpenAI 兼容 API 分析（默认 DeepSeek：`llm_base_url` / `llm_api_key` / `llm_model`） | **新增 Ollama 本地模型作为分析后端，可与 API 模式切换** | 多模型路由 / 按 Run 临时选模型 / 本地 Embedding 全量替换 |
| LangChain `ChatOpenAI` + Legacy `LLMGateway` 共用同一套 Settings | **两套引擎路径均支持 Ollama；Settings UI 可配置与探测** | 自建模型微调流水线、GPU 调度面板 |
| Settings 热更新 base_url / model / api_key | **Provider 模式、Ollama 连通性与本地模型列表** | 云厂商专用 SDK（Anthropic / Gemini 原生协议） |

现状：分析链路强制走 OpenAI Compatible HTTP（需 `LLM_API_KEY`），无法在无外网/无 Key 时用本机 Ollama 完成同等 Agent 分析。

---

## 1. 阶段目标

1. **双模式**：保留现有「远程 API」分析；新增「Ollama 本地」分析，用户可切换，默认仍为 API（不打断现网）。  
2. **配置**：可配置 Ollama 地址、模型名；本地模式不强制真实 API Key。  
3. **探测**：可检测 Ollama 是否可达，并列出本机已拉取模型。  
4. **引擎一致**：`agent_engine=langchain` 与 `legacy` 在 Ollama 模式下均可完成分析（能力受模型 tool-calling 支持程度约束，见决策项）。  
5. **UI**：Settings 可切换 Provider、填写 Ollama 参数、一键连通性测试；Workspace / Workflow 分析入口无需改交互语义。  
6. **可回归**：无真实 Ollama 时可用 mock / 单元测试验证 Provider 分支与配置热更新。

**非目标**：安装/管理 Ollama 进程本身、模型下载 UI、多 Provider 同时并行调用、按对话临时覆盖全局 Provider、本地向量模型替换（可后续 backlog）。

---

## 2. 范围

### 2.1 In Scope

| 模块 | 内容 |
|------|------|
| Config | `llm_provider`（`api` \| `ollama`）；Ollama 默认 base URL；API Key 策略；HOT_FIELDS 热更新 |
| LLM 层 | Gateway / LangChain 工厂按 provider 构建客户端；Ollama OpenAI 兼容端点 |
| Ops API | Settings 读写含 provider；连通性 / 模型列表探测接口 |
| UI Settings | Provider 切换、Ollama URL/Model、测试连接、保存 |
| Agent | Workspace 对话分析、Workflow `analyze` 节点随全局 Provider 走本地或远程 |
| Docs / Tests | README/.env 示例；provider 分支单测 |

### 2.2 Out of Scope

| 项 | 去向 |
|----|------|
| Ollama 安装向导、pull 模型 UI | 文档指引即可 |
| 按 Run / 会话级临时选模型 | backlog |
| 本地 Embedding / RAG 专用 Ollama embed | 另开或 P1 |
| Anthropic / Gemini 原生协议 | 另开 |
| 多机 Ollama 集群负载均衡 | 不做 |

---

## 3. 功能需求

### 3.1 配置与 Provider

**REQ-V11-CFG-001**  
THE SYSTEM SHALL 支持配置项 `llm_provider`，取值至少包含 `api` 与 `ollama`；默认值为 `api`。

**REQ-V11-CFG-002**  
WHEN `llm_provider` 为 `api`，THE SYSTEM SHALL 保持与 V10 等价行为：使用 `llm_base_url`、`llm_api_key`、`llm_model` 调用 OpenAI 兼容远程 API；未配置 `llm_api_key` 时拒绝发起真实 LLM 调用并给出明确错误。

**REQ-V11-CFG-003**  
WHEN `llm_provider` 为 `ollama`，THE SYSTEM SHALL 使用 Ollama 服务地址（建议配置键 `ollama_base_url`，默认 `http://localhost:11434`）与模型名（可复用 `llm_model` 或独立 `ollama_model`，见决策 D2）发起分析请求。

**REQ-V11-CFG-004**  
WHEN `llm_provider` 为 `ollama`，THE SYSTEM SHALL NOT 因缺少真实 `llm_api_key` 而拒绝调用；若底层客户端需要占位 Key，THE SYSTEM SHALL 使用可配置占位值（如 `ollama`）且不要求用户填写云厂商密钥。

**REQ-V11-CFG-005**  
THE SYSTEM SHALL 允许通过 Settings 热更新（`settings.json` / HOT_FIELDS）切换 `llm_provider` 及相关 URL、模型字段，并在保存后使后续新 Run 生效（重建 Gateway / Chat 客户端缓存）。

### 3.2 LLM 调用路径

**REQ-V11-LLM-001**  
WHEN `llm_provider=ollama` 且 `agent_engine=langchain`，THE SYSTEM SHALL 通过 OpenAI 兼容客户端指向 Ollama 的 `/v1`（或等价）端点完成 Agent 推理。

**REQ-V11-LLM-002**  
WHEN `llm_provider=ollama` 且 `agent_engine=legacy`，THE SYSTEM SHALL 通过现有 `LLMGateway` / Provider 抽象完成同等聊天调用（指向 Ollama）。

**REQ-V11-LLM-003**  
WHEN Ollama 不可达、超时或返回错误，THE SYSTEM SHALL 将失败映射为可观测的 Run/SSE 错误信息（含简短原因），且不得静默成功。

**REQ-V11-LLM-004**  
THE SYSTEM SHALL 在 Ollama 模式下继续统计可用的 token usage（若响应提供）；若 Ollama 未返回 usage，THE SYSTEM SHALL 将相关计数记为 0 或 null，且不因此中断分析。

### 3.3 探测与运维 API

**REQ-V11-OPS-001**  
THE SYSTEM SHALL 提供探测接口（建议 `GET /api/llm/ollama/health` 或 Settings 子路径），WHEN 调用时 SHALL 检查配置的 Ollama base URL 是否可达，并返回可达性与延迟（或错误摘要）。

**REQ-V11-OPS-002**  
WHEN Ollama 可达，THE SYSTEM SHALL 能列出本机已安装模型名称列表（基于 Ollama `/api/tags` 或等价），供 Settings UI 选用。

**REQ-V11-OPS-003**  
THE SYSTEM SHALL 在公开 Settings 响应中暴露当前 `llm_provider` 以及 Ollama 相关非敏感配置（不含密钥明文）。

### 3.4 UI

**REQ-V11-UI-001**  
WHEN 用户打开 Settings 页，THE SYSTEM SHALL 展示 Provider 选择（远程 API / Ollama 本地）。

**REQ-V11-UI-002**  
WHEN 用户选择 Ollama，THE SYSTEM SHALL 展示 Ollama Base URL、Model 输入（或下拉），并提供「测试连接」操作；API Key 输入可隐藏或标注为可选。

**REQ-V11-UI-003**  
WHEN 用户选择远程 API，THE SYSTEM SHALL 保持现有 Base URL / Model / API Key 表单行为。

**REQ-V11-UI-004**  
WHEN 用户保存 Settings，THE SYSTEM SHALL 持久化 Provider 与对应字段，并提示保存成功；后续 Workspace 提问 / Workflow analyze 使用新 Provider，无需改分析页交互。

### 3.5 兼容与回归

**REQ-V11-COMPAT-001**  
WHEN 未设置 `llm_provider` 或值为 `api`，THE SYSTEM SHALL 与升级前行为等价（含默认 DeepSeek 类配置）。

**REQ-V11-COMPAT-002**  
THE SYSTEM SHALL 在无真实 Ollama 进程的 CI 环境中，用 mock HTTP 或单元夹具验证：provider 分支选择、Key 策略、Settings 读写与健康检查失败路径。

---

## 4. 建议决策（请确认）

| ID | 议题 | 建议 | 备选 |
|----|------|------|------|
| **D1** | Provider 配置键 | 新增 `llm_provider`: `api` \| `ollama` | 仅靠改 `llm_base_url` 指向 localhost（弱：无探测/无 Key 策略） |
| **D2** | Ollama 模型字段 | **复用 `llm_model`**（切换 provider 时改模型名）；另存 `ollama_base_url` | 独立 `ollama_model`，与 `llm_model` 分存便于来回切 |
| **D3** | Ollama 协议 | **优先 OpenAI Compatible**（`{base}/v1/chat/completions`），与现网路径统一 | 原生 `/api/chat`（需新 Provider） |
| **D4** | Tool calling | **尽力启用**；若所选本地模型不支持 tools，文档说明并建议具备 tool 能力的模型（如 qwen2.5 等）；不在本切片做复杂降级编排 | 本切片强制 legacy JSON 决策兜底 |
| **D5** | Settings 热更新 | `llm_provider`、`ollama_base_url` 纳入 HOT_FIELDS | 仅 `.env` 重启生效 |
| **D6** | Embedding / RAG | **本切片不改**；知识库仍走现有 embedding 配置 | Ollama embed 同步做 |
| **D7** | UI 范围 | **仅 Settings**；分析页不增加二次选择 | Workspace 顶栏也可临时切换 |

**已确认**：按建议锁定。见 `design.md` / `tasks.md`；回复 **「开始执行」** 后改代码。

---

## 5. 验收标准（摘要）

1. Settings 可将 Provider 设为 Ollama，保存后新分析 Run 走本地地址。  
2. 本地模式下无云 API Key 仍可发起调用（Ollama 已启动且模型已 pull）。  
3. 「测试连接」能反映 Ollama 可达/不可达；可达时可看到模型列表。  
4. `llm_provider=api` 时行为与现网一致。  
5. 相关单测在无真实 Ollama 下通过。

---

## 6. 变更记录

| 日期 | 变更 |
|------|------|
| 2026-09-21 | 立项 V11；初稿 `requirements.md`（待确认） |
| 2026-09-21 | 用户确认「按建议」；D1–D7 锁定 |
| 2026-09-21 | 执行完成；API 0.11.0 |
