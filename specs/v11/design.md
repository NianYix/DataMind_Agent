# DataMind Agent — V11 Architecture Design

> 对应：`specs/v11/requirements.md`（**已确认**，D1–D7 按建议锁定）  
> 基线：V10 Multi-Dataset  
> 状态：**已确认并已实现**  
> 非目标：Ollama 安装/拉模 UI、按 Run 临时选模型、本地 Embedding、原生 `/api/chat` Provider

---

## 1. 目标

```text
Settings UI
  llm_provider = api | ollama
        │
        ├─ api  → llm_base_url + llm_api_key + llm_model
        └─ ollama → ollama_base_url + llm_model（复用）+ 占位 key
        │
        ▼
resolve_llm_endpoint()
        │
        ├─ LLMGateway (legacy)  → OpenAICompatibleProvider
        └─ get_chat_model() (langchain) → ChatOpenAI(base_url=.../v1)
        │
        ▼
Workspace stream_analysis / Workflow analyze
```

默认 `llm_provider=api`，与 V10 行为等价。

---

## 2. 已锁定决策

| # | 取值 |
|---|------|
| D1 | `llm_provider`: `api` \| `ollama` |
| D2 | 模型名 **复用 `llm_model`**；新增 `ollama_base_url` |
| D3 | **OpenAI Compatible**（`{ollama_base_url}/v1/chat/completions`） |
| D4 | Tool calling **尽力启用**；弱模型文档说明，本切片不做复杂降级 |
| D5 | `llm_provider`、`ollama_base_url` 纳入 **HOT_FIELDS** |
| D6 | **不改** Embedding / RAG |
| D7 | UI **仅 Settings** |

---

## 3. 配置

`server/core/config.py` + `.env.example`：

| 键 | 默认 | 说明 |
|----|------|------|
| `LLM_PROVIDER` / `llm_provider` | `api` | `api` \| `ollama` |
| `OLLAMA_BASE_URL` / `ollama_base_url` | `http://localhost:11434` | 无尾斜杠；探测用 `/api/tags`，聊天用 `/v1` |
| `LLM_MODEL` | 不变 | Ollama 下填本地模型名（如 `qwen2.5:7b`） |
| `LLM_BASE_URL` / `LLM_API_KEY` | 不变 | 仅 `api` 模式使用；`ollama` 模式忽略 Key 强制校验 |

**HOT_FIELDS 新增**：`llm_provider`、`ollama_base_url`（已有 `llm_base_url`、`llm_model`、`llm_api_key`）。

**解析辅助**（建议放 `llm/resolve.py` 或 `server/core/config.py` 方法）：

```text
def resolved_chat_base_url(settings) -> str:
  if provider == ollama:
    return ollama_base_url.rstrip("/")   # 调用方再拼 /v1
  return llm_base_url.rstrip("/")

def resolved_chat_api_key(settings) -> str:
  if provider == ollama:
    return llm_api_key or "ollama"      # 占位，不强制用户填写
  return llm_api_key                    # 空则调用侧 raise

def require_api_key_for_chat(settings) -> bool:
  return provider != "ollama"
```

保存 Settings 后：`reload_settings()` + 清空 `LLMGateway` 单例（现有逻辑扩展即可）。LangChain 侧每次 `get_chat_model()` 读最新 Settings（已无全局单例缓存则无需额外清）。

---

## 4. LLM 层改动

### 4.1 `OpenAICompatibleProvider`

- `api` 模式：保持「无 `api_key` → RuntimeError」。
- `ollama` 模式：允许占位 Key；URL 仍为 `{base}/v1/chat/completions`。
- 建议由 Gateway 传入已解析的 `base_url` / `api_key`，Provider 本身可增加可选参数 `require_api_key: bool = True`，或 Gateway 保证 ollama 时 key 非空。

### 4.2 `LLMGateway`

构造时：

```text
settings = get_settings()
base = resolve chat base (api → llm_base_url, ollama → ollama_base_url)
key  = resolve chat key
model = settings.llm_model
→ OpenAICompatibleProvider(base, key, model)
```

### 4.3 `agent/lc/llm.py` · `get_chat_model`

```text
if provider == api and not llm_api_key → raise
base = resolved_chat_base_url + ensure /v1
api_key = resolved_chat_api_key
→ ChatOpenAI(model=llm_model, api_key=..., base_url=base, temperature=...)
```

### 4.4 错误映射

- 连接失败 / 超时 / HTTP 4xx/5xx：现有 `raise_for_status` / LangChain 异常向上抛；`chat_service` / runtime 已有错误 SSE 路径，本切片确保消息含「Ollama」或 host 提示即可（可选轻量包装，非必须新异常类型）。

### 4.5 Token usage

沿用现有解析；Ollama 若无 `usage` → 0 / 既有默认，不中断。

---

## 5. Ops API

### 5.1 Settings 扩展

`SettingsUpdate` / `get_public_settings` 增加：

| 字段 | 读写 |
|------|------|
| `llm_provider` | 读写；校验 `api`\|`ollama` |
| `ollama_base_url` | 读写 |
| （已有）`llm_base_url` / `llm_model` / `llm_api_key` | 不变 |

公开响应仍掩码 `llm_api_key`；`llm_api_key_set` 在 ollama 下可为 false（正常）。

### 5.2 探测接口

建议挂在 `server/api/ops.py`：

| 方法 | 路径 | 行为 |
|------|------|------|
| `GET` | `/api/llm/ollama/health` | 对 `ollama_base_url` 发 `GET /api/tags`（短超时，如 5s）；返回 `{ ok, latency_ms?, models?: string[], error? }` |
| （可选合并） | 同上一次返回 models | 避免再开 list 接口；UI 一次拉取即可 |

实现：`server/services/ollama_service.py`（httpx），不依赖 LLM Gateway。

校验：仅探测配置中的 base URL；不代理任意用户输入 host（本切片用已保存 settings；若 query 允许覆盖 url，须限制为本地或与 settings 一致——**建议本切片只用 settings 中的 `ollama_base_url`，避免 SSRF**）。

---

## 6. UI（Settings）

`apps/web/app/settings/page.tsx`：

1. Provider 单选 / 下拉：`远程 API` | `Ollama 本地`。
2. `api`：展示现有 Base URL、Model、API Key。
3. `ollama`：展示 Ollama Base URL、Model；隐藏或标注 API Key 可选；按钮「测试连接」→ 调 health，展示 ok/latency + 模型列表（可点选填入 `llm_model`）。
4. 保存时 PUT `llm_provider`、`ollama_base_url`、以及当前可见的 url/model/key 字段。

Workspace / Workflow **不改**交互。

---

## 7. 文档与版本

| 项 | 内容 |
|----|------|
| API version | `0.11.0` |
| `.env.example` | `LLM_PROVIDER`、`OLLAMA_BASE_URL` 注释示例 |
| `README.md` | 简述：安装 Ollama → pull 模型 → Settings 切本地 → 分析 |
| Tool calling 注意 | 建议使用支持 tools 的本地模型（如 qwen2.5 系列） |

---

## 8. 测试

`tests/test_ollama_provider.py`（或并入现有）：

| 用例 | 方式 |
|------|------|
| `resolve`：api 缺 key 应 require；ollama 不 require | 纯函数 |
| Gateway / get_chat_model 在 ollama 下使用 `ollama_base_url` + 占位 key | mock settings |
| health：mock httpx 200 + tags → ok + models | respx / monkeypatch |
| health：连接失败 → ok=false + error | mock |
| Settings PUT/GET 含 `llm_provider` | TestClient（若已有 settings 测则扩展） |

不要求 CI 起真实 Ollama。

---

## 9. 文件影响清单

| 路径 | 动作 |
|------|------|
| `server/core/config.py` | 新字段 + HOT_FIELDS |
| `llm/resolve.py`（新）或 config 方法 | 解析 base/key |
| `llm/gateway.py` | 按 provider 构造 |
| `llm/providers/openai_compatible.py` | 可选：放宽 key（若由 resolve 保证则可不动） |
| `agent/lc/llm.py` | 按 provider 构造 ChatOpenAI |
| `server/services/settings_service.py` | 公开字段 |
| `server/services/ollama_service.py` | 新：health + tags |
| `server/api/ops.py` | SettingsUpdate + health 路由 |
| `apps/web/app/settings/page.tsx` | Provider UI + 测试连接 |
| `tests/test_ollama_provider.py` | 新 |
| `.env.example` / `README.md` / `server/main.py` version | 文档与版本 |

---

## 10. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 本地模型不支持 tools，Agent 卡死/空转 | README 标明；D4 不本切片做降级 |
| 用户把 `ollama_base_url` 指到内网敏感机 | 本切片探测只用已存 settings；文档提醒仅本机 |
| 切换 provider 后忘记改 `llm_model` | UI 在 ollama 下用模型列表辅助填写 |
| LangChain 缓存模型实例 | 确认无跨请求长缓存；有则保存 settings 时清 |

---

## 11. 变更记录

| 日期 | 变更 |
|------|------|
| 2026-09-21 | 需求确认（按建议）；初稿 design |
| 2026-09-21 | 执行完成：Ollama provider；API 0.11.0 |
