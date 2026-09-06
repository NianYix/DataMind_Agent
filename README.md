# DataMind Agent

AI 智能数据分析平台：自然语言 → **LangGraph Supervisor** → LangChain Tools（SQL/Python）→ 下钻 → 图表 / 报告 / Trace / Evidence。

Agent 默认引擎：**LangChain + LangGraph**（`AGENT_ENGINE=langchain`）。可回滚：`AGENT_ENGINE=legacy`。

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

- 分析台（暗色 Logic Workspace）：http://localhost:3000  
- Settings / Metrics：http://localhost:3000/settings  
- Evaluation：http://localhost:3000/evaluation  

前端为 **UI Optimize** 暗色工程工作台：TopBar + AgentPanel + Logic Canvas（Trace 只读节点图）+ Inspector + ExecutionBar。

- Data Sources：http://localhost:3000/data-sources  
- Prompts：http://localhost:3000/prompts  
- Login：http://localhost:3000/login  
- Knowledge（RAG）：http://localhost:3000/knowledge  
- MCP：http://localhost:3000/mcp  

## V8 Multi-Agent

| 能力 | 说明 |
|------|------|
| Handoff / Roster | Run 级 `agents_involved` + `handoffs`（写入 `state_json.multi_agent`） |
| Blackboard | Analyst/Insight/Critic 共享草稿；Inspector **Agents** Tab |
| Critic | `CRITIC_ENABLED`（默认关）；不通过则标风险并继续 Report |
| Prompts | 可覆盖 `system_analyst` / `system_insight` / `system_critic` |
| API | `GET /api/agent-runs/{id}/collaboration` |

```bash
# .env
MULTI_AGENT_ENABLED=true
CRITIC_ENABLED=false
```

## V7 MCP

| 能力 | 说明 |
|------|------|
| MCP Client | `MCP_ENABLED` + `storage/mcp_servers.json`（stdio）→ 桥接为 `mcp_<server>_<tool>` |
| Agent | 动态挂入 Tool Registry / LangChain；提示词附带工具目录 |
| API / UI | `/api/mcp/status` · `/tools` · `/reload`；页面 `/mcp` |
| Mock | `python -m mcp_host.mock_server`（`echo`）供 CI |
| MCP Server（P1） | `python -m server.mcp_server`：只读 `ping` + `knowledge_search` |

实现为 **Content-Length JSON-RPC 最小子集**（包名 `mcp_host`，避免与官方 `mcp` 包冲突）。官方 `mcp` SDK 仍列入依赖以备扩展。

```bash
# .env
MCP_ENABLED=false
MCP_CONFIG_PATH=./storage/mcp_servers.json

# 启用时复制样例：
# copy mcp_servers.example.json storage\mcp_servers.json
```

## V6 RAG Knowledge

| 能力 | 说明 |
|------|------|
| 知识库 | Workspace 级 KB；上传 `.md` / `.txt` / `.pdf` |
| 管线 | 切分 → Embedding → **Chroma**（`storage/chroma`） |
| Tool | Agent `knowledge_search`（口径/定义类问题） |
| Embedding | `EMBEDDING_PROVIDER=mock`（CI/默认 Demo）或 `openai_compatible` |

样例文档：`samples/knowledge/east_china_metric.md`

```bash
# .env
EMBEDDING_PROVIDER=mock
CHROMA_PATH=./storage/chroma
KNOWLEDGE_DIR=./storage/knowledge
```

## V5 企业切片

| 能力 | 说明 |
|------|------|
| Data Sources | MySQL / PostgreSQL / **mock** 连接；测试连接；表注册为 Dataset |
| Prompts | `system_analyst` 版本化 + 激活，注入 Planner |
| HTTP Tool | `http_request`（`HTTP_URL_ALLOWLIST`）；`WEB_SEARCH_ENABLED` 默认关 |
| Auth | `AUTH_ENABLED=false` 默认；开启后 JWT + 种子 `admin`/`admin` |

驱动：`pymysql`、`psycopg`（见 `requirements.txt`）。无真实库时用 `db_type=mock` 验收。

```bash
# .env
AUTH_ENABLED=false
HTTP_URL_ALLOWLIST=https://httpbin.org/,https://api.github.com/
WEB_SEARCH_ENABLED=false
```

## 测试数据

- `samples/sales.csv` — 合成电商下降场景  
- `samples/superstore_clean.csv` — 公开 Superstore 清洗版  
- `samples/sales.sqlite` — SQLite 源（表名 `sales`）  
- `samples/knowledge/east_china_metric.md` — RAG 口径样例  

## Evaluation（V4）

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

## Agent 引擎

| 值 | 说明 |
|----|------|
| `langchain`（默认） | LangGraph StateGraph + ChatOpenAI + StructuredTool |
| `legacy` | 自研 `agent/runtime.py` |

## 文档

- V1–V3：`specs/`、`specs/v2/`、`specs/v3/`  
- V4 Evaluation：`specs/v4/`  
- UI Optimize：`specs/ui_optimize/`  
- V5 Enterprise：`specs/v5/`  
- V6 RAG：`specs/v6/`  
- LangChain 重构：`specs/langchain/`  

## 测试

```bash
pytest -q
```

## 原则

数值结论必须来自工具真实执行，而非 LLM 直接计算。
