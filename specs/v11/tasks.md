# DataMind Agent — V11 Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 状态：**已执行**  
> 决策：D1–D7 建议默认已锁定

---

## Phase V11-0 — 配置与解析 `[P0]`

### T0.1 Config
- [x] `llm_provider`（默认 `api`）、`ollama_base_url`（默认 `http://localhost:11434`）
- [x] HOT_FIELDS 纳入上述两键
- [x] `.env.example` 注释
- **验收**：`get_settings()` 可读新字段；未配置时默认 api

### T0.2 Resolve 辅助
- [x] `llm/resolve.py`：`resolved_chat_base_url` / `resolved_chat_api_key` / `require_api_key_for_chat`
- **验收**：单元测覆盖 api vs ollama 分支

---

## Phase V11-1 — LLM 路径 `[P0]`

### T1.1 Legacy Gateway
- [x] `LLMGateway` 按 provider 使用 resolve 结果构造 Provider
- [x] `reset_llm_gateway`；保存 Settings 后清空
- **验收**：ollama 下无真实 key 不因 Key 空失败

### T1.2 LangChain `get_chat_model`
- [x] `agent/lc/llm.py` 同步 resolve
- **验收**：与 T1.1 同测思路

### T1.3 Provider
- [x] `require_api_key` 开关
- **验收**：api 缺 key 仍报错

---

## Phase V11-2 — Ops API `[P0]`

### T2.1 Settings
- [x] `SettingsUpdate` + `get_public_settings` 暴露 `llm_provider`、`ollama_base_url`
- [x] PUT 校验 provider 枚举
- **验收**：GET/PUT 往返正确

### T2.2 Ollama health
- [x] `ollama_service.py`：`GET {ollama_base_url}/api/tags`
- [x] `GET /api/llm/ollama/health`
- [x] 仅用 settings 中的 URL（防 SSRF）
- **验收**：mock 成功/失败路径

---

## Phase V11-3 — Settings UI `[P1]`

### T3.1 Provider 表单
- [x] 远程 API / Ollama 切换；条件展示字段
- [x] 保存含新字段

### T3.2 测试连接
- [x] 调用 health；展示状态与模型列表；点选填入 model

---

## Phase V11-4 — 文档与回归 `[P0]`

### T4.1 版本与文档
- [x] API version **0.11.0**
- [x] README：Ollama 使用步骤 + tool-calling 模型建议
- [x] backlog BL-004 → 已完成

### T4.2 测试
- [x] `tests/test_ollama_provider.py`（9 passed）

---

## 确认与执行

- [x] 需求确认（用户：**按建议**）
- [x] `design.md` / `tasks.md` 已产出
- [x] 用户回复 **「开始执行」** 并完成 V11 主路径
