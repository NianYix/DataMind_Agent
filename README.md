# DataMind Agent

AI 智能数据分析平台：自然语言 → **LangGraph Supervisor** → LangChain Tools（SQL/Python）→ 下钻 → 图表 / 报告 / Trace / Evidence。

Agent 默认引擎：**LangChain + LangGraph**（`AGENT_ENGINE=langchain`）。可回滚：`AGENT_ENGINE=legacy`。

**原则**：数值结论必须来自工具真实执行，而非 LLM 直接计算。

---

## 快速开始

### Windows

```bat
start.bat
```

### 手动

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# 编辑 .env：LLM_API_KEY=...
# AGENT_ENGINE=langchain   # 或 legacy

uvicorn server.main:app --reload --port 8000
```

```bash
cd apps/web && pnpm install && pnpm dev
```

| 入口 | URL |
|------|-----|
| 分析台（Logic Workspace） | http://localhost:3000 |
| Knowledge / Workflows / MCP | `/knowledge` · `/workflows` · `/mcp` |
| Data Sources / Prompts / Settings | `/data-sources` · `/prompts` · `/settings` |
| Evaluation / Login | `/evaluation` · `/login` |

前端为暗色工程工作台：TopBar + AgentPanel + Logic Canvas（Trace 只读）+ Inspector + ExecutionBar。

---

## 功能一览：意义与使用

下面按「你为什么需要它 → 怎么用」说明各阶段能力。日常分析从 **Workspace** 开始；企业连接、知识库、MCP、工作流按需叠加。

### 1. Logic Workspace（分析台）

**意义**：把「问一句业务问题 → 自动规划、调工具、下钻、出图/报告」做成可观测的 Agent Run，避免黑盒聊天。

**使用**：

1. 打开 `/`，上传 CSV/Excel 或选已有 Dataset（也可挂 SQLite / 远程表）。  
2. **可多选 Dataset**（勾选 +「设为主」）：同一次提问联合多表；SQL 用 `data` / `data_2`…，Python 用 `df` / `df_2`…。  
3. 输入问题（如「为什么 8 月销售下降？」）→ **Run**。  
4. 左侧看对话与计划；中间 Canvas 看 Trace；右侧 Inspector 看 Context（绑定主/辅表）/ Evidence / Charts / Report / **Agents**。  
5. 需要停跑时点 **Stop**。

### 2. Multi-Dataset 同 Run（V10）

**意义**：Workspace 里多个已上传文件可在一次分析中对比或 JOIN，不必先外部合并。

**使用**：

1. Datasets 列表勾选 1–5 个表，点「设为主」指定 primary（默认 `data` / `df`）。  
2. 改选集合会新建会话（不改写历史 Run）。  
3. 提问即可；Inspector → Context 可见主/辅绑定。  
4. 上限：`MAX_DATASETS_PER_CONVERSATION=5`（默认）。远程多源本阶段不支持，请用 CSV/Excel/SQLite。

```bash
MAX_DATASETS_PER_CONVERSATION=5
```

### 3. Multi-Agent 协作（V8）

**意义**：一次分析由 Planner / Supervisor / Tools / Analyst / Insight / Report（可选 Critic）接力；交接与黑板可回看，便于审计「谁做了什么、依据是什么」。

**使用**：

1. 默认 `MULTI_AGENT_ENABLED=true`，跑完一次分析即可。  
2. Inspector → **Agents**：查看 `agents_involved`、handoffs、blackboard。  
3. 需要复核质量时设 `CRITIC_ENABLED=true`（Insight 后多一步 Critic；不通过则标风险并继续出报告）。  
4. 可用 Prompts 页覆盖 `system_insight` / `system_critic`（及 Planner 用的 `system_analyst`）。

```bash
MULTI_AGENT_ENABLED=true
CRITIC_ENABLED=false
```

### 4. AI Workflow（V9）

**意义**：把重复分析固化成可保存、可复跑的流程（绑定问题/数据 → analyze → 可选条件分支），适合周报归因、固定口径复检，而不必每次从零对话。

**使用**：

1. 打开 `/workflows`，从模板创建（如「标准销售归因分析」）。  
2. 必要时编辑右侧 Graph JSON（节点：`start` / `analyze` / `condition` / `end`）。  
3. 选择 Dataset、可覆盖 Question → **Run**；下方查看逐步状态。  
4. 无 LLM / CI：`.env` 设 `WORKFLOW_MOCK_ANALYZE=true`。

```bash
WORKFLOW_MOCK_ANALYZE=false
WORKFLOW_TIMEOUT_SEC=600
```

API：`GET /api/workflow-templates`、`POST /api/workflows`、`POST /api/workflows/{id}/runs`。

### 5. MCP 集成（V7）

**意义**：让 Agent 调用外部 MCP Server 工具（扩展能力），也可把 DataMind 只读能力以 MCP Server 形式暴露给 Cursor 等宿主。

**使用（Client）**：

1. `copy mcp_servers.example.json storage\mcp_servers.json`  
2. `.env`：`MCP_ENABLED=true`，按需改 command/args。  
3. 重启后端 → 打开 `/mcp` 看 Server 状态与桥接工具名（`mcp_<server>_<tool>`）。  
4. 在 Workspace 提问时，Agent 可选用这些工具。

**使用（Server P1）**：

```bash
python -m server.mcp_server
# 对外只读：ping、knowledge_search
```

本地 Demo Server：`python -m mcp_host.mock_server`（工具 `echo`）。

```bash
MCP_ENABLED=false
MCP_CONFIG_PATH=./storage/mcp_servers.json
```

### 6. RAG 知识库（V6）

**意义**：把口径、制度、指标定义等文档入库；问「华东口径包含哪些省市」时走检索，而不是只靠模型记忆，减少幻觉。

**使用**：

1. 打开 `/knowledge`，创建知识库 → 上传 `.md` / `.txt` / `.pdf`。  
2. 用页内「试检索」验证；样例：`samples/knowledge/east_china_metric.md`。  
3. 回到 Workspace 提问定义/口径类问题，Agent 会调 `knowledge_search`。  
4. Demo/CI：`EMBEDDING_PROVIDER=mock`；生产可改 `openai_compatible`。

```bash
EMBEDDING_PROVIDER=mock
CHROMA_PATH=./storage/chroma
KNOWLEDGE_DIR=./storage/knowledge
```

### 7. 企业切片（V5）

**意义**：对接真实库表、版本化系统提示词、受控 HTTP 工具与可选登录，便于从「本地 CSV Demo」过渡到团队试用。

**使用**：

| 能力 | 怎么用 |
|------|--------|
| Data Sources | `/data-sources`：添加 MySQL/PG/`mock` → 测试连接 → 选表注册为 Dataset → Workspace 选用 |
| Prompts | `/prompts`：创建并激活 `system_analyst`（Planner）；亦可维护 insight/critic |
| HTTP | Agent 工具 `http_request`；URL 须在 `HTTP_URL_ALLOWLIST` 内 |
| Auth | `AUTH_ENABLED=true` 后走 `/login`；种子账号 `admin` / `admin` |

```bash
AUTH_ENABLED=false
HTTP_URL_ALLOWLIST=https://httpbin.org/,https://api.github.com/
WEB_SEARCH_ENABLED=false
```

### 8. Evaluation（V4）

**意义**：用固定 Suite 回归「分析质量与工具成功率」，区分 mock（CI）与 live（真 LLM），避免改 Agent 后无感知退化。

**使用**：

```bash
python -m evaluation --list
python -m evaluation --suite sales_suite --mode mock
```

或打开 `/evaluation` 选择 suite / mode 启动。详见下文「Evaluation」一节。

### 9. Settings / Metrics

**意义**：热调模型与超时等运维参数，并查看 Run/工具成功率，方便排障。

**使用**：打开 `/settings`；若配置了 `APP_API_KEY`，写操作需带 `X-API-Key`。Multi-Agent / Critic 开关以 `.env` 为准（页内只读展示）。

---

## 版本能力速查（配置表）

### V10 Multi-Dataset

| 能力 | 说明 |
|------|------|
| 绑定 | `dataset_ids` + primary（`Conversation.dataset_id`） |
| SQL / Python | `data`/`data_2`… · `df`/`df_2`… |
| 上限 | `MAX_DATASETS_PER_CONVERSATION`（默认 5） |
| UI | Workspace 多选 + 主表；Inspector Context |

### V9 AI Workflow

| 能力 | 说明 |
|------|------|
| 定义 | Workspace 级 JSON DAG |
| 执行 | 同步 Engine + `workflow_run_steps` |
| Analyze | 复用 Agent；可 mock |
| 模板 | `standard_analysis`、`condition_branch` |

### V8 Multi-Agent

| 能力 | 说明 |
|------|------|
| Handoff / Roster | `state_json.multi_agent` |
| Blackboard | Inspector Agents |
| Critic | `CRITIC_ENABLED` |
| API | `GET /api/agent-runs/{id}/collaboration` |

### V7 MCP

| 能力 | 说明 |
|------|------|
| Client | stdio → `mcp_*` 工具 |
| UI | `/mcp` |
| Server P1 | `python -m server.mcp_server` |

实现为 Content-Length JSON-RPC 最小子集（包名 `mcp_host`，避免与 PyPI `mcp` 冲突）。

### V6 RAG Knowledge

| 能力 | 说明 |
|------|------|
| 管线 | 切分 → Embedding → Chroma |
| Tool | `knowledge_search` |

### V5 企业切片

| 能力 | 说明 |
|------|------|
| Data Sources | MySQL / PostgreSQL / mock |
| Prompts | 版本化 + 激活 |
| HTTP / Auth | Allowlist；可选 JWT |

驱动：`pymysql`、`psycopg`。无真实库时用 `db_type=mock`。

---

## 测试数据

- `samples/sales.csv` — 合成电商下降场景  
- `samples/superstore_clean.csv` — 公开 Superstore 清洗版  
- `samples/sales.sqlite` — SQLite 源（表名 `sales`）  
- `samples/knowledge/east_china_metric.md` — RAG 口径样例  

---

## Evaluation（V4）详解

可复跑评测：Suite JSON → Runner（mock / live）→ 启发式 scorers → `eval_runs` 落库 → API / UI。

### CLI

```bash
python -m evaluation --list
python -m evaluation --suite sales_suite --mode mock
```

### API

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/evaluation-suites` | 可用 suite |
| POST | `/api/evaluations` | `{suite_id, mode}`；若配置了 `APP_API_KEY` 需 `X-API-Key` |
| GET | `/api/evaluations` | 历史 |
| GET | `/api/evaluations/{id}` | 详情 + cases |
| GET | `/api/evaluations/{id}/summary` | 仅汇总 |

### Mode

| Mode | 说明 |
|------|------|
| `mock` | 不调 LLM；按 `expect.must_mention` 生成答案，适合 CI |
| `live` | 走真实 `create_runtime`（需 LLM Key） |

### 指标含义

| 指标 | 含义 |
|------|------|
| Task Success | `must_mention`（及 numbers）全部命中 |
| Tool / Python / SQL Success | 工具调用成功率 |
| Insight / Calculation / Hallucination | **heuristic** 启发式，非 LLM-as-judge |
| Avg Steps / Latency / Tokens | case 算术平均 |

Suite 定义：`evaluation/datasets/sales_suite.json`。

---

## Agent 引擎

| 值 | 说明 |
|----|------|
| `langchain`（默认） | LangGraph StateGraph + ChatOpenAI + StructuredTool |
| `legacy` | 自研 `agent/runtime.py` |

---

## 文档（specs）

| 阶段 | 路径 |
|------|------|
| V1–V3 | `specs/`、`specs/v2/`、`specs/v3/` |
| V4 Evaluation | `specs/v4/` |
| UI Optimize | `specs/ui_optimize/` |
| LangChain | `specs/langchain/` |
| V5 Enterprise | `specs/v5/` |
| V6 RAG | `specs/v6/` |
| V7 MCP | `specs/v7/` |
| V8 Multi-Agent | `specs/v8/` |
| V9 Workflow | `specs/v9/` |
| V10 Multi-Dataset | `specs/v10/` |

需求 / 设计 / 任务均在对应目录的 `requirements.md` · `design.md` · `tasks.md`。

未立项想法见 **需求池**：[`specs/backlog.md`](specs/backlog.md)。

---

## 测试

```bash
pytest -q
```
