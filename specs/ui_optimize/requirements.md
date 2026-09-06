# DataMind Agent — UI Optimize Requirements

> 源愿景：`specs/UI_Optimize.md`  
> 产品适配：DataMind **AI 数据分析工作台**（非独立低代码编排 SaaS）  
> 语法：EARS  
> 状态：**已确认**（用户 确认需求）  
> 顺序：**本阶段优先于 V5**；V5 按 `specs/v5/requirements.md` 建议决策（D1–D6 已锁定意向）在本阶段完成后推进

---

## 0. 阶段定位

将当前偏「浅色 SaaS 分析页」的前端，升级为：

> **AI Native + Developer Tool + Logic Flow + Professional Workspace**

视觉与信息架构对齐专业 AI 工程工具（Cursor / n8n / Blueprint 语感），**核心视觉中心是 Agent Logic Canvas（由 Trace / Plan / Tool 步骤驱动）**，而非普通 ChatGPT 对话框。

**复用现有业务**：Workspace / Dataset / Conversation / SSE Trace / Evidence / Charts / Cancel / Settings / Evaluation API 不变；本阶段以 `apps/web` 视觉与布局重构为主，**禁止为 UI 破坏后端协议**。

---

## 1. 阶段目标

1. **Design Token + Dark Theme**：统一暗色专业技术色板与字体层级。  
2. **IDE 式 Layout**：Top Bar + 左 Agent/资源 + 中 Logic Canvas + 右 Inspector + 底 Execution/Logs。  
3. **Logic Canvas**：将 Plan/Trace/Tool 步骤渲染为节点与连线（含克制的执行流动效）。  
4. **Agent Control Center**：左侧以「规划 / 推理 / 行动 / 校验」状态机呈现 Agent，而非纯聊天气泡墙。  
5. **Execution 状态体系**：IDLE / RUNNING / COMPLETED / WARNING / ERROR + Timeline。  
6. **Settings / Evaluation 页**：同 Token、同导航语言，避免两套皮肤。

---

## 2. 范围

### 2.1 In Scope

| 模块 | 内容 |
|------|------|
| Tokens | CSS 变量：bg / panel / border / text / accent / AI / success / warning / error |
| Theme | 全局暗色；克制边框与状态色；禁止霓虹堆砌 |
| Layout | 分析台五区布局（Top / Left / Canvas / Inspector / Bottom） |
| Canvas | 节点、连线、选中态、网格背景、Node ID |
| Agent Panel | 控制中心式状态与提问入口（可保留消息列表但降级为次要） |
| Inspector | Dataset schema / Evidence / Charts / 选中 Node 详情 |
| Toolbar | Run / Stop / 导航 / API 健康 / 模型或引擎提示 |
| Timeline | 底部执行步骤列表与状态点 |
| 子页 | `/settings`、`/evaluation` 套用同一主题与顶栏 |
| Motion | 100–200ms hover/选中；执行路径克制流动（非游戏化） |

### 2.2 Out of Scope

| 项 | 说明 |
|----|------|
| 后端 API / Agent 引擎改协议 | 除非为前端展示所必需的只读字段已存在 |
| 完整可视化 Flow 编辑器（拖拽新建任意节点、保存自定义图） | Canvas 以 **Run Trace 只读可视化** 为主 |
| V5 数据源 / 多用户 / Prompt API | 下一阶段 |
| 亮色主题切换 | 本阶段仅暗色（可选后续） |
| 移动端完整重做 | 桌面优先；窄屏可折叠侧栏即可 |

---

## 3. 产品映射（愿景 → DataMind）

| UI_Optimize 概念 | DataMind 映射 |
|------------------|---------------|
| Logic Canvas | Agent Run 的 Plan / Trace / Tool 节点图 |
| Agent Control Center | 提问、Run/Cancel、Planning/Reasoning/Action 状态 |
| Inspector | Profile 字段、Evidence、Charts、选中 step 详情 |
| Execution Timeline | Trace 步骤序列 + metrics（tokens / latency / cost） |
| Connection 数据流 | step → observation → next tool 的边；RUNNING 时高亮当前边 |
| Project / Toolbar | Workspace 选择、Dataset、导航到 Settings/Evaluation |

---

## 4. 功能需求

### 4.1 Design Token 与主题

**REQ-UI-TOK-001**  
THE SYSTEM SHALL 在 `globals.css`（或等价）定义并全站使用 Design Token，至少包含：background、panel、border、text、text-muted、primary、ai、success、warning、error。

**REQ-UI-TOK-002**  
WHEN 应用主题，THE SYSTEM SHALL 采用暗色专业技术风格；大面积背景不得使用纯黑 `#000000`；推荐范围对齐 `UI_Optimize.md`（如 bg `#0B0D10`/`#0F1115`，accent `#5B8CFF`，ai `#8B7CFF`）。

**REQ-UI-TOK-003**  
THE SYSTEM SHALL 禁止作为默认风格：大面积蓝紫渐变、霓虹 glow 堆砌、赛博朋克/星空背景、到处玻璃拟态、巨大圆角营销卡片。

**REQ-UI-TOK-004**  
THE SYSTEM SHALL 使用克制字体：UI 用无衬线（如 Inter / Geist Sans）；Node ID、token、latency、run id 等技术字段用等宽（如 JetBrains Mono / Geist Mono）。可替换现有 Fraunces 展示字体若与工程工具定位冲突。

---

### 4.2 Layout

**REQ-UI-LAY-001**  
WHEN 用户打开分析台（`/`），THE SYSTEM SHALL 呈现类似专业开发工具的分区布局：Top Bar、左侧栏、中央 Logic Canvas、右侧 Inspector、底部 Status/Execution。

**REQ-UI-LAY-002**  
THE SYSTEM SHALL 保证中央区域视觉权重最高（Logic Canvas），聊天不应占据第一视觉中心。

**REQ-UI-LAY-003**  
WHEN 视口变窄，THE SYSTEM SHALL 允许侧栏折叠或切换面板，不得导致核心 Run/提问不可用。

---

### 4.3 Logic Canvas

**REQ-UI-CAN-001**  
WHEN 存在 Agent Plan 或 Trace 步骤，THE SYSTEM SHALL 在 Canvas 中以节点展示（至少覆盖：Understand/Plan、Tool/Execute、Observe、Insight、Report/Final 等已有 step 类型）。

**REQ-UI-CAN-002**  
WHEN 渲染节点，THE SYSTEM SHALL 显示：图标或类型色、名称、类型、执行状态；可选 Node ID（如 `N-001`）。

**REQ-UI-CAN-003**  
THE SYSTEM SHALL 按节点类型使用克制色区分（例：AI→紫、Logic→蓝、Data→青、Action→黄、System→灰），不得大面积填充抢戏。

**REQ-UI-CAN-004**  
WHEN 步骤之间存在先后关系，THE SYSTEM SHALL 使用曲线连线；当前执行路径使用 accent；错误路径可用 error 色。

**REQ-UI-CAN-005**  
WHEN Run 状态为 RUNNING，THE SYSTEM SHALL 对当前边或节点提供克制的数据流动画或呼吸边框（服务于状态感知，非装饰特效）。

**REQ-UI-CAN-006**  
Canvas 背景 SHALL 使用极淡网格（major/minor 可选）；不得使用喧闹纹理。

**REQ-UI-CAN-007**  
WHEN 用户选中节点，THE SYSTEM SHALL 用 accent 边框（可极轻 glow）高亮，并在 Inspector 展示该步摘要 / Evidence 关联。

---

### 4.4 Agent Control Center（左栏）

**REQ-UI-AGT-001**  
THE SYSTEM SHALL 将左侧定位为 Agent Control Center：展示 Agent 状态（IDLE/RUNNING/…）、当前高层动作（Planning / Reasoning / Action / Validation 摘要），以及 Workspace/Dataset/会话选择与上传入口。

**REQ-UI-AGT-002**  
WHEN 用户提交分析问题，THE SYSTEM SHALL 提供明确的提问输入与 Run 触发；消息历史可保留但视觉优先级低于状态与 Canvas。

**REQ-UI-AGT-003**  
WHEN Run 进行中，THE SYSTEM SHALL 提供 Stop/Cancel（对接现有 cancel API），并反映 ● Running 状态点。

---

### 4.5 Inspector（右栏）

**REQ-UI-INS-001**  
THE SYSTEM SHALL 在右侧提供 Inspector/Context：Dataset 概况与字段、选中 Node 详情、Evidence 列表、Charts。

**REQ-UI-INS-002**  
WHEN 无选中节点，THE SYSTEM SHALL 默认展示 Dataset / 最近 Evidence 或 Run metrics，不得空白无说明。

---

### 4.6 Toolbar 与 Execution

**REQ-UI-TB-001**  
Top Bar SHALL 类似 IDE：品牌/项目（Workspace）、Run、Stop、到 Settings/Evaluation 的导航、API Connected 状态；避免堆砌普通营销按钮。

**REQ-UI-TB-002**  
THE SYSTEM SHALL 提供统一执行状态枚举的视觉：IDLE、RUNNING、COMPLETED、WARNING、ERROR。

**REQ-UI-TB-003**  
底部区域 SHALL 展示 Execution Timeline（步骤序号、名称、状态点）及可选 logs/metrics（tokens、latency、cost）。

**REQ-UI-TB-004**  
WHEN Run 完成，THE SYSTEM SHALL 仍可在 Canvas/Timeline 回放该次 Trace（只读），并在合适区域展示 final answer / report 入口。

---

### 4.7 微交互与动效

**REQ-UI-MOT-001**  
可交互元素 hover/focus SHALL 使用细微背景或边框变化；时长约 100–200ms。

**REQ-UI-MOT-002**  
面板开关与 Inspector 切换 SHALL 约 200–400ms；禁止无意义循环动画。

**REQ-UI-MOT-003**  
执行流动画仅在 RUNNING 时启用，完成后静止在最终状态。

---

### 4.8 子页面与一致性

**REQ-UI-PAGE-001**  
`/settings` 与 `/evaluation` SHALL 使用同一 Design Token、顶栏导航与暗色主题。

**REQ-UI-PAGE-002**  
THE SYSTEM SHALL 不改变上述页面的业务能力（改设置、跑 mock 评测等须仍可用）。

---

### 4.9 兼容与质量

**REQ-UI-NFR-001**  
WHEN 重构 UI，THE SYSTEM SHALL 继续消费现有 `lib/api.ts` 与 SSE 事件；不得要求后端破坏性改版作为前提。

**REQ-UI-NFR-002**  
THE SYSTEM SHALL 尽可能拆分为可复用组件（如 `TopBar`、`AgentPanel`、`LogicCanvas`、`FlowNode`、`Inspector`、`ExecutionBar`），避免单文件巨型 JSX 不可维护。

**REQ-UI-NFR-003**  
桌面宽度 ≥1280px 为验收主场景；功能回归：上传、提问、Trace、Evidence、Chart、Cancel、Settings、Evaluation mock。

---

## 5. 当前 UI 问题（基线分析摘要）

| 问题 | 现状 |
|------|------|
| 皮肤 | 浅色青绿 SaaS + 柔和渐变，偏后台而非工程工具 |
| 布局 | 三栏卡片，中栏以 Chat 为主，缺少 Logic Canvas 视觉中心 |
| Trace | 多为列表文本，弱「节点-连线-状态-数据流」 |
| 字体 | Fraunces 展示体偏品牌站，弱 mono 工程信息 |
| 子页 | Settings/Evaluation 各自一套浅色，未统一工作台语言 |
| 动效/状态 | 有 running 标志，但缺少系统化状态点与执行时间线 |

---

## 6. 验收标准

1. 打开 `/` 第一眼可判断为 AI/Logic 工程工作台（暗色、分区、Canvas 居中）。  
2. 一次完整分析 Run 中，Canvas 节点随 Trace 更新，当前执行路径可辨。  
3. 选中节点后 Inspector 显示对应上下文；Evidence/Charts 仍可用。  
4. Run / Stop、上传、Settings、Evaluation 功能无回归。  
5. 无明显违规：霓虹堆砌、紫渐变营销风、破坏 API。

---

## 7. 待确认决策

| # | 决策项 | 建议默认 |
|---|--------|----------|
| U1 | Canvas 定位为 **Trace 只读可视化**（非可编辑流程图） | **是** |
| U2 | 聊天降级为左栏/底栏次要面板，主视觉为 Canvas | **是** |
| U3 | 字体：Inter + JetBrains Mono（或 Geist 系）替换 Fraunces | **是** |
| U4 | Settings/Evaluation 同步暗色 | **是** |
| U5 | 是否引入 React Flow 等库画布 | **建议用轻量自研 SVG/CSS 节点图**（依赖少）；若实现成本过高可改 React Flow |
| U6 | V5 在本阶段后按 v5 文档 D1–D6 建议决策推进 | **是**（用户已表态） |

---

## 8. 确认方式

需求已确认。请审阅 `design.md` / `tasks.md` 后回复：

- **`确认设计`** — 锁定方案  
- **`开始执行`** — 锁定并开工改 `apps/web`

**未回复「开始执行」前不改前端实现。**

---

## 9. 与 V5 的衔接（已记录）

用户意向：

1. **先完成 UI Optimize**  
2. **再按 `specs/v5/requirements.md` 建议决策** 进入企业级切片（连接器 + Prompt + HTTP Tool + 轻量多用户；Web Search 骨架默认关；JWT；不做 RAG/MCP；可用 mock 验收 DB）
