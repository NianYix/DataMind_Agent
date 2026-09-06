# DataMind Agent — LangChain 重构任务

> 对应：`requirements.md`（已确认）+ `design.md`  
> 执行门槛：仅当用户明确回复 **「开始执行」** 后改业务代码

---

## Phase LC-0 — 依赖与开关 `[P0]`

### T0.1 依赖与配置
- [ ] `requirements.txt` 增加 `langchain-core`、`langchain-openai`、`langgraph`
- [ ] `Settings.agent_engine` + `.env.example` `AGENT_ENGINE`
- **验收**：安装成功；默认 `langchain`

### T0.2 Facade 骨架
- [ ] `agent/facade.py` + Protocol
- [ ] `chat_service` 改为通过 facade 创建 runtime（先仍指向 legacy 也可，T3 再切）
- **验收**：`AGENT_ENGINE=legacy` 行为与现网一致

---

## Phase LC-1 — LLM & Tools `[P0]`

### T1.1 Chat model 工厂
- [ ] `agent/lc/llm.py`：`ChatOpenAI` + settings
- **验收**：配置 key 后可单次 `invoke`（可手工）

### T1.2 StructuredTool 包装
- [ ] `agent/lc/tools.py`：7 个工具绑定 `ToolContext`
- **验收**：直接 `tool.invoke` 跑 `dataset_schema` / `sql_query` 成功

---

## Phase LC-2 — LangGraph `[P0]`

### T2.1 State + Nodes
- [ ] `agent/lc/state.py`、`nodes.py`
- [ ] understand / plan / supervisor / agent / tools / observe / insight / report / finalize
- **验收**：mock LLM 下图可编译

### T2.2 Graph 组装
- [ ] `agent/lc/graph.py`：`build_analysis_graph()`
- [ ] cancel / max_steps / timeout 在 supervisor
- **验收**：单元测试 compile + 空跑路径不崩

---

## Phase LC-3 — Runtime 对接 `[P0]`

### T3.1 LangGraphAgentRuntime
- [ ] `agent/lc/runtime.py`：`run_stream` → SSE AgentEvent + DB Trace
- [ ] Evidence / Chart / Report 落库兼容
- **验收**：与前端现有 SSE 字段兼容

### T3.2 切换默认引擎
- [ ] facade 默认 langchain；legacy 可回滚
- [ ] README 说明 `AGENT_ENGINE`
- **验收**：DEMO-001/002（真实 LLM）

---

## Phase LC-4 — 测试与清理 `[P1]`

### T4.1 测试
- [ ] tools 包装单测；graph mock 测试
- [ ] 回归 sandbox / sql_guard
- **验收**：`pytest -q` 通过

### T4.2 文档
- [ ] README：LangChain/LangGraph 架构一句 + 回滚方式
- [ ] 旧 `llm_ops` 标注可选废弃（不强制删）

---

## 建议顺序

```text
LC-0 → LC-1 → LC-2 → LC-3 → LC-4
```

---

## 确认与执行

回复 **`确认任务`** 或 **`开始执行`**。  
**未收到「开始执行」前不修改业务代码。**
