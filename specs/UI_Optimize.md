# UI 重构要求：AI Logic Flow 工作台科技感升级

请对当前项目的 UI 进行一次系统性的视觉升级。

## 一、核心设计定位

当前产品是一款「AI 驱动的逻辑流程编排工具」。

UI 不要做成普通 SaaS 后台，也不要做成传统低代码平台。

整体定位：

> **AI Native + Developer Tool + Logic Flow + Professional Workspace**

视觉上应该让用户第一眼感受到：

* 这是一个专业的 AI 开发工具
* 这是一个可以编排复杂逻辑的工作台
* 有明显的技术感、工程感、未来感
* 信息密度较高，但不能杂乱
* 强调「结构、连接、状态、数据流」
* UI 应该服务于逻辑流程，而不是为了装饰而装饰

参考方向：

* Cursor
* Linear
* ComfyUI
* Unreal Engine Blueprint
* n8n
* GitHub Copilot Workspace
* Figma
* VS Code

但不要直接复制这些产品的 UI。

---

# 二、整体视觉风格

采用：

**Dark Professional Technical UI**

基础色以：

* 深黑
* 深灰
* 石墨灰
* 冷灰

为主。

不要大面积使用纯黑 #000000。

推荐使用类似：

Background：
#0B0D10
#0F1115
#14171C

Panel：
#15181E
#181C22

Border：
#252A32
#303640

Text：
#E6EAF0

Secondary Text：
#8B949E

Accent：
使用一个主要科技色，例如蓝紫色 / 青蓝色。

推荐：

Primary：
#5B8CFF

AI：
#8B7CFF

Success：
#35C98B

Warning：
#F5B942

Error：
#FF5C68

注意：

**不要到处使用发光、渐变和霓虹色。**

科技感主要来自：

* 信息层级
* 精细边框
* 状态颜色
* 动态连接线
* 节点结构
* 微交互
* 数据状态
* 空间布局

而不是靠大量 Glow。

---

# 三、整体布局

重新审视整个 App 的 Layout。

建议采用类似专业开发工具的布局：

┌──────────────────────────────────────────────┐
│ Top Bar                                      │
├──────────┬───────────────────────┬───────────┤
│          │                       │           │
│ 左侧     │                       │ 右侧      │
│ Agent /  │     Logic Canvas      │ Inspector │
│ Flow     │                       │ / Context │
│          │                       │           │
│          │                       │           │
├──────────┴───────────────────────┴───────────┤
│ Status / Execution / Logs                    │
└──────────────────────────────────────────────┘

核心区域应该是：

**Logic Canvas**

让用户感觉自己是在操作一个真正的 AI Logic Engine。

---

# 四、Logic Flow Canvas 是整个产品最重要的视觉中心

不要把 Flow 做成普通的流程图。

应该突出：

> Node → Connection → Data → State → Execution

节点需要具有明显的「工程工具」感觉。

例如：

┌─────────────────────────────┐
│ ◉  AI Decision               │
│─────────────────────────────│
│ Model      GPT-5             │
│ Status     ● Ready           │
│                             │
│ Input                       │
│ ○ context                   │
│                             │
│ Output                      │
│ ○ decision                  │
└─────────────────────────────┘

节点顶部显示：

* Node Icon
* Node Name
* Node Type
* Execution Status

节点内部显示：

* Input
* Output
* Parameters
* Runtime State

不同 Node 类型使用非常克制的颜色区分。

例如：

AI Node → 紫色

Logic Node → 蓝色

Data Node → 青色

Action Node → 黄色

System Node → 灰色

---

# 五、Connection / 连线

连线是科技感非常重要的来源。

不要使用简单的静态灰色直线。

推荐：

* Bezier Curve
* Hover 时高亮
* Active Flow 显示数据流动动画
* Execution 时沿连接线出现流动粒子
* Connection 上可以显示数据类型
* 错误连接显示红色状态
* 当前执行路径显示 Accent Color

例如：

Node A
│
└───────●───────> Node B
↑
Data Flow

执行过程中：

● → → → → →

但动画要非常克制。

---

# 六、AI Agent 区域

如果产品包含 Agent，不要把 Agent UI 做成普通 ChatGPT 聊天窗口。

应该表现为：

**Agent Control Center**

例如：

AGENT
──────────────────

● Running

Planning
└ Analyze current graph

Reasoning
└ Find dependency conflict

Action
└ Modify Node #23

Validation
└ Running...

这样用户会明显感受到：

> Agent 正在操作 Logic Graph

而不是：

> 我在和一个聊天机器人聊天。

---

# 七、Execution / Runtime 状态

增加明显的运行状态体系。

例如：

● IDLE

▶ RUNNING

✓ COMPLETED

⚠ WARNING

✕ ERROR

EXECUTION

01  Load Context       ✓
02  Analyze Graph      ✓
03  Execute Agent      ▶
04  Validate Output    ○
05  Commit Changes     ○

执行的时候增加非常轻微的动态效果。

例如：

节点边框轻微呼吸

Connection 出现数据流

Execution Timeline 自动推进

但不要做成游戏 UI。

---

# 八、顶部 Toolbar

顶部不要放大量普通 Button。

更像 IDE / 专业开发工具。

例如：

[ Project ]

[ Undo ] [ Redo ]

[ Run ▶ ]

[ Stop ■ ]

[ AI Agent ✦ ]

[ Debug ]

右侧：

● Connected

GPT-5

CPU 23%

Memory 1.8GB

这些细节可以增强专业工具感。

---

# 九、Typography

字体非常重要。

不要使用太花哨的字体。

优先：

Inter

或者：

JetBrains Mono / SF Mono / Geist Mono

其中：

普通 UI：

Inter

代码、Node ID、参数、状态：

Monospace

例如：

NODE_023

EXECUTION_ID

INPUT_TOKEN

LATENCY 842ms

这些技术信息使用 Mono Font，会明显增强工程感。

---

# 十、细节设计

重点增加以下微细节：

### 1. Grid

Canvas 背景使用非常淡的 Grid。

例如：

· · · · · · · ·
· · · · · · · ·
· · · · · · · ·

不要太明显。

可以有：

Major Grid

Minor Grid

类似 Figma / Unreal Blueprint。

---

### 2. Node ID

每个 Node 可以拥有：

N-001

N-002

N-003

这样的 ID。

让整个系统感觉更加工程化。

---

### 3. 状态指示器

使用：

●

而不是大量文字。

例如：

● Connected

● Running

● Ready

这样更现代。

---

### 4. Hover

所有可交互元素增加非常细微的：

* Background highlight
* Border highlight
* Shadow
* Accent

不要使用夸张动画。

---

### 5. Selected Node

选中节点时：

Border：

Accent Color

外围增加非常轻微的 Glow。

例如：

┌───────────────────────┐
│ AI Decision           │
└───────────────────────┘

而不是大面积蓝色填充。

---

# 十、禁止事项

请特别注意：

不要：

❌ 大量蓝紫渐变

❌ 大量霓虹 Glow

❌ 巨大的圆角卡片

❌ 玻璃拟态 everywhere

❌ 大量发光线条

❌ 赛博朋克背景

❌ 星空 / 电路板背景

❌ 大量装饰图形

❌ 普通 SaaS Dashboard 风格

❌ AI 生成网站常见的紫色渐变 UI

目标不是：

"看起来很 AI"

而是：

> **看起来像一个真正成熟的 AI 工程软件。**

---

# 十一、动效

整体动效需要克制。

推荐：

100~200ms：

Button Hover

Panel Transition

Node Selection

200~400ms：

Panel Open

Inspector Transition

Flow State Change

Execution：

实时数据流动画。

所有动画都应该服务于：

**状态变化 / 数据流 / 执行过程**

不要为了动画而动画。

---

# 十二、最终设计目标

完成后，请从以下几个维度检查：

### 第一眼

用户是否觉得这是一个：

「AI 开发 / Logic Engineering Tool」

而不是：

「普通后台系统」？

### 第二眼

用户是否能立即看出：

* 当前 Flow
* 当前 Agent
* 当前执行状态
* 当前选中 Node
* 当前数据流

### 第三眼

用户是否能感受到：

> 「这个系统正在运行。」

而不是一张静态流程图。

---

# 十三、实施要求

不要只修改 CSS 颜色。

请从以下层级逐步重构：

1. Design Token
2. Global Theme
3. Layout
4. Canvas
5. Node
6. Connection
7. Agent Panel
8. Inspector
9. Toolbar
10. Execution Timeline
11. Status System
12. Micro Interaction

优先保证：

**信息架构 > 布局 > 层级 > 状态 > 交互 > 装饰**

不要一次性重写整个项目。

先分析当前 UI 结构，然后给出：

1. 当前 UI 问题分析
2. UI 重构方案
3. Component 改造列表
4. Design Token
5. 实施顺序

确认整体方案后，再逐模块实施。

同时：

**尽可能复用现有组件和业务逻辑，不要为了 UI 重构破坏现有功能。**

“不要把科技感理解成视觉特效，而要把科技感理解成‘专业开发工具的视觉语言’。”