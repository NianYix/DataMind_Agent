# DataMind Agent — V2 Implementation Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 执行门槛：仅当用户明确回复 **「开始执行」** 后，方可改业务代码

---

## Phase V2-0 — 基础扩展 `[P0]`

### T0.1 配置与模型字段
- [ ] `.env.example` 增加 price / duckdb 配置
- [ ] `Settings` 读取新配置
- [ ] `datasets` 增加 `source_type` / `table_name`（兼容迁移）
- [ ] `agent_runs` 增加 `estimated_cost` / `cancel_requested`（或等价 state 字段）
- **验收**：旧 DB 可启动；新字段可读可写

### T0.2 Cancel 注册表
- [ ] `agent/cancel.py`
- [ ] `POST /api/agent-runs/{id}/cancel`
- **验收**：cancel 后 flag 可读；Run 状态可标 cancelled

---

## Phase V2-1 — Gateway Tool Calling `[P0]`

### T1.1 Provider / Gateway 支持 tools
- [ ] `ChatResult.tool_calls`
- [ ] `openai_compatible.chat(..., tools=)`
- [ ] Gateway 透传
- **验收**：对支持 tools 的模型能解析 tool_calls（可用 mock 单测）

### T1.2 Tool Schemas + Registry 统一
- [ ] `tools/schemas.py`
- [ ] `ToolContext` + `run_tool`
- [ ] 接入既有 schema/preview/python/chart
- **验收**：按名称执行工具返回结构化结果

---

## Phase V2-2 — SQL / Statistics / Anomaly `[P0/P1]`

### T2.1 SQL Guard + sql_query `[P0]`
- [ ] `tools/sql_guard.py`（仅 SELECT/WITH）
- [ ] DuckDB 查询文件 Dataset（表名 `data`）
- [ ] 依赖 `duckdb` 写入 requirements
- **验收**：合法聚合成功；`DELETE` 被拒绝

### T2.2 SQLite Dataset 注册 `[P1]`
- [ ] 上传 `.db/.sqlite` + `table_name` API
- [ ] Profiler 适配 SQLite 表
- [ ] `samples/sales.sqlite` 生成脚本/文件
- **验收**：注册后可 Profile；可 sql_query

### T2.3 statistics / anomaly_detection `[P0]`
- [ ] 实现并注册到 schemas
- **验收**：可对 sales 列产出摘要 / 异常计数

---

## Phase V2-3 — Supervisor Runtime `[P0]`

### T3.1 Supervisor 决策模块
- [ ] `agent/supervisor.py`（tools 优先 + JSON fallback）
- [ ] Trace 记录 reason
- **验收**：给定 state mock 能产出合法 action

### T3.2 重写/升级 Runtime Loop
- [ ] 接入 Supervisor、工具执行、observe、insight、report
- [ ] 检查 cancel / MAX_STEPS / RUN_TIMEOUT
- [ ] 保留 Evidence / Chart / SSE 事件（增加 supervisor、cancelled）
- **验收**：无 LLM mock 下状态机能走到 finish；真 LLM 下 DEMO-001 可跑

### T3.3 Memory LLM 更新 `[P0]`
- [ ] `agent/memory.py`
- [ ] 发消息前更新 context_json
- **验收**：追问「只看华东」写入 filters；后续 prompt 含该约束

---

## Phase V2-4 — Observability & Export `[P0/P1]`

### T4.1 Cost 汇总 `[P0]`
- [ ] Run 结束计算 estimated_cost
- [ ] SSE final / GET run 返回 tokens、latency、cost
- **验收**：UI 或 API 可见

### T4.2 结构化日志 `[P1]`
- [ ] run/step/tool 关键日志
- **验收**：控制台可按 run_id 检索

### T4.3 PDF 导出 `[P1]`
- [ ] `report_export.py` + `GET .../report.pdf`
- [ ] 依赖加入 requirements
- **验收**：下载 PDF 非空

---

## Phase V2-5 — 前端增量 `[P0/P1]`

### T5.1 取消 + Run 摘要 `[P0]`
- [ ] 分析中 Cancel 按钮
- [ ] 展示 tokens / latency / cost
- **验收**：取消后 UI 显示 cancelled

### T5.2 历史 Run + Evidence 列表 `[P0]`
- [ ] 拉取 runs / evidences
- [ ] 点选回看 trace/charts/report/evidence
- **验收**：完成一次分析后可回看

### T5.3 SQLite 注册入口 + PDF 按钮 `[P1]`
- [ ] 侧栏上传 sqlite + 表名
- [ ] 导出 PDF
- **验收**：DEMO-002/004 可操作

---

## Phase V2-6 — 测试与验收 `[P0]`

### T6.1 自动化测试
- [ ] sql_guard / duckdb select / cancel / cost
- [ ]（可选）mock tool_calls integration
- **验收**：`pytest -q` 通过

### T6.2 Demo 清单
- [ ] DEMO-001：销售下降 + Supervisor + 非 Python 工具
- [ ] DEMO-002：SQLite 源分析
- [ ] DEMO-003：中途取消
- [ ] DEMO-004：PDF + 历史 Evidence
- **验收**：人工勾选通过；更新 README V2 说明

---

## 建议顺序

```text
V2-0 → V2-1 → V2-2(sql+stats) → V2-3 → V2-4 → V2-5 → V2-6
                 ↘ T2.2 SQLite 可并行靠后
```

---

## 确认与执行

1. 审阅任务；需调整指出编号。  
2. 回复 **`确认任务`** 或 **`开始执行`**：  
   - `确认任务`：锁定清单  
   - `开始执行`：从 Phase V2-0 起改代码  

**未收到「开始执行」前，不修改业务代码。**
