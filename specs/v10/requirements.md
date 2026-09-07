# DataMind Agent — V10 Requirements

> 基线：V1–V9 + BL-002 / BL-003（已实现）  
> 本阶段：**V10 — Multi-Dataset 同 Run 分析**（立项自 BL-001）  
> 语法：EARS  
> 状态：**已确认**（D1–D7 按建议锁定）

---

## 0. 阶段定位

| 已完成 | 本阶段 | 明确另开 |
|--------|--------|----------|
| 单 Dataset / 会话绑定 `dataset_id`；工具仅 `df` / `data` | **一次提问可绑定 ≥2 个 Dataset 联合分析** | 跨 Workspace 联邦、任意跨库分布式 JOIN |
| Logic Canvas 详情 / 拖动（BL-002/003） | **UI 多选 Dataset；沙箱多表；Trace 标明来源** | 「先合并文件再上传」捷径产品化 |
| Workflow analyze 单 dataset | **Workspace 对话路径优先；Workflow 可选跟进** | 完整多源建模 / 语义层 |

需求池 **BL-001** 为本切片唯一主线。

---

## 1. 阶段目标

1. **会话可绑定多个 Dataset**：至少一个为主（primary），其余为辅（secondary）。  
2. **Agent 沙箱多表可用**：Python 侧可访问多个 DataFrame；SQL 侧可按稳定表名查询并对多表 JOIN。  
3. **工具与 Prompt 感知多源**：schema / preview / 规划提示列出各表字段；Evidence / Trace 可标注 `dataset_id` 或表名。  
4. **Workspace UI**：Dataset 列表支持多选（或主/辅标记）；创建会话 / Run 使用所选集合；单选路径行为与 V9 一致。  
5. **兼容**：仅 1 个 Dataset 时 API / 工具 / UI 与现网等价（无强制迁移打断）。  
6. **可回归**：无 LLM 时可用 fixture 多 CSV 跑通工具层与 API 单测。

**非目标**：跨 Workspace 数据联邦、自动 schema 对齐合并成单表、行级权限、分布式查询引擎、拖拽「合并 Dataset」向导（可作为后续 backlog）。

---

## 2. 范围

### 2.1 In Scope

| 模块 | 内容 |
|------|------|
| ORM / API | Conversation 支持多 Dataset 绑定；兼容旧 `dataset_id` |
| ToolContext / Sandbox | 多路径加载；SQL 多表注册；Python 多 `df_*` 或命名空间 |
| Agent Prompt / State | 注入多表 schema 摘要；`dataset_ids` + primary |
| Evidence / Trace（轻量） | 工具结果可带 `source`（表名或 dataset_id） |
| UI Workspace | Dataset 多选 + 主表标记；提问走多源会话 |
| Tests | 双 CSV JOIN / 并排汇总路径；单 Dataset 回归 |

### 2.2 Out of Scope

| 项 | 去向 |
|----|------|
| Workflow `analyze` 多 dataset 全量改造 | P1 可选；默认可仅 Workspace |
| 自动推断 JOIN 键并物化宽表 | 更后 |
| 跨 Workspace / 远程联邦 | 更后 |
| UI「合并为单 Dataset」上传捷径 | backlog 另条 |

---

## 3. 功能需求

### 3.1 数据模型与 API

**REQ-V10-API-001**  
THE SYSTEM SHALL 允许一个 Conversation 绑定有序 Dataset 列表：`dataset_ids[]`（长度 ≥1），并指定恰好一个 `primary_dataset_id`（默认列表首项）。

**REQ-V10-API-002**  
WHEN 客户端仅提供旧字段 `dataset_id`，THE SYSTEM SHALL 将其解释为单元素 `dataset_ids`，且 `primary_dataset_id = dataset_id`（向后兼容）。

**REQ-V10-API-003**  
WHEN 创建或更新 Conversation 的数据集绑定，THE SYSTEM SHALL 校验：所有 id 属于同一 Workspace、去重、primary 落在列表内；否则返回 4xx。

**REQ-V10-API-004**  
THE SYSTEM SHALL 在 Conversation / Run 相关响应中暴露 `dataset_ids` 与 `primary_dataset_id`（并保留 `dataset_id` 别名 = primary，便于旧前端）。

**REQ-V10-API-005**  
THE SYSTEM SHALL 限制单次绑定 Dataset 数量上限（建议默认 **5**，可配置），超限拒绝。

### 3.2 沙箱与工具

**REQ-V10-TOOL-001**  
WHEN Run 绑定多个 Dataset，THE SYSTEM SHALL 在 SQL 沙箱中为每个 Dataset 注册稳定表名：primary 仍可用 `data`；其余使用可预测别名（如 `data_2`… 或基于安全化后的 `dataset.name`，立项设计锁定一种）。

**REQ-V10-TOOL-002**  
WHEN Run 绑定多个 Dataset，THE SYSTEM SHALL 在 Python 沙箱中提供多个可引用帧：至少 `df`（primary）以及与 SQL 表名对应的附加帧（如 `df_data_2` 或 `dfs["data_2"]`）。

**REQ-V10-TOOL-003**  
THE SYSTEM SHALL 扩展 `dataset_schema` / `dataset_preview`（或新增等价工具参数）以支持按表名 / dataset 查询；默认行为针对 primary，与现网一致。

**REQ-V10-TOOL-004**  
WHEN 执行成功的工具调用涉及明确数据源，THE SYSTEM SHOULD 在 Evidence 或 tool payload 中写入 `source`（表名或 `dataset_id`），便于 Inspector 展示。

### 3.3 Agent 规划

**REQ-V10-AGENT-001**  
WHEN 多 Dataset 绑定存在，THE SYSTEM SHALL 在规划 / 系统提示中注入各表名称、行数级别与字段摘要，并说明表别名约定。

**REQ-V10-AGENT-002**  
WHEN 用户问题涉及对比或关联且存在 ≥2 个 Dataset，THE SYSTEM SHALL 允许 Agent 生成跨表 SQL JOIN 或分表汇总后再对比的工具调用（不强制自动选 JOIN 键正确，但能力上可用）。

**REQ-V10-AGENT-003**  
WHEN 仅绑定 1 个 Dataset，THE SYSTEM SHALL 保持与 V9 相同的工具上下文与提示结构（无额外噪声表列表）。

### 3.4 Workspace UI

**REQ-V10-UI-001**  
THE SYSTEM SHALL 在 Workspace Dataset 区支持选择 **1..N** 个 Dataset，并标记 **主表**（默认第一个选中项）。

**REQ-V10-UI-002**  
WHEN 用户发起提问，THE SYSTEM SHALL 使用当前多选集合创建或复用 Conversation（绑定 `dataset_ids` + primary），不得静默丢弃辅表。

**REQ-V10-UI-003**  
THE SYSTEM SHALL 在 Context / Agent 侧可见展示当前绑定的 Dataset 列表（主/辅），避免用户误以为仍是单表。

**REQ-V10-UI-004**  
WHEN 用户将选择从多表改回单表，THE SYSTEM SHALL 允许新建会话或更新绑定（设计阶段锁定：优先「改选后下次提问用新绑定」，避免改写历史 Run）。

### 3.5 兼容与观测

**REQ-V10-COMPAT-001**  
THE SYSTEM SHALL 保证既有单 Dataset 会话、历史 Run 回放、评测套件在未改调用方的情况下继续通过。

**REQ-V10-TEST-001**  
THE SYSTEM SHALL 提供自动化测试：两个小型 CSV（或 fixture）在同一次工具调用路径下可被 SQL JOIN 或 Python 双帧读取。

---

## 4. 非功能

| ID | 要求 |
|----|------|
| NFR-V10-001 | 多表加载失败时：明确错误（哪个 dataset），不静默退化为单表成功 |
| NFR-V10-002 | 大表仍受现有超时 / 行数策略约束；多表总内存风险在设计中说明降级策略（如仅 profile 注入、按需 load） |
| NFR-V10-003 | API 版本号递增至 **0.10.0**（与 README 阶段表一致） |

---

## 5. 验收标准

1. 用户在 Workspace 选中两个已上传 CSV，主/辅标记清晰，一问可得到涉及两表的汇总或对比类回答（真实 LLM 或 mock 工具路径其一可验收）。  
2. SQL 沙箱中可对 `data` 与第二表名执行 JOIN（单测覆盖）。  
3. 仅选一个 Dataset 时行为与现网一致（回归测试）。  
4. Conversation API 兼容只传 `dataset_id`。  
5. 全量 `pytest` 绿；前端 `tsc` 通过。

---

## 6. 待确认决策

| # | 决策项 | 建议默认 |
|---|--------|----------|
| D1 | 下一阶段是否做 **Multi-Dataset 同 Run（本文件 / BL-001）**？ | **是** |
| D2 | 绑定模型 | **`dataset_ids[]` + `primary_dataset_id`**；保留 `dataset_id` 别名 |
| D3 | SQL 辅表命名 | **`data` + `data_2`…`data_N`**（稳定、与显示名解耦） |
| D4 | Python 辅帧 | **`df` = primary；`df_2`…`df_N` 与 SQL 序号对齐** |
| D5 | 存储落点 | **Conversation：`dataset_id`=primary + `context_json.dataset_ids`**（少迁表）；或新列——设计定一种 |
| D6 | Workflow analyze 多源 | **本阶段不做**（仅 Workspace） |
| D7 | 单次绑定上限 | **5** |

---

## 7. 确认方式

请回复：

- **`确认需求`** — 按 D1–D7 建议默认锁定，进入 `design.md` / `tasks.md`  
- **`确认需求：…`** — 修改决策（例如辅表用文件名、或同期改 Workflow）  

**未确认前不编写 design 以外的业务代码；未回复「开始执行」前不改实现。**

---

## 确认记录

- 2026-09-07：用户确认需求，决策采取建议（D1–D7）。已产出 `design.md` / `tasks.md`。
