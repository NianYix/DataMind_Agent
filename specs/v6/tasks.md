# DataMind Agent — V6 Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 状态：**已执行**

---

## Phase V6-0 — 基础 `[P0]`

### T0.1 Config / deps
- [x] Settings：embedding / chroma / chunk / knowledge_dir
- [x] `requirements.txt`：chromadb、pypdf；`.env.example`
- **验收**：配置可读

### T0.2 ORM
- [x] `KnowledgeBase`、`KnowledgeDocument`；`init_db`
- **验收**：建表成功

---

## Phase V6-1 — RAG 管线 `[P0]`

### T1.1 extract / chunk / embed / store
- [x] `knowledge/extract.py`、`chunking.py`、`embeddings.py`、`store.py`
- [x] mock + openai_compatible
- **验收**：mock 单测

### T1.2 ingest
- [x] `knowledge/ingest.py` + `knowledge_service`
- [x] 上传 → ready/error；删文档清向量
- **验收**：md 样例入库可检索

---

## Phase V6-2 — API `[P0]`

### T2.1 Knowledge API
- [x] CRUD KB、上传文档、删除、search
- [x] 挂载 `server/main.py`；audit
- **验收**：TestClient mock 全路径

---

## Phase V6-3 — Agent Tool `[P0]`

### T3.1 knowledge_search
- [x] registry + LC StructuredTool
- [x] ToolContext.workspace_id；提示词增量
- **验收**：空库不 500；有库可返回 results

---

## Phase V6-4 — 前端 `[P1]`

### T4.1 `/knowledge` + TopBar
- [x] 暗色页：KB、上传、状态、试检索
- [x] `api.ts` helpers
- **验收**：手工可走通

---

## Phase V6-5 — 文档与回归 `[P0]`

### T5.1 样例 / README / pytest
- [x] `samples/knowledge/east_china_metric.md`
- [x] README V6 节；`pytest -q` 全绿
- [ ] （P1）knowledge eval suite 1–2 case — 未做，可后续补
- **验收**：CI mock 路径可复现

---

## 确认与执行

已收到 **「开始执行」** 并完成 V6 主路径。
