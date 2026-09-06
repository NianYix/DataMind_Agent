# DataMind Agent — V6 Architecture Design

> 对应：`specs/v6/requirements.md`（**已确认**，D1–D6 按推荐锁定）  
> 基线：V5 + UI Optimize  
> 状态：**已确认并已实现**  
> 基线：V5 + UI Optimize  
> 非目标：MCP / SSO / OCR

---

## 1. 目标

```text
Upload doc (md/txt/pdf)
        │
        ▼
   extract + chunk
        │
        ▼
 embedding (openai_compatible | mock)
        │
        ▼
  Chroma (storage/chroma)
        │
        ▼
 knowledge_search Tool ──► Agent Trace / Evidence
        │
        ▼
 /knowledge UI + API
```

---

## 2. 已锁定决策

| # | 取值 |
|---|------|
| D1 | 做 RAG Knowledge |
| D2 | **Chroma** → `storage/chroma` |
| D3 | Embedding 默认 `openai_compatible`；CI **`mock`** |
| D4 | PDF：**pypdf** 抽文本 |
| D5 | 不做 MCP |
| D6 | Evaluation：**P1** 轻量 1–2 case（可与实现同期或紧随） |

---

## 3. 配置

`server/core/config.py` + `.env.example`：

| 键 | 默认 | 说明 |
|----|------|------|
| `EMBEDDING_PROVIDER` | `openai_compatible` | 或 `mock` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 兼容网关可改 |
| `EMBEDDING_BASE_URL` | 空则回落 `llm_base_url` | |
| `EMBEDDING_API_KEY` | 空则回落 `llm_api_key` | |
| `CHROMA_PATH` | `./storage/chroma` | |
| `RAG_CHUNK_SIZE` | `800` | 字符 |
| `RAG_CHUNK_OVERLAP` | `120` | |
| `RAG_TOP_K` | `5` | |
| `KNOWLEDGE_DIR` | `./storage/knowledge` | 原文文件 |

HOT_FIELDS 可选纳入：`embedding_provider`、`rag_top_k`（非必须本切片 UI 化）。

---

## 4. 数据模型

### `knowledge_bases`

| 字段 | 说明 |
|------|------|
| id | uuid |
| workspace_id | FK |
| name / description | |
| created_at | |

### `knowledge_documents`

| 字段 | 说明 |
|------|------|
| id | uuid |
| knowledge_base_id | FK |
| filename / file_path | |
| content_type | md/txt/pdf |
| status | `pending` \| `indexing` \| `ready` \| `error` |
| chunk_count | int |
| error | text 可空 |
| created_at | |

Chunk 正文以 Chroma metadata + document 存储为主；可选 `knowledge_chunks` 表做调试（P1，非必须）。

Chroma collection 命名：`kb_{knowledge_base_id}`；metadata：`doc_id`, `filename`, `chunk_index`, `workspace_id`。

---

## 5. 模块划分

```text
knowledge/
  extract.py      # md/txt/pdf → text
  chunking.py     # overlapping char chunks
  embeddings.py   # provider: openai_compatible | mock
  store.py        # Chroma upsert / query / delete_doc
  ingest.py       # pipeline orchestrator
server/services/knowledge_service.py
server/api/knowledge.py
tools/knowledge_search.py
tools/registry.py + agent/lc/tools.py  # 注册 Tool
apps/web/app/knowledge/page.tsx
samples/knowledge/east_china_metric.md  # 演示口径文档
```

### 5.1 Embedding

- `openai_compatible`：`httpx` POST `{base}/embeddings`（OpenAI 形状）；批量切小批。  
- `mock`：对文本 SHA256 → 固定维（如 64）float 向量，归一化；同文同向量。

### 5.2 Ingest 流程

1. 保存文件到 `KNOWLEDGE_DIR/{kb_id}/`  
2. status=`indexing`  
3. extract → chunk → embed → chroma upsert  
4. `chunk_count`、status=`ready`；异常 → `error` + audit  

上传后**同步 ingest**（V6 足够；异步队列非目标）。

### 5.3 `knowledge_search` Tool

```python
def knowledge_search(query, knowledge_base_id=None, top_k=None, workspace_id=None) -> dict
```

- 若未传 kb_id：检索该 workspace 下所有 ready 库（或默认库）。  
- 空库：`{success:True, results:[], message:"no documents"}`  
- 成功：`results:[{text, filename, doc_id, score, knowledge_base_id}]`

`ToolContext` 增加 `workspace_id`（从 conversation/dataset 反查），便于默认范围。

Agent 提示词增量：

- `SUPERVISOR_SYSTEM` / `TOOL_PICKER_SYSTEM`：口径/定义/制度类问题可调用 `knowledge_search`。  
- LangChain `build_tools` 注册该 Tool。

Evidence：tool 成功且有结果时，由现有 observe 路径或 tool 包装写入 claim（复用现有 Evidence 机制，最小改动）。

---

## 6. API

| Method | Path | 说明 |
|--------|------|------|
| GET/POST | `/api/knowledge-bases` | 列表 / 创建（`workspace_id`） |
| DELETE | `/api/knowledge-bases/{id}` | 删库 + chroma collection |
| GET | `/api/knowledge-bases/{id}/documents` | 文档列表 |
| POST | `/api/knowledge-bases/{id}/documents` | multipart 上传并 ingest |
| DELETE | `/api/knowledge-documents/{id}` | 删文档 + 向量 |
| POST | `/api/knowledge-bases/{id}/search` | 试检索 `{query, top_k}` |

鉴权：写操作走现有 `require_admin` 或成员策略（与 V5 一致：AUTH off 开放 Demo）。

---

## 7. 前端

- `/knowledge`：Workspace 选择、KB 创建、上传、文档状态表、试检索输入与结果卡片。  
- TopBar 增加 **Knowledge**。  
- 暗色 Token / AppShell 复用。  
- `lib/api.ts` 增加 knowledge helpers。

---

## 8. 依赖

```text
chromadb>=0.5.0
pypdf>=5.0.0
```

（embedding 用现有 httpx；不强制 langchain-community）

---

## 9. 测试

| 测项 | 方式 |
|------|------|
| chunking 边界 | unit |
| mock embedding 确定性 | unit |
| ingest md → ready + search hit | TestClient + EMBEDDING_PROVIDER=mock |
| 空库 search | unit |
| 回归 | 现有 pytest 全绿 |

样例：`samples/knowledge/east_china_metric.md`（含「华东」「口径」等词）。

P1：`evaluation/datasets` 增 `knowledge_suite` 1–2 case（可第二批）。

---

## 10. 实施顺序

```text
V6-0 Config + ORM + deps
V6-1 extract/chunk/embed/store/ingest
V6-2 Knowledge API
V6-3 Tool + Agent 提示词 + ToolContext.workspace_id
V6-4 /knowledge UI
V6-5 样例 + tests + README（P1 eval 可选）
```

---

## 11. 风险

| 风险 | 缓解 |
|------|------|
| Chroma 依赖体积/平台问题 | 锁定版本；失败时文档写明；测试用 mock |
| DeepSeek 无 embeddings 端点 | 配置独立 EMBEDDING_BASE_URL；Demo 用 mock |
| PDF 扫描件无字 | 明确不做 OCR；error 提示 |
| ToolContext 缺 workspace | conversation → workspace_id 注入 |

---

## 12. 确认方式

回复 **`确认设计`** 或 **`开始执行`**（后者视为设计与任务锁定并开工）。
