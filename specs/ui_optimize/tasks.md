# DataMind Agent — UI Optimize Tasks

> 对应：`requirements.md`（已确认）+ `design.md`  
> 状态：**已执行**

---

## Phase U0 — Token / Theme `[P0]`

### T0.1 Design Tokens
- [x] `globals.css` 暗色变量（bg/panel/border/text/accent/ai/status/node kinds）
- [x] 去掉默认浅色青绿大背景渐变
- **验收**：body 为暗色专业技术底

### T0.2 Typography
- [x] `layout.tsx`：Inter + JetBrains Mono（next/font）
- [x] 技术字段使用 `font-mono`
- **验收**：无 Fraunces 作为默认展示依赖

---

## Phase U1 — Shell `[P0]`

### T1.1 AppShell / TopBar / StatusDot
- [x] `components/shell/*`
- [x] 导航：分析台 / Evaluation / Settings；health 点；Workspace 槽位
- **验收**：三页可共用顶栏骨架

---

## Phase U2 — Flow Model + Canvas `[P0]`

### T2.1 flowModel
- [x] `lib/flowModel.ts`、`lib/runStatus.ts`
- [x] Trace/steps → nodes/edges + kind 映射
- **验收**：单元可手工用样例数组验证（或轻量测试）

### T2.2 LogicCanvas
- [x] `LogicCanvas` / `FlowNode` / `FlowEdge` + 淡网格
- [x] 选中回调；RUNNING active edge 克制动效
- **验收**：喂入假 Trace 可见节点链

---

## Phase U3 — Agent + Inspector + Execution `[P0]`

### T3.1 AgentPanel
- [x] 状态块、Dataset/上传、会话与 Run 列表、Composer、可折叠 MessageRail
- **验收**：仍能上传并提问（接现有 handlers）

### T3.2 Inspector
- [x] Context / Node / Evidence / Charts / Report 分区
- [x] `ChartView` 暗色容器
- **验收**：选中节点与 Evidence 联动

### T3.3 ExecutionBar
- [x] Timeline + metrics + export 链
- **验收**：Run 中步骤点推进

---

## Phase U4 — 组装分析台 `[P0]`

### T4.1 page.tsx 五区布局
- [x] 接线现有 state/SSE/cancel/loadRun
- [x] Chat 不再占据视觉中心
- **验收**：完整分析路径功能无回归

---

## Phase U5 — 子页换肤 `[P1]`

### T5.1 Settings / Evaluation
- [x] 套用 AppShell + Token
- [x] 表单/卡片暗色可读
- **验收**：改设置、mock 评测仍可用

---

## Phase U6 — 打磨与验收 `[P0]`

### T6.1 Motion + 禁止项自检
- [x] hover 100–200ms；无霓虹/紫渐变堆砌
- **验收**：对照 requirements §6

### T6.2 回归清单
- [x] `tsc --noEmit` 通过；后端 `pytest` 22 passed（UI 不改协议）
- **验收**：桌面 ≥1280 主路径可手工点检

---

## 建议顺序

```text
U0 → U1 → U2 → U3 → U4 → U5 → U6
```

---

## 确认与执行

已收到 **「开始执行」** 并完成实现。下一阶段：V5（`specs/v5/requirements.md`）。
