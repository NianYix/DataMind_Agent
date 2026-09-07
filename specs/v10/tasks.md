# DataMind Agent — V10 Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 状态：**已执行**  
> 决策：D1–D7 建议默认已锁定

---

## Phase V10-0 — 契约与配置 `[P0]`

### T0.1 Config
- [x] `MAX_DATASETS_PER_CONVERSATION`（Settings + `.env.example`）

### T0.2 绑定工具模块
- [x] `server/services/dataset_binding.py`

### T0.3 Schema / create_conversation
- [x] `ConversationCreate` / `ConversationOut`；`chat_service` 写 `dataset_ids`

---

## Phase V10-1 — 运行时与沙箱 `[P0]`

### T1.1–T1.5
- [x] AgentState / ToolContext.sources；SQL 多表；Python 多帧；schema/preview alias；prompt 注入

---

## Phase V10-2 — 前端 `[P1]`

### T2.1–T2.3
- [x] api.ts；AgentPanel 多选+主表；Inspector Context 绑定列表

---

## Phase V10-3 — 文档与回归 `[P0]`

### T3.1
- [x] API **0.10.0**；README；`tests/test_multi_dataset.py`；BL-001 已完成

---

## 确认与执行

已收到 **「开始执行」** 并完成 V10 主路径。
