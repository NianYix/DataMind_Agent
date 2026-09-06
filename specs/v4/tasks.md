# DataMind Agent — V4 Evaluation Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 执行门槛：仅当用户明确回复 **「开始执行」** 后改业务代码

---

## Phase V4-0 — 数据与评分 `[P0]`

### T0.1 Suite 文件
- [x] `evaluation/datasets/sales_suite.json`（≥5 cases）
- [x] `GET /api/evaluation-suites` 可读
- **验收**：文件合法；列表返回 suite id

### T0.2 Scorers
- [x] `evaluation/scorers.py`
- [x] 单测：must_mention、numbers、hallucination heuristic
- **验收**：`pytest` 覆盖 scorers

---

## Phase V4-1 — 存储与 Runner `[P0]`

### T1.1 ORM + 迁移
- [x] `EvalRun`、`EvalCaseResult`
- **验收**：init_db 建表

### T1.2 Mock + Live Runner
- [x] `evaluation/mock_runtime.py`、`evaluation/runner.py`
- [x] dataset seed（自动上传 samples）
- **验收**：mock 跑完落库 summary

### T1.3 CLI
- [x] `python -m evaluation --suite sales_suite --mode mock`
- **验收**：打印指标

---

## Phase V4-2 — API `[P0]`

### T2.1 Evaluations API
- [x] POST/GET evaluations、summary、suites
- [x] APP_API_KEY 保护 POST
- **验收**：TestClient mock 评测

---

## Phase V4-3 — 前端 `[P1]`

### T3.1 `/evaluation` 页
- [x] 启动评测、汇总卡片、case 表、heuristic 标注
- [x] 导航入口
- **验收**：DEMO-001 UI 可操作（mock）

---

## Phase V4-4 — 文档与验收 `[P0]`

### T4.1 README
- [x] Evaluation 用法、指标含义、mock vs live
- **验收**：文档可按步骤复现

### T4.2 回归
- [x] `pytest -q` 全绿
- **验收**：含 evaluation 测试

---

## 建议顺序

```text
V4-0 → V4-1 → V4-2 → V4-3 → V4-4
```

---

## 确认与执行

已完成 **「开始执行」**（V4 Evaluation）。
