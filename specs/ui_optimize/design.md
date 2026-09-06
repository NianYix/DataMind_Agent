# DataMind Agent — UI Optimize Design

> 对应：`specs/ui_optimize/requirements.md`（已确认）  
> 愿景原文：`specs/UI_Optimize.md`  
> 状态：**已确认并已实现**  
> 对应设计：`design.md` · 任务：`tasks.md`

---

## 1. 目标与约束

把分析台从「浅色 SaaS Chat」升级为「暗色 AI Logic 工程工作台」：

```text
TopBar
────────────────────────────────────────────
│ AgentPanel │   LogicCanvas    │ Inspector │
│ (control)  │   (视觉中心)      │ (context) │
────────────────────────────────────────────
│ ExecutionBar (timeline / metrics / logs)  │
```

**约束**

- 复用 `lib/api.ts`、SSE `streamMessage`、现有 Cancel / Evidence / Charts / Report。  
- Canvas = **Trace 只读可视化**（U1），不引入可编辑流程图产品。  
- 默认 **轻量自研 SVG/CSS 节点图**（U5），不新增 React Flow 依赖（除非实现卡死再评估）。  
- Settings / Evaluation 同步暗色（U4）。  
- 禁止霓虹堆砌、紫渐变营销风、大面积纯黑。

---

## 2. 当前问题 → 方案

| 问题 | 方案 |
|------|------|
| 浅色青绿 SaaS | Design Token 暗色体系 |
| 中栏 Chat 抢戏 | Chat/提问迁入 AgentPanel；中栏改为 Canvas |
| Trace 纯列表 | `flowModel` 将 steps → nodes/edges |
| Fraunces 偏品牌站 | Inter + JetBrains Mono（next/font） |
| 单文件 `page.tsx` 过大 | 拆组件；`page.tsx` 只做状态编排 |
| 子页两套皮 | 共享 `AppShell` / tokens |

---

## 3. Design Token

文件：`apps/web/app/globals.css`

```css
:root {
  --bg-0: #0B0D10;
  --bg-1: #0F1115;
  --bg-2: #14171C;
  --panel: #15181E;
  --panel-2: #181C22;
  --border: #252A32;
  --border-strong: #303640;
  --text: #E6EAF0;
  --text-muted: #8B949E;
  --primary: #5B8CFF;
  --ai: #8B7CFF;
  --success: #35C98B;
  --warning: #F5B942;
  --error: #FF5C68;
  --grid-dot: #1a1f28;
  --node-ai: #8B7CFF;
  --node-logic: #5B8CFF;
  --node-data: #2EC4B6;
  --node-action: #F5B942;
  --node-system: #6B7280;
}
```

Tailwind v4：通过 `@theme inline` 映射 `--color-*`，组件用语义类（如 `bg-[var(--panel)]`）或 theme 扩展。

**字体**（`layout.tsx`）

- `Inter` → `--font-sans`  
- `JetBrains_Mono` → `--font-mono`  
- 移除 Fraunces / Source Sans 作为默认展示体  

---

## 4. 前端架构

```text
apps/web/
  app/
    layout.tsx              # fonts + dark body
    globals.css             # tokens
    page.tsx                # 分析台状态容器
    settings/page.tsx       # 套用 AppShell
    evaluation/page.tsx     # 套用 AppShell
  components/
    shell/
      AppShell.tsx          # 顶栏 + 内容槽
      TopBar.tsx
      StatusDot.tsx
    agent/
      AgentPanel.tsx        # 左栏控制中心
      AgentComposer.tsx     # 提问 + Run
      MessageRail.tsx       # 次要消息列表（可折叠）
    canvas/
      LogicCanvas.tsx
      FlowNode.tsx
      FlowEdge.tsx          # SVG path
      canvasGrid.css        # 淡网格
    inspector/
      Inspector.tsx
      EvidencePane.tsx
      ChartsPane.tsx
      NodeDetail.tsx
      ReportPane.tsx
    execution/
      ExecutionBar.tsx
      ExecutionTimeline.tsx
    ChartView.tsx           # 改暗色边框
  lib/
    api.ts                  # 不变
    flowModel.ts            # Trace → GraphModel
    runStatus.ts            # IDLE|RUNNING|...
```

**依赖**：不新增 npm 包（echarts 保留）。字体走 `next/font/google`。

---

## 5. 数据流（不变后端）

```text
用户提问
  → streamMessage (SSE)
  → liveTrace / metrics / final
  → flowModel.fromTrace(liveTrace | steps)
  → LogicCanvas 渲染
  → 选中 nodeId → Inspector
  → loadRun 回放：api.trace / evidences / charts / report
```

### 5.1 `flowModel.ts`

输入：`{ type, summary }[]` 或 `AgentStep[]`  

输出：

```ts
type FlowNodeModel = {
  id: string;        // N-001
  type: string;      // understand | plan | tool | observe | insight | report | metrics | ...
  kind: "ai" | "logic" | "data" | "action" | "system";
  title: string;
  summary: string;
  status: "pending" | "running" | "done" | "error";
};

type FlowEdgeModel = {
  id: string;
  from: string;
  to: string;
  active?: boolean;  // 当前执行边
  error?: boolean;
};

type GraphModel = { nodes: FlowNodeModel[]; edges: FlowEdgeModel[] };
```

**布局算法（自研、简单）**

- 纵向或横向分层：按 step 序号均分坐标（固定 node 宽高）。  
- 首屏无 Trace：显示占位节点「Awaiting Run」。  
- 边：相邻 step 用二次 Bezier；`RUNNING` 时最后一条边 `active`。

**类型映射（示例）**

| step.type 含 | kind |
|--------------|------|
| understand / insight / report / supervisor | ai |
| plan / observe | logic |
| tool / execute / sql / python / statistics | data/action |
| metrics / error | system |

---

## 6. 分区职责

### 6.1 TopBar

- 左：品牌 `DataMind`、Workspace 下拉  
- 中：`Run ▶`（聚焦 composer 或提交）、`Stop ■`（cancel）  
- 右：Evaluation / Settings 链、`● Connected`（health）、可选引擎/模型只读提示（来自 settings 公开字段若易取，否则省略）

### 6.2 AgentPanel（左）

- Agent 状态块：`● IDLE|RUNNING|…` + 当前高层摘要（取 latest liveTrace summary）  
- Dataset 列表 + 上传 CSV/SQLite  
- Conversations / 历史 Run（紧凑）  
- `AgentComposer`：输入 + 发送  
- `MessageRail`：默认可折叠，避免抢 Canvas

### 6.3 LogicCanvas（中）

- 淡网格背景  
- SVG 层：edges + nodes  
- 点击选中；选中 accent 边框  
- RUNNING：active edge 短划线/位移动画（CSS，200–400ms 周期，克制）  
- 无障碍：节点可键盘 focus（至少 tab + enter 选中，P1 尽力）

### 6.4 Inspector（右）

Tab 或手风琴：

1. **Context** — Dataset profile 摘要 / 字段表  
2. **Node** — 选中节点 summary  
3. **Evidence** — 列表 + 详情（现逻辑）  
4. **Charts** — `ChartView` 暗色容器  
5. **Report** — markdown + PDF 链  

### 6.5 ExecutionBar（底）

- Timeline：`01 Load… ✓` 式步骤点  
- Metrics 一行：tokens / latency / cost  
- Export Trace JSON 链  

---

## 7. 状态机（`runStatus`）

| UI Status | 条件 |
|-----------|------|
| IDLE | 无 running 且无 error |
| RUNNING | `running === true` |
| COMPLETED | 有 final / report 且非 running |
| WARNING | 可选：部分 tool 失败（若前端能从 steps 推断；否则暂不用） |
| ERROR | `error` 非空或 run.status === error |

状态点组件 `StatusDot` 统一用于 TopBar / AgentPanel / Timeline。

---

## 8. 动效规范

| 场景 | 时长 | 手段 |
|------|------|------|
| Hover / 选中 | 100–200ms | border/background |
| 面板切换 | 200–400ms | opacity/transform |
| Active edge | 仅 RUNNING | stroke-dashoffset |
| 禁止 | — | 永久 glow 脉冲、星空粒子 |

---

## 9. 子页改造

- `AppShell` 包裹 Settings / Evaluation：同 TopBar 导航、同 bg。  
- 表单控件：暗色 input/border；Metric 卡片用 `--panel` 非白底。  
- `ChartView`：边框/标题改 token；ECharts 若过亮，可设 `backgroundColor: 'transparent'`（不强制改业务 option）。

---

## 10. `page.tsx` 重构策略

1. 抽出 hooks 或保留状态于 `page.tsx`，子组件纯展示 + 回调。  
2. 行为回归清单：上传、建会话、SSE、cancel、loadRun、evidence、charts、report、export。  
3. 不修改 `api.ts` 契约（除非仅加只读 helper）。

---

## 11. 实施顺序（与 tasks 对齐）

```text
T0 Tokens + fonts + globals
T1 Shell / TopBar / StatusDot
T2 flowModel + LogicCanvas + Node/Edge
T3 AgentPanel + Composer（迁移左栏业务）
T4 Inspector + ExecutionBar（迁移右栏/底）
T5 组装 page.tsx 五区布局
T6 Settings + Evaluation 换肤
T7 动效打磨 + 手工回归
```

---

## 12. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 自研布局节点重叠 | 固定纵向步进 + 滚动容器；节点数多时可横向压缩 |
| 重构时功能回归 | 每阶段保持可运行；最后按验收清单点检 |
| ECharts 亮色图 | 容器暗色即可；不阻塞主题 |
| 单文件过大难拆 | 先壳后肉：先空布局再迁状态 |

---

## 13. 非目标重申

- 不实现拖拽编辑 / 保存自定义 graph  
- 不改 FastAPI / Agent  
- 不做亮色切换、不做移动端像素级重做  
- 不做 V5 业务页（数据源/多用户）——仅预留导航风格一致性  

---

## 14. 确认方式

回复 **`确认设计`** 或 **`开始执行`**（后者视为设计与任务一并锁定并开工）。
