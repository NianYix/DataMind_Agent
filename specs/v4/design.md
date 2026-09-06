# DataMind Agent — V4 Evaluation Design

> 对应：`specs/v4/requirements.md`（已确认）  
> 状态：待审阅

---

## 1. 目标

在现有 Agent（LangChain/LangGraph 或 legacy）之上增加可复跑评测管线：

```text
Eval Suite (JSON)
      │
      ▼
 Eval Runner ──► AgentRuntime (facade) 或 Mock
      │
      ▼
 scorers (keyword / number / tool stats)
      │
      ▼
 eval_runs + eval_case_results
      │
      ▼
 API + /evaluation UI
```

---

## 2. 目录

```text
evaluation/
  datasets/
    sales_suite.json
  scorers.py          # 启发式评分
  runner.py           # 执行 suite
  __main__.py         # python -m evaluation
  mock_runtime.py     # CI mock
server/
  models/             # + EvalRun, EvalCaseResult
  services/eval_service.py
  api/evaluations.py
apps/web/app/evaluation/page.tsx
```

---

## 3. Suite JSON Schema

```json
{
  "id": "sales_suite",
  "name": "Sales Analysis Suite",
  "cases": [
    {
      "id": "trend_drop",
      "question": "为什么 8 月销售下降？",
      "dataset": "samples/sales.csv",
      "expect": {
        "must_mention": ["8", "下降", "华东"],
        "prefer_tools": ["sql_query", "python_execute"],
        "max_steps": 20,
        "numbers": [{"value": 17.4, "tolerance": 5.0}]
      }
    }
  ]
}
```

`dataset` 相对仓库根；评测时若尚未入库，Runner 可临时注册到默认 Workspace 或直接传路径给 runtime（推荐：确保 samples 已可通过上传 API / 启动时 seed）。

**Seed 策略**：评测启动时按 path 查找已有 Dataset（同名）；没有则自动 upload 到默认 workspace。

---

## 4. 数据模型

### `eval_runs`

| 字段 | 说明 |
|------|------|
| id | uuid |
| suite_id | str |
| mode | `live` \| `mock` |
| status | `running` \| `done` \| `error` |
| summary_json | 聚合指标 |
| created_at | |

### `eval_case_results`

| 字段 | 说明 |
|------|------|
| id | uuid |
| eval_run_id | FK |
| case_id | str |
| agent_run_id | 可空（关联真实 AgentRun） |
| status | passed \| failed \| error |
| scores_json | 分项分 |
| final_answer | text |
| latency_ms | int |
| input_tokens / output_tokens | int |
| steps | int |
| tool_stats_json | {total, success, python_*, sql_*} |
| error | text |

---

## 5. 评分逻辑（`scorers.py`）

| 指标 | 算法 |
|------|------|
| task_success | `must_mention` 全部命中（大小写/简繁不敏感可选）→ 1 else 0；若有 numbers，至少一个在 answer 或 tool 文本中落在 tolerance 内则加分门槛 |
| tool_success_rate | success_tools / total_tools（无调用则 null） |
| python_success_rate | python 成功 / python 调用 |
| sql_success_rate | sql 成功 / sql 调用 |
| calculation_score | numbers 命中比例（heuristic） |
| insight_score | must_mention 命中比例（heuristic） |
| hallucination_rate | answer 中抽取的数字里，未在 tool_results 文本出现的比例（heuristic） |
| avg_steps / latency / tokens / cost | 算术平均 |

Suite summary = cases 平均（跳过 null）。

---

## 6. Runner

```python
def run_suite(suite_id, mode="live"|"mock", db=...) -> eval_run_id
```

- `mock`：`MockRuntime` 根据 case.expect 生成假 final_answer（拼上 must_mention）与假 tool_calls  
- `live`：创建 conversation + `create_runtime(db).run_stream`（收集事件，不推 SSE 也可同步 drain）

并发：V4 串行执行 case，避免打爆 LLM。

---

## 7. API

| Method | Path | 鉴权 |
|--------|------|------|
| POST | `/api/evaluations` | body: `{suite_id, mode}`；若有 APP_API_KEY 则需 Key |
| GET | `/api/evaluations` | 列表 |
| GET | `/api/evaluations/{id}` | 详情 + cases |
| GET | `/api/evaluations/{id}/summary` | 仅 summary_json |
| GET | `/api/evaluation-suites` | 可用 suite 列表 |

---

## 8. 前端 `/evaluation`

- 选择 suite + mode（mock/live）→ 启动  
- 展示最新/历史 run 的卡片：Task Success、Tool Success、Python/SQL、Avg Steps/Latency/Tokens/Cost  
- Case 表格：id、passed、latency、score 明细  
- Hallucination / Insight 旁标注 `heuristic`

导航：分析台 / Settings / Evaluation 三入口（layout 或页内链）。

---

## 9. CLI

```bash
python -m evaluation --suite sales_suite --mode mock
```

打印 summary JSON；exit code 在 mock 下恒 0，live 下可选。

---

## 10. 测试

- scorer 单测（关键词/数字/幻觉启发式）  
- mock runner 集成：跑 sales_suite → summary 有 task_success_rate  
- API 启动 mock 评测（TestClient）

---

## 11. 确认方式

回复 **`确认设计`** 或 **`开始执行`**（后者视为设计与任务锁定并开工）。
