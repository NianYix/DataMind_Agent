# DataMind Agent — V6 Tasks

> 对应：`requirements.md`（已确认，D1–D6 推荐）+ `design.md`  
> 执行门槛：仅当用户明确回复 **「开始执行」** 后改业务代码

---

## Phase V6-0 — 基础 `[P0]`

### T0.1 Config / deps
- [ ] Settings：embedding / chroma / chunk / knowledge_dir
- [ ] `requirements.txt`：chromadb、pypdf；`.env.example`
- **验收**：配置可读

### T0.2 ORM
- [ ] `KnowledgeBase`、`KnowledgeDocument`；`init_db`
- **验收**：建表成功

---

## Phase V6-1 — RAG 管线 `[P0]`

### T1.1 extract / chunk / embed / store
- [ ] `knowledge/extract.py`、`chunking.py`、`embeddings.py`、`store.py`
- [ ] mock + openai_compatible
- **验收**：mock 单测

### T1.2 ingest
- [ ] `knowledge/ingest.py` + `knowledge_service`
- [ ] 上传 → ready/error；删文档清向量
- **验收**：md 样例入库可检索

---

## Phase V6-2 — API `[P0]`

### T2.1 Knowledge API
- [ ] CRUD KB、上传文档、删除、search
- [ ] 挂载 `server/main.py`；audit
- **验收**：TestClient mock 全路径

---

## Phase V6-3 — Agent Tool `[P0]`

### T3.1 knowledge_search
- [ ] registry + LC StructuredTool
- [ ] ToolContext.workspace_id；提示词增量
- **验收**：空库不 500；有库可返回 results

---

## Phase V6-4 — 前端 `[P1]`

### T4.1 `/knowledge` + TopBar
- [ ] 暗色页：KB、上传、状态、试检索
- [ ] `api.ts` helpers
- **验收**：手工可走通

---

## Phase V6-5 — 文档与回归 `[P0]`

### T5.1 样例 / README / pytest
- [ ] `samples/knowledge/east_china_metric.md`
- [ ] README V6 节；`pytest -q` 全绿
- [ ] （P1）knowledge eval suite 1–2 case
- **验收**：CI mock 路径可复现

---

## 建议顺序

```text
V6-0 → V6-1 → V6-2 → V6-3 → V6-4 → V6-5
```

---

## 确认与执行

回复 **`确认设计`** 或 **`开始执行`**。  
**未收到「开始执行」前不修改业务代码。**
