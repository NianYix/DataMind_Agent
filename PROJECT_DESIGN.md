# AI Agent 数据分析平台

> 项目名称：DataMind Agent
> 项目类型：AI Application / AI Agent / 数据分析平台
> 项目定位：基于 LLM + Agent + Python/SQL Tool 构建的智能数据分析平台
> 核心目标：让用户通过自然语言完成从数据理解、分析规划、数据计算、可视化到业务洞察和报告生成的完整数据分析流程。

---

# 1. 项目概述

## 1.1 项目背景

传统数据分析通常需要用户具备 SQL、Python、Excel 或 BI 工具使用能力。

用户提出一个业务问题后，通常需要经历：

```text
业务问题
    ↓
理解数据
    ↓
编写 SQL / Python
    ↓
执行查询
    ↓
整理结果
    ↓
制作图表
    ↓
人工分析
    ↓
撰写报告
```

DataMind Agent 希望通过 LLM 和 Agent 技术，将这一流程自动化。

用户只需要提出自然语言问题，例如：

> 为什么 8 月销售额下降？

系统自动完成：

```text
用户问题
    ↓
理解问题
    ↓
理解数据
    ↓
制定分析计划
    ↓
调用 Python / SQL Tool
    ↓
执行真实数据分析
    ↓
观察分析结果
    ↓
发现异常
    ↓
自动进一步下钻
    ↓
生成图表
    ↓
提取业务洞察
    ↓
生成分析报告
```

---

# 2. 项目目标

## 2.1 核心目标

构建一个具备自主数据分析能力的 AI Agent。

核心能力：

* 自然语言数据分析
* 数据集自动理解
* 自动生成分析计划
* Tool Calling
* Python 数据分析
* SQL 数据分析
* 自动图表生成
* 异常检测
* 自动分析下钻
* Agent 自我纠错
* 多轮上下文
* 分析证据追溯
* Agent Trace
* 分析报告生成
* Agent Evaluation

---

# 3. 产品定位

项目最终定位：

> **AI Business Analyst —— AI 智能数据分析师**

用户不需要知道：

* SQL
* Python
* Pandas
* 数据库查询
* 数据可视化

只需要描述自己的问题。

例如：

```text
帮我分析最近三个月销售趋势。

为什么 8 月销售下降？

哪个地区影响最大？

哪个 SKU 对销售下降贡献最大？

帮我找出异常客户。

如果继续下降，下个月可能是什么情况？
```

Agent 自动完成分析。

---

# 4. 核心产品流程

```text
                         用户
                          │
                          ↓
                      自然语言问题
                          │
                          ↓
                  ┌───────────────┐
                  │ Supervisor    │
                  │    Agent      │
                  └───────┬───────┘
                          ↓
                    Planner Agent
                          │
                          ↓
                     分析计划
                          │
             ┌────────────┼────────────┐
             ↓            ↓            ↓
          SQL Tool    Python Tool   Statistics
             │            │            │
             └────────────┼────────────┘
                          ↓
                    Analysis Agent
                          │
                          ↓
                    发现异常 / 趋势
                          │
                   是否需要继续分析
                    ↙           ↘
                  Yes            No
                   ↓              ↓
                RePlan         Insight
                   │              │
                   ↓              ↓
                Execute        Report
                   │              │
                   └──────┬───────┘
                          ↓
                       最终结果
```

---

# 5. 产品功能模块

平台主要包含以下模块：

| 模块               | 功能            |
| ---------------- | ------------- |
| Workspace        | 工作空间管理        |
| Data Source      | 数据源管理         |
| Dataset Profiler | 数据集自动分析       |
| AI Analysis      | AI Agent 数据分析 |
| Dashboard        | 数据可视化         |
| Report           | AI 分析报告       |
| Agent Trace      | Agent 执行过程    |
| Evaluation       | Agent 能力评估    |
| Settings         | 模型及系统配置       |

---

# 6. Workspace 工作空间

## 6.1 功能

用户可以创建多个数据分析工作空间。

例如：

```text
我的工作空间

├── 电商销售分析
├── 游戏运营分析
├── 用户增长分析
└── 广告投放分析
```

每个 Workspace 独立管理：

* 数据集
* 对话
* 分析任务
* Dashboard
* 报告
* Agent 执行记录

---

# 7. Data Source 数据源

## 7.1 V1

第一版本支持：

```text
Excel
CSV
JSON
```

---

## 7.2 V2

增加：

```text
MySQL
PostgreSQL
SQLite
```

---

## 7.3 V3

扩展：

```text
REST API
企业数据库
数据仓库
第三方数据平台
```

---

# 8. Dataset Profiler

Dataset Profiler 是 Agent 进行数据分析之前的数据理解模块。

用户上传：

```text
sales.xlsx
```

系统自动分析数据。

---

## 8.1 基础信息

```text
数据集名称：
sales.xlsx

记录数：
52,361

字段数：
8

时间范围：
2026-01-01 ~ 2026-08-31
```

---

## 8.2 字段识别

例如：

```text
date        datetime
region      string
product     string
category    string
sales       float
quantity    int
customer_id string
channel     string
```

---

## 8.3 数据质量分析

自动检测：

* 缺失值
* 重复值
* 异常值
* 唯一值
* 数值分布
* 数据类型
* 时间范围
* 分类数量
* 字段关联

---

## 8.4 Dataset Profile

最终生成：

```text
Dataset Profile

数据规模：
52,361 rows × 8 columns

时间字段：
date

数值字段：
sales
quantity

分类字段：
region
product
category
channel

缺失数据：
region：0.3%

异常数据：
sales：17 条
```

Dataset Profile 会作为后续 Agent 的基础 Context。

---

# 9. AI Analysis

AI Analysis 是平台核心页面。

建议采用：

```text
┌─────────────────────────────────────────────────────┐
│ DataMind Agent                                      │
├───────────────┬─────────────────────────────────────┤
│ Workspace     │                                     │
│               │ AI Analysis                         │
│ 数据集        │                                     │
│               │ User                                │
│ sales.xlsx    │ 为什么 8 月销售下降？                │
│               │                                     │
│               │ Agent                               │
│ 分析记录      │ 正在分析……                          │
│               │                                     │
│               │ ┌─────────────────────────────────┐ │
│               │ │ Agent Trace                     │ │
│               │ │ Planner ✓                       │ │
│               │ │ Python ✓                        │ │
│               │ │ Analysis ✓                      │ │
│               │ └─────────────────────────────────┘ │
│               │                                     │
│               │ Dashboard / Report                  │
└───────────────┴─────────────────────────────────────┘
```

---

# 10. Agent 架构

采用：

> **Supervisor + Specialized Agents**

整体架构：

```text
                   Supervisor Agent
                          │
                          ↓
                    Planner Agent
                          │
          ┌───────────────┼───────────────┐
          ↓               ↓               ↓
      SQL Agent       Python Agent    Statistics Agent
          │               │               │
          └───────────────┼───────────────┘
                          ↓
                    Analysis Agent
                          ↓
                    Insight Agent
                          ↓
                    Report Agent
```

---

# 11. Supervisor Agent

Supervisor Agent 负责整个 Agent 系统的调度。

主要职责：

* 管理 Agent 状态
* 判断下一步任务
* 调度不同 Agent
* 管理 Tool Calling
* 控制最大执行次数
* 处理异常
* 判断任务是否完成

---

# 12. Planner Agent

Planner Agent 负责将用户自然语言问题转换为可执行的分析计划。

例如：

用户：

```text
为什么 8 月销售下降？
```

Planner：

```json
{
  "goal": "分析8月销售下降原因",
  "steps": [
    "计算7月和8月销售额",
    "计算环比变化",
    "按地区分析",
    "按商品分析",
    "按渠道分析",
    "分析客户变化",
    "定位主要下降原因"
  ]
}
```

---

# 13. Python Agent

Python Agent 负责：

* 数据计算
* 数据清洗
* 数据聚合
* 趋势分析
* 统计分析
* 异常检测
* 相关性分析

例如：

```python
monthly_sales = (
    df.groupby(df["date"].dt.to_period("M"))["sales"]
      .sum()
)

monthly_sales.pct_change()
```

代码生成后交给 Python Sandbox 执行。

---

# 14. SQL Agent

当数据源是数据库时，由 SQL Agent 自动生成 SQL。

例如：

```sql
SELECT
    region,
    SUM(sales) AS total_sales
FROM sales
GROUP BY region
ORDER BY total_sales DESC;
```

执行后将真实结果返回给 Agent。

---

# 15. Analysis Agent

Analysis Agent 负责理解工具执行结果。

例如：

```text
Python 执行结果：

华东：
7月：2,340,000
8月：1,761,000

下降：
24.7%
```

Agent 判断：

> 华东地区是整体销售下降的重要来源。

随后继续触发更深入的数据分析。

---

# 16. Insight Agent

Insight Agent 负责从分析结果中提取业务洞察。

采用：

```text
Observation
    ↓
Evidence
    ↓
Reason
    ↓
Impact
    ↓
Recommendation
```

例如：

```text
发现：

8 月销售下降 17.4%

↓

证据：

华东地区销售下降 24.7%

↓

进一步分析：

SKU-A 销售下降 42%

↓

根因：

两个核心客户停止采购

↓

建议：

优先针对核心客户进行召回
```

---

# 17. Report Agent

Report Agent 负责生成最终分析报告。

报告结构：

```text
AI 数据分析报告

1. Executive Summary

2. Key Findings

3. Sales Trend

4. Regional Analysis

5. Product Analysis

6. Customer Analysis

7. Root Cause

8. Recommendations

9. Data Evidence
```

支持：

```text
Markdown
PDF
Excel
```

---

# 18. Tool Calling

Agent 的核心能力来自 Tools。

第一版本实现：

```text
dataset_schema
dataset_preview
python_execute
sql_query
statistics
anomaly_detection
correlation_analysis
generate_chart
report_generate
```

后续扩展：

```text
web_search
database
API
RAG
MCP
email
notification
```

---

# 19. Python Sandbox

Python Sandbox 是项目的重要技术模块。

Agent 生成 Python 代码后，不能直接运行在主服务环境中。

执行流程：

```text
LLM
 ↓
生成 Python Code
 ↓
Sandbox
 ↓
Execute
 ↓
Result
 ↓
LLM 分析
```

---

## 19.1 安全限制

Sandbox 需要限制：

```text
文件访问
网络访问
进程创建
系统命令
CPU 使用
内存使用
执行时间
```

增加：

```text
Timeout
Memory Limit
CPU Limit
File Isolation
```

---

# 20. Agent Loop

核心 Agent 执行模型：

```text
START
  ↓
UNDERSTAND
  ↓
PLAN
  ↓
EXECUTE
  ↓
OBSERVE
  ↓
REPLAN
  ↓
EXECUTE
  ↓
OBSERVE
  ↓
INSIGHT
  ↓
REPORT
  ↓
END
```

核心思想：

> **Plan → Execute → Observe → RePlan**

---

# 21. Agent State

建议设计统一 Agent State：

```python
class AgentState:

    question: str

    dataset_id: str

    schema: dict

    plan: list

    current_step: int

    observations: list

    tool_results: list

    charts: list

    insights: list

    errors: list

    final_answer: str
```

Agent State 用于：

* Agent Resume
* Retry
* Memory
* Trace
* Evaluation

---

# 22. Reflection / Self Correction

Agent 需要具备自动纠错能力。

例如：

```text
生成 Python
    ↓
执行
    ↓
KeyError: city
    ↓
读取 Dataset Schema
    ↓
发现字段实际为 region
    ↓
修改代码
    ↓
重新执行
```

完整流程：

```text
Generate
   ↓
Execute
   ↓
Error
   ↓
Reflect
   ↓
Fix
   ↓
Execute Again
```

---

# 23. 自动可视化

Agent 根据数据类型自动选择图表。

| 数据场景 | 推荐图表        |
| ---- | ----------- |
| 时间趋势 | Line Chart  |
| 分类比较 | Bar Chart   |
| 占比分析 | Donut / Pie |
| 数据分布 | Histogram   |
| 相关性  | Scatter     |
| 地区分析 | Map         |
| 多维分析 | Heatmap     |

---

# 24. Dashboard

自动生成数据分析 Dashboard。

示例：

```text
┌──────────────┬──────────────┬──────────────┐
│ 总销售额     │ 环比         │ 客户数       │
│ ¥12.4M       │ -17.4%       │ 8,231        │
└──────────────┴──────────────┴──────────────┘

                 销售趋势

              /\        /\
             /  \      /  \
       _____/    \____/    \__
                          ↓
                        August


地区销售变化

华东   ██████████       -24.7%
华北   █████████████     -3.0%
华南   ██████████████    +4.0%
```

---

# 25. Evidence 数据证据链

AI 给出的重要结论必须能够追溯。

例如：

> 华东地区销售下降 24.7%。

用户点击：

> 查看证据

系统显示：

```text
SQL：

SELECT
    region,
    SUM(sales)
FROM sales
GROUP BY region;
```

执行结果：

```text
Region    July       August
华东      2.34M      1.76M
```

同时展示：

```text
Data Source
SQL / Python
Execution Result
Analysis
```

实现：

> **AI 结论可追溯。**

---

# 26. Agent Trace

开发模式下展示完整 Agent 执行过程。

```text
Agent Trace

01 User
   为什么 8 月销售下降？

02 Planner
   生成 6 步分析计划

03 Dataset Tool
   获取 Schema

04 Python Agent
   分析月销售趋势

05 Python Tool
   Execute ✓

06 Analysis Agent
   发现华东异常

07 Planner
   Drill Down → 华东

08 Python Agent
   分析 SKU

09 Analysis Agent
   SKU-A 下降 42%

10 Planner
   Drill Down → Customer

11 Insight Agent
   发现核心客户流失

12 Report Agent
   生成报告
```

---

# 27. Memory

支持多轮数据分析上下文。

例如：

```text
用户：
分析 8 月销售。

AI：
……

用户：
只看华东。

AI：
……

用户：
再看看商品。

AI：
……
```

Agent 自动维护：

```text
Dataset = sales.xlsx
Month = August
Region = 华东
```

---

# 28. 异常处理

需要处理：

```text
Python 执行失败
SQL 错误
Token 超限
数据过大
字段不存在
LLM JSON 格式错误
Agent 无限循环
Tool Timeout
结果为空
```

对应机制：

```text
Retry
Fallback
Timeout
Validation
Reflection
Max Steps
```

例如：

```python
MAX_AGENT_STEPS = 20
```

防止 Agent 无限执行。

---

# 29. 数据处理架构

根据数据规模选择不同的数据处理方式。

```text
Small Data
    ↓
Pandas

Large File
    ↓
DuckDB

Database
    ↓
SQL Agent
```

推荐技术：

```text
Pandas
Polars
DuckDB
```

---

# 30. 数据库设计

核心数据表：

```text
users

workspaces

datasets

dataset_fields

conversations

messages

agent_runs

agent_steps

tool_calls

analysis_results

charts

reports
```

---

## 30.1 agent_runs

```text
run_id
conversation_id
question
status
model
input_tokens
output_tokens
cost
latency
created_at
```

---

## 30.2 tool_calls

```text
tool_name
arguments
result
duration
success
error
```

这些数据后续可以直接用于 Evaluation。

---

# 31. 技术架构

```text
                    Frontend
                React / Next.js
                       │
                       ↓
                     FastAPI
                       │
                       ↓
                Agent Runtime
                       │
              ┌────────┴────────┐
              ↓                 ↓
          LLM Gateway          Tools
              │          ┌──────┼──────┐
              │          ↓      ↓      ↓
              │       Python   SQL    Chart
              │       Sandbox
              │
              ↓
       OpenAI / Claude /
       Gemini / DeepSeek /
       Qwen / Local LLM

                       │
                       ↓
                  Data Layer
              ┌────────┼────────┐
              ↓        ↓        ↓
         PostgreSQL   Redis   Object Storage
```

---

# 32. 推荐技术栈

## Frontend

```text
React
Next.js
TypeScript
Tailwind CSS
ECharts / Recharts
```

## Backend

```text
Python
FastAPI
Pydantic
SQLAlchemy
```

## Agent

```text
LangGraph
```

或者：

```text
自研 Agent State Machine
```

建议核心 Agent Loop 自己理解并实现一部分，不要完全依赖框架黑盒。

---

## Data

```text
Pandas
Polars
DuckDB
```

## Database

```text
PostgreSQL
Redis
```

## Object Storage

```text
MinIO
S3
```

## LLM

通过统一 LLM Gateway 支持：

```text
OpenAI
Claude
Gemini
DeepSeek
Qwen
Local LLM
```

---

# 33. V1 MVP

第一版本只实现最核心的数据分析链路。

```text
Excel / CSV
     ↓
Dataset Profiler
     ↓
自然语言问题
     ↓
Planner
     ↓
Python Agent
     ↓
Python Sandbox
     ↓
Analysis
     ↓
Chart
     ↓
Insight
     ↓
最终回答
```

准备一份：

> 电商销售 Dataset

实现一个完整 Demo：

> 为什么 8 月销售下降？

Agent 自动完成：

```text
整体趋势
   ↓
地区分析
   ↓
商品分析
   ↓
客户分析
   ↓
发现异常
   ↓
自动下钻
   ↓
生成图表
   ↓
生成结论
```

---

# 34. V2 —— Agent 化

增加：

```text
Supervisor
Planner
Tool Calling
Agent Loop
RePlan
Reflection
Memory
```

形成：

```text
Plan
 ↓
Execute
 ↓
Observe
 ↓
RePlan
 ↓
Execute
```

---

# 35. V3 —— 工程化

增加：

```text
Python Sandbox
SQL Sandbox
Agent Trace
Retry
Timeout
Cost Tracking
Permission
Logging
```

项目从 Demo 向 Production AI 演进。

---

# 36. V4 —— Evaluation

增加 Agent Evaluation：

```text
Task Success Rate
Tool Success Rate
Python Success Rate
SQL Accuracy
Calculation Accuracy
Insight Accuracy
Chart Accuracy
Hallucination Rate
Latency
Token Cost
```

Dashboard：

```text
AI Agent Evaluation

Task Success       91.2%
Tool Success       96.7%
Python Success     94.2%

Avg Steps           7.8
Avg Latency        12.4s
Avg Tokens         8,421
Avg Cost           $0.032
```

---

# 37. V5 —— 企业级能力

最终扩展：

```text
MySQL
PostgreSQL
RAG
MCP
API Tool
Web Search
多用户
权限
团队协作
数据权限
审计日志
模型管理
Prompt Management
```

最终形成：

> **AI Business Analyst Platform**

---

# 38. 核心 Demo 场景

## 场景：分析销售下降原因

### Step 1：上传数据

```text
sales.xlsx
```

---

### Step 2：Dataset Profiler

```text
52,361 条记录
8 个字段
时间范围：8个月
```

---

### Step 3：用户提问

```text
为什么 8 月销售下降？
```

---

### Step 4：Planner

```text
生成 6 步分析计划
```

---

### Step 5：分析整体趋势

```text
August
-17.4%
```

---

### Step 6：自动分析地区

```text
华东
-24.7%
```

---

### Step 7：自动分析商品

```text
SKU-A
-42%
```

---

### Step 8：自动分析客户

```text
两个核心客户停止采购
```

---

### Step 9：Insight Agent

生成：

```text
整体销售下降的主要原因：

1. 华东地区销售下降
2. SKU-A 表现下降
3. 核心客户流失
```

---

### Step 10：自动生成图表

```text
销售趋势图
地区对比图
SKU 分析图
客户变化图
```

---

### Step 11：生成报告

```text
Executive Summary

Key Findings

Root Cause

Evidence

Recommendations
```

---

# 39. 项目技术亮点

项目重点展示以下能力：

## 39.1 LLM Gateway

统一不同模型调用接口。

---

## 39.2 Agent State Machine

管理 Agent 生命周期。

---

## 39.3 Planner

自动生成数据分析计划。

---

## 39.4 Tool Calling

让 LLM 操作真实工具。

---

## 39.5 Code Interpreter

让 Agent 执行 Python。

---

## 39.6 Sandbox

隔离并限制 AI 生成代码。

---

## 39.7 Agentic Loop

实现：

```text
Plan
 ↓
Execute
 ↓
Observe
 ↓
RePlan
```

---

## 39.8 Reflection

实现 Agent 自动纠错。

---

## 39.9 Evidence

让 AI 结论可追溯。

---

## 39.10 Evaluation

量化 Agent 的实际能力。

---

# 40. 项目目录结构

```text
datamind-agent/

├── apps/
│   └── web/
│
├── server/
│   ├── api/
│   └── services/
│
├── agent/
│   ├── supervisor/
│   ├── planner/
│   ├── analyst/
│   ├── insight/
│   ├── reporter/
│   ├── graph/
│   └── state/
│
├── tools/
│   ├── python/
│   ├── sql/
│   ├── dataset/
│   ├── chart/
│   └── statistics/
│
├── sandbox/
│   ├── executor/
│   └── security/
│
├── data/
│   ├── parser/
│   └── profiler/
│
├── llm/
│   ├── providers/
│   ├── prompts/
│   └── gateway/
│
├── evaluation/
│   ├── datasets/
│   ├── metrics/
│   └── evaluator/
│
├── storage/
│   ├── database/
│   └── cache/
│
└── tests/
```

---

# 41. 开发路线

项目按照以下模块逐步开发：

```text
01 项目骨架
      ↓
02 数据上传
      ↓
03 Dataset Profiler
      ↓
04 Chat / Streaming
      ↓
05 Python Tool
      ↓
06 Planner Agent
      ↓
07 Agent Loop
      ↓
08 自动图表
      ↓
09 Insight Agent
      ↓
10 Report Agent
      ↓
11 Agent Trace
      ↓
12 Memory
      ↓
13 Reflection / Retry
      ↓
14 Python Sandbox
      ↓
15 Evaluation
      ↓
16 企业级扩展
```

---

# 42. 开发原则

## 原则一：先跑通，再抽象

不要一开始设计过度复杂的 Agent Framework。

先实现：

```text
Question
 ↓
Planner
 ↓
Python
 ↓
Result
 ↓
Answer
```

再逐步抽象。

---

## 原则二：LLM 不负责计算

不要：

```text
数据
 ↓
LLM
 ↓
计算结果
```

应该：

```text
数据
 ↓
Python / SQL
 ↓
真实结果
 ↓
LLM
 ↓
业务解释
```

---

## 原则三：Agent 必须有边界

设置：

```text
Max Steps
Timeout
Token Limit
Tool Permission
Sandbox
```

---

## 原则四：所有重要结论必须有证据

```text
AI Conclusion
      ↓
Evidence
      ↓
Tool Call
      ↓
Data
```

---

## 原则五：Agent 必须可观察

保存：

```text
Agent Run
Agent Step
Tool Call
Tool Result
Error
Latency
Token
Cost
```

---

# 43. 面试展示重点

面试 Demo 不应该只展示：

> “上传 Excel，然后 AI 给答案。”

应该重点展示：

### 1. Agent Planning

展示 AI 如何制定分析计划。

### 2. Tool Calling

展示 AI 为什么选择 Python / SQL。

### 3. Code Execution

展示生成代码并真实执行。

### 4. Agent Loop

展示：

```text
Plan
→ Execute
→ Observe
→ RePlan
```

### 5. Autonomous Drill Down

展示 AI 如何根据结果自主决定下一步分析。

### 6. Reflection

故意制造字段错误，让 Agent 自动修复。

### 7. Evidence

点击结论查看真实数据和代码。

### 8. Trace

展示完整 Agent 执行链路。

### 9. Evaluation

展示 Agent 成功率、耗时、Token、成本。

---

# 44. 简历项目描述

## 项目名称

**DataMind Agent —— AI 智能数据分析平台**

## 项目描述

基于 LLM 和 Agent 技术构建智能数据分析平台，支持 Excel、CSV 及数据库数据接入，通过自然语言实现数据探索、趋势分析、异常检测、自动下钻、可视化及分析报告生成。

## 技术亮点

* 设计 Supervisor + Specialized Agents 架构，实现 Planner、Python Agent、SQL Agent、Analysis Agent、Insight Agent 和 Report Agent 协同工作。
* 构建 `Plan → Execute → Observe → RePlan` Agent Loop，实现复杂数据分析任务的自主规划与动态下钻。
* 基于 Python Sandbox 实现 AI 生成代码的安全执行，并加入 Timeout、资源限制、Retry 和 Reflection 机制。
* 实现 Tool Calling、Dataset Profiler、自动图表生成、Agent Memory、Agent Trace 和 Evidence Chain。
* 构建 Agent Evaluation 模块，从 Task Success、Tool Success、Calculation Accuracy、Insight Accuracy、Latency、Token Cost 等维度量化 Agent 能力。

---

# 45. 最终产品能力

最终 DataMind Agent 应具备：

```text
                 DataMind Agent
                       │
                       ↓
                  数据接入
                       ↓
                  数据理解
                       ↓
                 自然语言提问
                       ↓
                  任务规划
                       ↓
                 Tool Calling
                       ↓
                Python / SQL
                       ↓
                  真实执行
                       ↓
                   结果观察
                       ↓
                  自动纠错
                       ↓
                  自动下钻
                       ↓
                   异常检测
                       ↓
                   数据可视化
                       ↓
                   业务洞察
                       ↓
                    证据链
                       ↓
                    分析报告
                       ↓
                 Agent Evaluation
```

---

# 46. 项目最终定位

DataMind Agent 最终不是：

> 一个可以和 Excel 聊天的 AI。

而是：

> **一个能够自主完成真实数据分析任务的 AI Business Analyst。**

项目核心技术路线：

```text
LLM
 ↓
Tool Calling
 ↓
Code Interpreter
 ↓
Agent
 ↓
Agent Loop
 ↓
Reflection
 ↓
Memory
 ↓
Sandbox
 ↓
Trace
 ↓
Evaluation
 ↓
Production AI
```

---

# 47. 后续扩展方向

完成 DataMind Agent 后，可以继续向以下方向扩展：

```text
DataMind Agent
      │
      ├── RAG
      │
      ├── MCP
      │
      ├── Multi-Agent
      │
      ├── AI Workflow
      │
      ├── LLM Evaluation
      │
      ├── AI Coding Agent
      │
      └── Enterprise AI
```

最终形成完整的 AI Application 技术能力体系：

```text
AI Coding
    +
RAG
    +
Tool Calling
    +
Agent
    +
Workflow
    +
Sandbox
    +
Evaluation
    ↓
AI Application Engineer
```

---

# 48. 项目开发阶段总览

| 阶段       | 核心内容             | 目标          |
| -------- | ---------------- | ----------- |
| Phase 1  | 项目骨架             | 跑通基础服务      |
| Phase 2  | 数据上传             | 建立数据入口      |
| Phase 3  | Dataset Profiler | AI 理解数据     |
| Phase 4  | Chat             | 自然语言交互      |
| Phase 5  | Python Tool      | AI 执行数据分析   |
| Phase 6  | Planner          | AI 自主规划     |
| Phase 7  | Agent Loop       | 自主执行与下钻     |
| Phase 8  | Visualization    | 自动生成图表      |
| Phase 9  | Insight / Report | 生成业务结论      |
| Phase 10 | Trace            | Agent 可观察   |
| Phase 11 | Sandbox          | 安全执行        |
| Phase 12 | Evaluation       | 量化 Agent 能力 |
| Phase 13 | Enterprise       | 企业级扩展       |

---

# 49. 项目完成标准

当以下流程能够完整运行时，项目达到第一个重要里程碑：

```text
上传 sales.xlsx
       ↓
自动识别数据结构
       ↓
用户：
“为什么8月销售下降？”
       ↓
Planner生成分析计划
       ↓
Python Agent生成分析代码
       ↓
Sandbox执行
       ↓
发现整体下降17.4%
       ↓
Agent自动分析地区
       ↓
发现华东下降24.7%
       ↓
Agent继续分析SKU
       ↓
发现SKU-A下降42%
       ↓
Agent继续分析客户
       ↓
发现核心客户流失
       ↓
生成图表
       ↓
生成业务洞察
       ↓
输出分析报告
       ↓
展示完整Agent Trace
       ↓
所有结论可以查看Evidence
```

**这条链路跑通，就是 DataMind Agent 的 V1 核心 Demo。**
