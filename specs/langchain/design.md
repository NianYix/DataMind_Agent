# DataMind Agent — LangChain / LangGraph 重构设计

> 对应需求：`specs/langchain/requirements.md`（已确认）  
> 状态：待审阅

---

## 1. 目标架构

```text
ChatService.stream_analysis
        │
        ▼
  AgentRuntimeFacade  (AGENT_ENGINE)
        │
   ┌────┴────┐
   ▼         ▼
 LangGraph  Legacy
  Runtime   runtime.py (保留)
   │
   ▼
┌──────────────────────────────────┐
│  StateGraph                      │
│  understand → plan → agent_loop  │
│       ↑            │             │
│       └── replan ←─┤             │
│                    ▼             │
│              tools / observe     │
│                    ▼             │
│         insight → report → END   │
└──────────────────────────────────┘
   │              │
   ▼              ▼
 ChatOpenAI    StructuredTools
 (DeepSeek)    → tools/registry + sandbox
```

原则：

- **产品行为不变**：SSE 事件、DB Trace、Evidence、Cancel、步数/超时。  
- **替换内核**：LLM 调用与编排走 LangChain/LangGraph。  
- **复用**：Sandbox、sql_guard、profiler、ORM、前端。

---

## 2. 依赖

```text
langchain-core
langchain-openai
langgraph
```

版本在实现时锁定较新的稳定版；写入 `requirements.txt`。

环境变量新增：

```text
AGENT_ENGINE=langchain   # langchain | legacy
```

---

## 3. 模块划分

```text
agent/
  runtime.py              # legacy（保留）
  facade.py               # 按 AGENT_ENGINE 分发
  lc/
    __init__.py
    llm.py                # 构建 ChatOpenAI
    tools.py              # StructuredTool 工厂（闭包注入 ToolContext）
    state.py              # TypedDict / Pydantic Graph State
    graph.py              # build_graph() / compile
    nodes.py              # understand/plan/call_model/tools/observe/insight/report
    callbacks.py          # 把节点事件 → AgentEvent + DB persist
    runtime.py            # LangGraphAgentRuntime.run_stream()
```

旧 `llm/gateway.py`：langchain 路径可不走；legacy 继续用。可后续统一。

---

## 4. Graph State

```python
class GraphState(TypedDict, total=False):
    run_id: str
    conversation_id: str
    question: str
    dataset_id: str
    dataset_path: str
    source_type: str
    table_name: str | None
    schema_info: dict
    profile_summary: str
    memory: dict
    plan: list[dict]          # [{id, description, status}]
    observations: list[dict]
    messages: list            # LangChain messages（tool calling 用）
    step_count: int
    input_tokens: int
    output_tokens: int
    used_non_python_tool: bool
    final_answer: str | None
    report_markdown: str | None
    status: str               # running|done|error|cancelled
    error: str | None
    pending_tool_calls: list  # 可选
```

与现有 `AgentState` 双向映射：进入 Graph 前 `to_graph_state`，结束后/流式过程中 `persist`。

---

## 5. 节点设计

| 节点 | 职责 |
|------|------|
| `understand` | dataset_schema tool（可直接调 registry，不必经 LLM） |
| `plan` | LLM JSON → plan steps（可用 `with_structured_output`） |
| `supervisor` | 决定 `call_tools` / `insight` / `end`（结构化输出） |
| `agent` | bind_tools 的 ChatOpenAI，产出 AIMessage + tool_calls |
| `tools` | LangGraph `ToolNode` 或自研执行器（推荐自研以便写 audit + Evidence） |
| `observe` | 分析工具结果，更新 observations，可能追加 plan（replan） |
| `insight` | 结构化洞察 + final_answer |
| `report` | Markdown 报告 |
| `finalize` | status=done，写 Report ORM |

### 边（简化）

```text
START → understand → plan → supervisor
supervisor → agent | insight | END(cancelled/timeout)
agent → tools → observe → supervisor
insight → report → finalize → END
```

Cancel / MAX_STEPS / RUN_TIMEOUT：在 `supervisor` 入口检查（读 cancel registry + state.step_count + elapsed）。

---

## 6. Tools 包装

`agent/lc/tools.py`：

```python
def build_tools(ctx: ToolContext) -> list[BaseTool]:
    # 每个 tool 内部 call tools.registry.run_tool(name, args, ctx)
```

参数 schema 与现有 `tools/schemas.py` 对齐，避免模型侧能力回退。

`python_execute` / `sql_query` 仍进 sandbox；成功非 python 工具时置 `used_non_python_tool=True`。

---

## 7. LLM 工厂

```python
def get_chat_model() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.llm_model,
        api_key=s.llm_api_key,
        base_url=s.llm_base_url.rstrip("/") + "/v1",  # 视 SDK 要求调整
        temperature=0.2,
    )
```

Token：从 `AIMessage.response_metadata` / `usage_metadata` 累加到 state。

---

## 8. 流式与持久化

`LangGraphAgentRuntime.run_stream`：

1. 创建/更新 `AgentRun`  
2. `for event in graph.stream(state, stream_mode="updates")`（或 nodes 内主动 `emit`）  
3. 映射为现有 `AgentEvent`：`step` / `observation` / `chart` / `final` / `error`  
4. 节点内调用现有 `_add_step` / `ToolCall` / `Evidence` 写入逻辑（抽到 `agent/persist.py` 供 legacy 与 lc 共用更佳）

为减少大爆炸：第一版可在 nodes 里直接用 Session 写库（与 legacy 相同模式），后续再抽 persist。

---

## 9. Facade

```python
# agent/facade.py
def create_runtime(db: Session) -> AgentRuntimeProtocol:
    if get_settings().agent_engine == "legacy":
        from agent.runtime import AgentRuntime
        return AgentRuntime(db)
    from agent.lc.runtime import LangGraphAgentRuntime
    return LangGraphAgentRuntime(db)
```

`chat_service.stream_analysis` 改为依赖 facade。

---

## 10. 配置

`Settings.agent_engine: str = "langchain"`

`.env.example` 增加 `AGENT_ENGINE=langchain`。

---

## 11. 测试策略

| 测试 | 内容 |
|------|------|
| 保留 | sandbox / sql_guard / profiler |
| 新增 | `build_tools` 可调用；graph 在 mock LLM 下能从 plan 走到 finalize |
| 手动 | DEMO：superstore / sales + Trace 可见 tool |

---

## 12. 风险与缓解

| 风险 | 缓解 |
|------|------|
| DeepSeek tool_calls 与 LC 差异 | 保留 JSON fallback 节点（supervisor 指定 preferred_tool + 手工组 args） |
| stream 与 DB Session 线程问题 | 保持同步 stream，单线程写 Session |
| 包体积/版本冲突 | 精简依赖，锁版本 |
| 回归 | `AGENT_ENGINE=legacy` 快速回滚 |

---

## 13. 实施顺序（摘要）

见 `tasks.md`：依赖 → llm/tools → graph nodes → runtime/facade → chat_service 切换 → 测试/README。

---

## 14. 确认方式

回复 **`确认设计`** / 指出修改；或直接 **`开始执行`**（视为设计与任务一并锁定并开工）。
