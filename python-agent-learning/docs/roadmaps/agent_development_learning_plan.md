# Agent 开发线学习计划

## 目标

8 周内完成一个能跑、能调试、能评估、能讲清楚的 Agent 应用项目。

推荐项目方向：

> 页面需求分析 Agent：输入一段页面需求，输出组件拆分、状态设计、接口假设、交互风险和测试点。

这个方向贴合前端背景，也能覆盖 Agent 开发线的核心能力：结构化输出、工具调用、上下文管理、评估和工程化。

## 学习原则

1. 不追框架大全，只围绕一个项目推进。
2. 每周必须有代码产出或评估产出。
3. 优先学习能迁移的工程能力：Agent Loop、Tool Use、Context、Eval、Trace。
4. 暂时不投入模型微调、Agentic RL、论文复现。

学习过程中的每日理解、企业场景判断和项目复盘统一记录到 `learning_notes/`。

## 学习链接索引

- AgentGuide：https://github.com/adongwanai/AgentGuide
- AgentGuide 开发岗路线：https://github.com/adongwanai/AgentGuide/blob/main/docs/05-roadmaps/learning-roadmap-development.md
- AgentGuide 文档导航：https://github.com/adongwanai/AgentGuide/blob/main/docs/README.md
- Agent Harness Engineering：https://github.com/adongwanai/AgentGuide/blob/main/docs/02-tech-stack/27-agent-harness-engineering.md
- Context Engineering 资源：https://github.com/adongwanai/AgentGuide/blob/main/docs/02-tech-stack/13-context-engineering-resources.md
- Context Engineering 2.0：https://github.com/adongwanai/AgentGuide/blob/main/docs/02-tech-stack/18-context-engineering-guide.md
- MCP 协议指南：https://github.com/adongwanai/AgentGuide/blob/main/docs/02-tech-stack/10-mcp-protocol.md
- Agent 评估指南：https://github.com/adongwanai/AgentGuide/blob/main/docs/02-tech-stack/agent-evaluation-complete-guide.md
- Hello-Agents 在线阅读：https://hello-agents.datawhale.cc/
- Hello-Agents GitHub：https://github.com/datawhalechina/hello-agents
- Hello-Agents 视频课导航：https://github.com/datawhalechina/hello-agents/blob/main/Extra-Chapter/Extra13-Hello-Agents%E8%A7%86%E9%A2%91%E8%AF%BE%E5%BD%95%E5%88%B6%E5%85%B1%E5%88%9B.md
- Deep Agents 实战：https://datawhalechina.github.io/deepagents-in-action/
- Deep Agents 实战 B 站合集：https://space.bilibili.com/28357052/lists/7757577?type=season
- LangGraph 官方文档：https://langchain-ai.github.io/langgraph/
- LangChain Academy：https://academy.langchain.com/
- Hugging Face Agents Course：https://huggingface.co/learn/agents-course/unit0/introduction
- Anthropic Building Effective Agents：https://www.anthropic.com/engineering/building-effective-agents

## AgentGuide 7 天实践版

这部分对应 AgentGuide 的第一周实践清单：

- 原文：https://github.com/adongwanai/AgentGuide/blob/main/docs/00-getting-started/02-first-7-days.md

不要把这 7 天当成“再看一堆资料”，而是当成当前项目的第一轮小闭环。

### Day 1：建立边界

目标：

- 说清楚页面需求分析为什么需要 Agent。
- 说清楚哪些部分只是普通 Workflow。

实践：

- 打开 `02_requirement_analyzer.py`。
- 用一句话写清楚输入、输出、失败边界：
  - 输入：自然语言页面需求。
  - 输出：前端可执行的结构化信息。
  - 工具：暂时无工具，先只做结构化输出。
  - 失败边界：漏字段、字段语义不准、测试点太泛。

产出：

- 新建或补充一页笔记：`agent_boundary_notes.md`。

### Day 2：手写最小 Agent Loop

目标：

- 理解 `observe -> think -> act -> observe`。

实践：

- 不急着上 LangGraph。
- 先写一个普通 Python 循环，最大 5 步。
- 每一步只做一件事：
  1. 识别页面目标。
  2. 拆组件。
  3. 推断状态。
  4. 生成风险点。
  5. 生成测试点。

建议文件：

- 可以新建 `09_requirement_agent_loop.py`。

产出：

- 能处理 5 条固定页面需求。
- 出错时返回可读失败原因，而不是直接崩溃。

### Day 3：工具设计

目标：

- 让工具变得“模型友好”。

实践：

- 参考 `03_tool_calling.py`。
- 给页面需求分析 Agent 设计 3 个本地工具：
  - `extract_components(requirement)`
  - `infer_state(requirement)`
  - `generate_test_points(requirement)`

每个工具都写清楚：

- 工具名。
- 什么时候用。
- 输入参数。
- 返回结构。
- 错误码。
- 示例。

产出：

- 一个 `tools` 列表或工具注册表。
- 至少 3 个工具调用失败样例。

### Day 4：上下文工程

目标：

- 控制什么内容进入模型。

实践：

- 新建 `context_template.md`。
- 把 prompt 分成 5 层：
  - `system`：角色和总体规则。
  - `task`：当前页面需求。
  - `schema`：输出字段。
  - `examples`：少量优质样例。
  - `recent_trace`：最近一次失败摘要。

约束：

- 不把完整日志直接塞进模型。
- 不一次放太多样例。
- 输出 schema 固定，便于评估。

产出：

- 一份稳定的上下文模板。
- 对比有无 examples 时的输出差异。

### Day 5：评测集

目标：

- 从“感觉能用”变成“可测量”。

实践：

- 参考 `07_eval_regression.py`。
- 写 20 条 eval case：
  - 10 条正常页面需求。
  - 5 条边界需求。
  - 5 条失败/安全需求。

每条 case 包含：

- 输入。
- 期望字段。
- 禁止行为。
- 评分方式。

产出：

- `eval_cases.json`。
- 一份通过率统计。
- 失败原因分类。

### Day 6：项目化包装

目标：

- 让别人能 clone、运行、理解。

实践：

- 给项目补 README 小节：
  - 项目目标。
  - 架构。
  - 安装。
  - 运行。
  - 测试。
  - 已知限制。

产出：

- `README.md` 中新增“页面需求分析 Agent”说明。
- `eval_report.md` 记录评测结果。
- `demo_script.md` 记录演示脚本。

### Day 7：复盘与简历表达

目标：

- 把项目变成可讲述的工程经验。

实践：

- 做一次失败归因：
  - schema 漏字段。
  - 模型误判。
  - 工具返回太泛。
  - 上下文污染。
  - 缺少边界样例。

产出：

- 一段项目描述：

```text
基于轻量 Agent Loop 构建页面需求分析 Agent，将自然语言页面需求结构化为组件拆分、状态设计、接口假设、风险点和测试点；设计工具注册表、分层 context template、JSONL trace 和 20 条 eval case，用于验证输出合法性和关键字段覆盖率。
```

## 第 1 周：建立 Agent 坐标系

学习重点：

- 区分 Chatbot、Workflow、Agent、Multi-Agent。
- 理解 Agent Loop：observe -> think/plan -> act -> observe。
- 理解 Tool Use 和结构化输出。

建议资料：

- `AgentGuide`：Agent 核心概念、开发岗路线。
  - https://github.com/adongwanai/AgentGuide
  - https://github.com/adongwanai/AgentGuide/blob/main/docs/05-roadmaps/learning-roadmap-development.md
- `hello-agents`：第一章只泛读，重点看 Agent 定义和范式。
  - https://hello-agents.datawhale.cc/
  - https://github.com/datawhalechina/hello-agents

代码任务：

- 阅读并运行 `01_cli_chat.py`。
- 阅读并运行 `02_requirement_analyzer.py`。
- 记录当前脚本的输入、输出、模型调用和失败点。

产出：

- 一页笔记：什么时候需要 Agent，什么时候普通 Workflow 就够了。

## 第 2 周：结构化需求分析

学习重点：

- Prompt 约束。
- JSON 结构化输出。
- 字段设计和校验。

建议资料：

- Hugging Face Agents Course：看 Tool 和结构化输出相关内容。
  - https://huggingface.co/learn/agents-course/unit0/introduction
- Anthropic Building Effective Agents：看 Workflow 和 Agent 的边界。
  - https://www.anthropic.com/engineering/building-effective-agents

代码任务：

- 扩展 `02_requirement_analyzer.py` 的输出结构。
- 建议字段：
  - `page_type`
  - `target_users`
  - `core_components`
  - `user_actions`
  - `state_requirements`
  - `api_assumptions`
  - `risk_points`
  - `test_points`

产出：

- 5 条页面需求样例。
- 5 份结构化输出结果。
- 手动标注输出是否可用于前端开发。

## 第 3 周：最小工具调用 Agent

学习重点：

- Tool Schema。
- 工具注册。
- 工具选择。
- 工具调用失败处理。

建议资料：

- `AgentGuide`：Tool Design、Agent Loop。
  - https://github.com/adongwanai/AgentGuide
- `03_tool_calling.py`。

代码任务：

- 阅读并运行 `03_tool_calling.py`。
- 给需求分析 Agent 增加 2-3 个本地工具：
  - `extract_components(requirement)`
  - `infer_state(requirement)`
  - `generate_test_points(requirement)`

产出：

- 一个可以显式调用工具的需求分析 Demo。
- 记录至少 3 个工具调用失败案例。

## 第 4 周：Agent Loop 与终止条件

学习重点：

- 多轮执行循环。
- 最大步数。
- 停止条件。
- Retry / fallback。

建议资料：

- Hello-Agents：重点看 ReAct、Plan-and-Solve、Reflection。
  - https://hello-agents.datawhale.cc/
- LangGraph 官方文档：了解状态图和循环控制。
  - https://langchain-ai.github.io/langgraph/

代码任务：

- 把需求分析流程拆成多步：
  1. 分析页面类型。
  2. 拆组件。
  3. 推断状态。
  4. 生成风险点。
  5. 生成测试点。
- 给每一步加失败兜底。

产出：

- 一个 100-200 行的最小 Agent Loop。
- README 里写清楚流程图和终止条件。

## 第 5 周：Context Engineering

学习重点：

- 上下文分层。
- 当前任务上下文。
- 历史样例。
- 输出格式约束。
- 无关信息裁剪。

建议资料：

- `AgentGuide`：Context Engineering。
  - https://github.com/adongwanai/AgentGuide/blob/main/docs/02-tech-stack/13-context-engineering-resources.md
  - https://github.com/adongwanai/AgentGuide/blob/main/docs/02-tech-stack/18-context-engineering-guide.md
- Datawhale `Deep Agents 实战` 中 Context Engineering 相关章节。
  - https://datawhalechina.github.io/deepagents-in-action/
  - https://space.bilibili.com/28357052/lists/7757577?type=season

代码任务：

- 为需求分析 Agent 设计上下文模板：
  - system rule
  - task input
  - output schema
  - examples
  - constraints
- 控制样例数量，避免无限堆上下文。

产出：

- 一份 `context_template.md`。
- 对比有无 examples 时的输出稳定性。

## 第 6 周：Trace、日志与可调试性

学习重点：

- 每一步输入输出记录。
- 工具调用日志。
- 失败原因归因。
- 成本与耗时记录。

建议资料：

- Agent Harness Engineering：重点看 trace、replay、observability。
  - https://github.com/adongwanai/AgentGuide/blob/main/docs/02-tech-stack/27-agent-harness-engineering.md
- Deep Agents 实战：看 Streaming、Trace、工具事件流相关章节。
  - https://datawhalechina.github.io/deepagents-in-action/

代码任务：

- 给 Agent 加简单 trace：
  - step name
  - input
  - output
  - tool name
  - error
  - duration
- 输出保存为 JSONL。

产出：

- 至少 10 条运行 trace。
- 总结最常见的 3 类失败。

## 第 7 周：Eval 与回归测试

学习重点：

- eval case 设计。
- 通过率。
- 失败分类。
- 回归测试。

建议资料：

- `AgentGuide`：Eval / Observability / Safety。
  - https://github.com/adongwanai/AgentGuide/blob/main/docs/02-tech-stack/agent-evaluation-complete-guide.md
- `07_eval_regression.py`。

代码任务：

- 阅读并运行 `07_eval_regression.py`。
- 为需求分析 Agent 建立 20 条 eval case。
- 每条 case 至少检查：
  - 是否输出合法 JSON。
  - 是否包含核心组件。
  - 是否包含状态需求。
  - 是否包含测试点。

产出：

- `eval_cases.json`。
- 一份评估结果表。
- 失败原因分类。

## 第 8 周：项目化整理

学习重点：

- 项目说明。
- 架构表达。
- 工程取舍。
- 简历表达。

建议资料：

- AgentGuide：如何落地一个可写进简历的 Agent 项目。
  - https://github.com/adongwanai/AgentGuide/blob/main/docs/03-practice/05-ship-agent-project.md
- AgentGuide：开发岗路线。
  - https://github.com/adongwanai/AgentGuide/blob/main/docs/05-roadmaps/learning-roadmap-development.md

代码任务：

- 整理项目入口。
- 补 README。
- 加运行示例。
- 加 eval 结果。

产出：

- 一个可 clone 后运行的项目。
- 一段简历描述：

```text
基于轻量 Agent Loop 构建页面需求分析 Agent，将自然语言页面需求结构化为组件拆分、状态设计、接口假设、风险点和测试点；实现工具注册、分步执行、失败兜底、JSONL Trace 与 20 条 eval case，支持对输出合法性和关键字段覆盖率进行回归评估。
```

## 每周节奏

- 周一到周二：看资料，只看当前任务相关内容。
- 周三到周五：写代码。
- 周六：跑 eval，记录失败。
- 周日：整理笔记和下周任务。

## 暂时不学

- Agentic RL。
- SFT / DPO / GRPO。
- 多模态训练。
- 论文算法优化。
- 大量框架横向对比。

## 优先级最高的能力

1. 把需求拆成结构化任务。
2. 设计工具边界。
3. 控制上下文。
4. 记录可调试 trace。
5. 用 eval 证明效果。
6. 讲清楚工程取舍。
