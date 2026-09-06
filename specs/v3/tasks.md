# DataMind Agent — V3 Implementation Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 执行门槛：仅当用户明确回复 **「开始执行」** 后，方可改业务代码

---

## Phase V3-0 — 基础与审计表 `[P0]`

### T0.1 配置扩展
- [ ] `.env.example`：`APP_API_KEY`、`LARGE_FILE_MB`、`PROFILE_SAMPLE_ROWS`、`LOG_DIR`、`SETTINGS_PATH`
- [ ] `Settings` 模型读取；`settings.json` 覆盖逻辑骨架
- **验收**：无 settings.json 时行为与 V2 一致

### T0.2 Audit 表 + 日志
- [ ] ORM `audit_events` + 迁移
- [ ] `logging_setup` 滚动文件
- [ ] `audit_service.record(...)`
- **验收**：启动后可写一条 audit；日志文件生成

### T0.3 API Key 中间件/依赖
- [ ] `require_api_key`
- **验收**：配置 key 后无头请求 PUT settings 返回 401

---

## Phase V3-1 — Sandbox 统一 `[P0]`

### T1.1 errors + python_runner
- [ ] 错误码 SECURITY/TIMEOUT/RUNTIME/OUTPUT
- [ ] 包装 executor；可选 memory limit
- [ ] 失败写 audit
- **验收**：`import os` → SECURITY；单测通过

### T1.2 sql_runner
- [ ] 统一只读 + max_rows + timeout
- [ ] registry 改走 runner
- **验收**：写 SQL 拒绝并 audit

---

## Phase V3-2 — Settings `[P0/P1]`

### T2.1 Settings API `[P0]`
- [ ] GET 脱敏 / PUT 持久化 + cache_clear + gateway 重置
- **验收**：改 model 名后 GET 可见

### T2.2 Settings 前端页 `[P1]`
- [ ] `/settings` 表单 + 保存（带 X-API-Key 输入）
- **验收**：DEMO-002 可操作

---

## Phase V3-3 — Export / Metrics / Large Data `[P0/P1]`

### T3.1 Trace Export `[P0]`
- [ ] `GET /api/agent-runs/{id}/export`
- [ ] 前端导出按钮
- **验收**：JSON 含 run/steps/tools

### T3.2 Metrics API + UI `[P0/P1]`
- [ ] `GET /api/metrics`
- [ ] 简易数字卡片（分析台或 Settings 旁）
- **验收**：DEMO-004

### T3.3 Large file profile `[P1]`
- [ ] 超阈值 DuckDB/抽样；`engine` 标记
- **验收**：大文件上传不崩溃（可用造大文件或调低阈值测）

---

## Phase V3-4 — 接线与验收 `[P0]`

### T4.1 Runtime/Chat 接线
- [ ] run_start/end、cancel、sandbox_reject → audit
- **验收**：完整分析后 audit 可查

### T4.2 测试与 README
- [ ] 单测：sandbox / settings / metrics / audit
- [ ] README：API Key、日志路径、Settings、导出
- **验收**：`pytest -q` 通过；DEMO-001~003 可勾选

---

## 明确不做

- `UI_Optimize.md` 全量暗色重构  
- Docker Sandbox、Evaluation 打分面板、多用户 RBAC、远程业务库  

---

## 建议顺序

```text
V3-0 → V3-1 → V3-2 → V3-3 → V3-4
```

---

## 确认与执行

回复 **`确认任务`** 或 **`开始执行`**（后者从 V3-0 起改代码）。  
**未收到「开始执行」前不修改业务代码。**
