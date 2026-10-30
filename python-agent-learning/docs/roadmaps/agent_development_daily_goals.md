# Agent 开发线每日学习目标

> 配套主计划：`agent_development_learning_plan.md`
>
> 使用方式：每天只完成当天目标，不提前横向扩展框架；每日笔记继续写到 `docs/notes/learning_notes/daily/`。

## 是否需要新建文件夹

不需要。

当前目录已经够用：

- `docs/roadmaps/`：放学习路线和每日目标。
- `docs/notes/learning_notes/daily/`：放每日学习笔记。
- `docs/checklists/`：后续可放验收清单。
- `docs/concepts/`：后续可放概念卡片。
- `tests/`：放确定性逻辑测试和 eval 回归测试。

本文件直接放在 `docs/roadmaps/`，避免新增重复目录。

## 第 1 周：建立 Agent 坐标系

目标：先分清 Chatbot、Workflow、Agent 的边界，跑通最小模型调用和结构化输出。

| 天数 | 学习目标 | 实操任务 | 验收标准 |
| --- | --- | --- | --- |
| Day 1 | 建立 Agent / Workflow 边界 | 阅读主计划 Day 1，补充 `agent_boundary_notes.md` | 能说清页面需求分析中哪些是 workflow，哪些才需要 Agent |
| Day 2 | 跑通模型调用 | 运行 `01_cli_chat.py`，修改 system prompt 和 temperature | 能解释 message、system、human、response.content |
| Day 3 | 理解结构化输出 | 运行 `02_requirement_analyzer.py` | 能解释 Pydantic schema 如何约束模型输出 |
| Day 4 | 拆解页面需求字段 | 给输出模型增加 `page_type`、`target_users`、`test_points` | 输出 JSON 能被 Python 继续处理 |
| Day 5 | 梳理失败边界 | 准备 3 条模糊需求，观察输出缺陷 | 能记录漏字段、误判、泛化输出等失败类型 |
| Day 6 | 写第一份学习笔记 | 总结 Agent、Workflow、结构化输出关系 | 笔记中包含 1 个生活类比和 1 个代码例子 |
| Day 7 | 周复盘 | 整理本周代码和笔记 | 能用 3 分钟讲清“为什么先学结构化输出” |

## 第 2 周：结构化需求分析

目标：把页面需求稳定转成前端可执行结构，而不是只让模型自由回答。

| 天数 | 学习目标 | 实操任务 | 验收标准 |
| --- | --- | --- | --- |
| Day 1 | 明确输出字段职责 | 设计 `page_type`、`core_components`、`state_requirements` 等字段 | 每个字段都有一句职责说明 |
| Day 2 | 扩展 Pydantic 模型 | 修改 `02_requirement_analyzer.py` 的数据模型 | 运行后能输出新增字段 |
| Day 3 | 准备需求样例 | 写 5 条页面需求样例 | 样例覆盖列表页、详情页、表单页、弹窗、批量操作 |
| Day 4 | 人工检查输出质量 | 对 5 份输出做手动标注 | 能指出每份输出是否可用于前端开发 |
| Day 5 | 补字段校验 | 给关键字段增加非空或类型约束 | 错误输入时能返回可读失败信息 |
| Day 6 | 总结结构化输出模式 | 记录 BaseModel、Field、model_dump 的作用 | 能解释“模型输出”和“程序校验”的分工 |
| Day 7 | 周复盘 | 汇总 5 条样例和标注结果 | 能说明哪些字段最容易被模型遗漏 |

## 第 3 周：最小工具调用 Agent

目标：理解模型只负责提出工具调用请求，Python 代码才是真正执行工具的一方。

| 天数 | 学习目标 | 实操任务 | 验收标准 |
| --- | --- | --- | --- |
| Day 1 | 读懂工具调用入口 | 阅读并运行 `03_tool_calling.py` | 能解释 `@tool`、`args_schema`、`.invoke()` |
| Day 2 | 设计工具边界 | 设计 `extract_components`、`infer_state`、`generate_test_points` | 每个工具职责互斥，不互相抢活 |
| Day 3 | 实现工具注册表 | 写一个 `TOOLS` 或 `TOOL_REGISTRY` | 新增工具只需要加注册项 |
| Day 4 | 增加入参校验 | 用 Pydantic 校验工具参数 | 错误参数会返回结构化错误 |
| Day 5 | 处理工具失败 | 手动构造 3 个失败案例 | 至少覆盖参数错误、空输入、未知工具 |
| Day 6 | 记录工具 trace | 每次工具调用记录 tool、args、result、error | 能复盘一次工具调用链路 |
| Day 7 | 周复盘 | 总结 Tool 和普通函数的区别 | 能说清工具为什么要为模型设计返回结构 |

## 第 4 周：Agent Loop 与终止条件

目标：把需求分析从一次调用改成可控的多步执行流程。

| 天数 | 学习目标 | 实操任务 | 验收标准 |
| --- | --- | --- | --- |
| Day 1 | 画出执行流程 | 将流程拆为页面类型、组件、状态、风险、测试点 5 步 | 每一步都有输入和输出 |
| Day 2 | 写最小循环 | 新建或完善 `09_requirement_agent_loop.py` | 循环最多 5 步，不会无限执行 |
| Day 3 | 增加状态对象 | 设计 `state` 保存每步产出 | 任一步失败后仍能看到已完成结果 |
| Day 4 | 增加停止条件 | 支持 `done`、`max_steps`、`failed` | 能解释每种终止原因 |
| Day 5 | 增加 retry / fallback | 对单步失败增加一次重试或默认兜底 | 失败时返回可读原因 |
| Day 6 | 跑 5 条固定任务 | 用同一套流程处理 5 条页面需求 | 每条都能产出结构化结果 |
| Day 7 | 周复盘 | 在 README 或笔记中写清流程图和终止条件 | 能说明为什么 Agent Loop 需要最大步数 |

## 第 5 周：Context Engineering

目标：控制什么信息进入模型，避免靠“堆 prompt”解决问题。

| 天数 | 学习目标 | 实操任务 | 验收标准 |
| --- | --- | --- | --- |
| Day 1 | 理解上下文分层 | 阅读主计划中的 Context Engineering 部分 | 能区分 system、task、schema、examples、trace |
| Day 2 | 新建上下文模板 | 创建 `context_template.md` | 模板固定包含 5 层上下文 |
| Day 3 | 固定输出 schema | 将输出字段写入模板 | 模型输出格式更稳定 |
| Day 4 | 增加优质样例 | 加 1-2 个页面需求示例 | 能说明样例放多了会污染上下文 |
| Day 5 | 接入失败摘要 | 将最近一次失败摘要放入 `recent_trace` | 不直接塞完整日志 |
| Day 6 | 对比实验 | 对同一需求分别运行有无 examples 的版本 | 记录字段完整度和稳定性差异 |
| Day 7 | 周复盘 | 总结 Context Engineering 与 Prompt Engineering 区别 | 能说清“上下文是模型决策前看到的一切” |

## 第 6 周：Trace、日志与可调试性

目标：让 Agent 的每一步都能复盘，而不是只看最终输出。

| 天数 | 学习目标 | 实操任务 | 验收标准 |
| --- | --- | --- | --- |
| Day 1 | 设计 trace 字段 | 定义 step、input、output、tool、error、duration | trace 字段能覆盖一次执行过程 |
| Day 2 | 写 JSONL trace | 每次运行追加一行或多行 trace | 能用文本查看历史执行记录 |
| Day 3 | 增加 trace_id | 每次任务生成唯一 `trace_id` | 前端或日志能关联同一次运行 |
| Day 4 | 记录工具耗时 | 给工具调用增加 duration | 能定位慢步骤 |
| Day 5 | 记录失败原因 | 增加 failure_type | 至少能区分工具错误、模型误判、上下文问题 |
| Day 6 | 跑 10 条 trace | 连续运行 10 条需求 | 能统计最常见 3 类失败 |
| Day 7 | 周复盘 | 写一页失败归因笔记 | 能说明 trace 对调试 Agent 的价值 |

## 第 7 周：Eval 与回归测试

目标：从“感觉变好”转成“可重复验证”。

| 天数 | 学习目标 | 实操任务 | 验收标准 |
| --- | --- | --- | --- |
| Day 1 | 读懂 eval 脚本 | 阅读并运行 `07_eval_regression.py` | 能解释 EvalCase 的输入和断言 |
| Day 2 | 设计 eval case 字段 | 定义 input、expected、forbidden、grader | 每条 case 都有明确成功标准 |
| Day 3 | 写正常任务 case | 写 10 条正常页面需求 | 覆盖常见前端页面 |
| Day 4 | 写边界 case | 写 5 条模糊、缺字段、冲突需求 | Agent 不应编造不存在的信息 |
| Day 5 | 写失败/安全 case | 写 5 条越权、危险、无效需求 | Agent 应拒绝或要求人工确认 |
| Day 6 | 跑评估并统计 | 输出通过率、失败类型、问题样例 | 能看到明确的失败分类 |
| Day 7 | 周复盘 | 把历史失败沉淀为 eval case | 能解释为什么 Agent 项目必须有回归评估 |

## 第 8 周：项目化整理

目标：把练习整理成能运行、能演示、能讲清楚的项目。

| 天数 | 学习目标 | 实操任务 | 验收标准 |
| --- | --- | --- | --- |
| Day 1 | 整理项目入口 | 明确主入口脚本和运行命令 | 新机器能按命令跑起来 |
| Day 2 | 补 README | 写项目目标、架构、安装、运行、测试、限制 | README 能让别人理解项目 |
| Day 3 | 整理 eval 报告 | 新建或补充 `eval_report.md` | 包含通过率和失败类型 |
| Day 4 | 整理演示脚本 | 新建或补充 `demo_script.md` | 能按脚本演示完整流程 |
| Day 5 | 补充架构表达 | 写清 agent loop、工具注册、context、trace、eval | 面试时能讲工程取舍 |
| Day 6 | 写项目复盘 | 总结做对的设计、失败点、下一步改进 | 不只写功能，还写为什么 |
| Day 7 | 写简历描述 | 产出一段 80-120 字项目描述 | 描述包含架构、场景、指标和评测 |

## 每日记录模板

每天结束时在 `docs/notes/learning_notes/daily/` 记录：

```text
# YYYY-MM-DD Day N：主题

## 今天目标

## 实际完成

## 卡住的问题

## 关键理解

## 代码或文件变更

## 明天继续
```

## 执行原则

- 每天只做当天目标，不顺手扩展无关功能。
- 每周至少有一个可运行产出。
- 每周至少有一次复盘，记录失败原因。
- 先用确定性代码解决控制流，再让模型处理开放判断。
- 不为了“像生产系统”而提前引入复杂队列、多 Agent 或微调。
