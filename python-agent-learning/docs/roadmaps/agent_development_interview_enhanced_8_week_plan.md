# Agent 开发线面试增强版 8 周计划

> 目标：在保留“页面需求分析 Agent”项目主线的基础上，显式补齐面试高频的 ReAct、RAG 深挖和 Multi-Agent。
>
> 适用目标：Agent 应用开发岗、LLM 应用工程岗、AI 应用工程实习/初级岗位。

前 15 天的逐日课程、代码练习和详细注释见：

- `agent_development_daily_course_and_code.md`

## 总体定位

原 8 周计划更偏“单 Agent 工程化落地”。这份增强版面向面试，把学习重心调整为：

- 第 1-3 周：打稳 LLM、结构化输出、Tool Calling。
- 第 4 周：补齐 ReAct 和 Agent Loop。
- 第 5 周：深挖 RAG，不只会写基础检索。
- 第 6 周：补 Context Engineering、Memory 和可恢复状态。
- 第 7 周：补 Trace、Eval、Safety。
- 第 8 周：补 Multi-Agent 入门，并完成项目表达。

## 按面试目标仍需补齐的知识点

增强版主线已经覆盖 ReAct、RAG 深挖和 Multi-Agent，但如果按 Agent 应用开发岗面试追问来看，还需要补下面这些“面试二层问题”。它们不一定都要写成项目功能，但至少要能讲清楚。

### 必须补齐

| 模块 | 缺口 | 为什么面试会问 |
| --- | --- | --- |
| LLM 基础参数 | temperature、top_p、top_k、max_tokens、streaming | 判断你是否真的理解模型调用，而不是只会调 SDK |
| Structured Output | JSON Mode、Function Calling、Pydantic 校验的区别 | 面试常追问“模型输出不合法怎么办” |
| Embedding 基础 | embedding 是什么、维度、归一化、cosine / dot / euclidean | RAG 深挖绕不开向量检索原理 |
| 向量库基础 | vector store、metadata、相似度阈值、索引更新 | 判断你是否懂 RAG 入库和查询链路 |
| LangGraph 基础 | State、Node、Edge、Conditional Edge、Checkpointer | Agent 开发岗常问有状态流程怎么做 |
| Human-in-the-loop | interrupt、审批、resume、人工确认 | 和权限、安全、可恢复执行强相关 |
| 幂等与重试 | timeout 后为什么不能直接重试、如何设计 idempotency key | 工具调用和真实业务系统的核心风险 |
| 并发与限流 | asyncio、RPM / TPM、排队、降级 | 面试系统设计题容易追问 |
| 成本与延迟 | token 成本、缓存、模型路由、P95 latency | 判断你是否有生产化意识 |
| 项目讲述 | 2 分钟项目介绍、失败案例、指标、取舍 | 决定项目能不能撑住面试追问 |

### 建议了解

| 模块 | 了解到什么程度 |
| --- | --- |
| MCP | 能说清 Host / Client / Server，以及 Tools / Resources / Prompts 的区别 |
| Agentic RAG | 知道 query rewrite、multi-query、HyDE、rerank、GraphRAG 分别解决什么问题 |
| Tool Retrieval | 知道工具很多时不能全塞进 prompt，需要先召回候选工具 |
| LLM-as-Judge | 知道它适合开放质量评分，但有位置偏差、一致性和校准问题 |
| 沙箱 | 知道执行代码、访问文件、浏览网页时要限制网络、路径、环境变量和系统调用 |
| 灰度发布 | 知道 prompt / workflow / model 变更也要回归、灰度和回滚 |

### 暂时不作为重点

| 模块 | 原因 |
| --- | --- |
| SFT / DPO / RLHF | 偏算法岗，不是 Agent 应用开发初中级主线 |
| PagedAttention / KV Cache / 推测解码 | 偏推理服务和模型部署，可作为加分项了解 |
| 复杂 GraphRAG 平台 | 成本高、实现重，先理解适用场景即可 |
| 大规模 Multi-Agent 平台 | 初级面试更看重边界判断，不看重堆复杂架构 |

## 第 1 周：LLM 调用与结构化输出

目标：能把自然语言需求转成稳定结构，理解模型输出为什么必须被程序校验。

每日目标：

| 天数 | 学习目标 | 实操任务 | 面试要能回答 |
| --- | --- | --- | --- |
| Day 1 | 区分 Chatbot / Workflow / Agent | 阅读主计划边界部分，补 `agent_boundary_notes.md` | 什么场景不该用 Agent |
| Day 2 | 跑通模型调用 | 运行 `01_cli_chat.py` | `system`、`human`、temperature 的作用 |
| Day 3 | 理解结构化输出 | 运行 `02_requirement_analyzer.py` | 为什么不能只让模型输出自然语言 |
| Day 4 | 扩展需求字段 | 增加页面类型、组件、状态、接口、风险、测试点 | Pydantic 在 Agent 里的作用 |
| Day 5 | 增加字段校验 | 给关键字段加类型和非空约束 | 模型输出不合法怎么办 |
| Day 6 | 准备 5 条页面需求样例 | 生成并人工检查结构化结果 | 怎么判断输出是否可用于前端开发 |
| Day 7 | 周复盘 | 写本周学习笔记 | 结构化输出和 Tool Calling 的关系 |

本周产出：

- 5 条页面需求样例。
- 5 份结构化输出。
- 一页“为什么 Agent 开发要先学结构化输出”的笔记。

## 第 2 周：Tool Calling 与工具设计

目标：理解模型只负责提出工具调用请求，确定性代码负责执行、校验和授权。

每日目标：

| 天数 | 学习目标 | 实操任务 | 面试要能回答 |
| --- | --- | --- | --- |
| Day 1 | 读懂工具调用入口 | 阅读并运行 `03_tool_calling.py` | Tool Calling 的完整链路 |
| Day 2 | 设计工具 schema | 设计 `extract_components` 入参和返回结构 | 好工具和坏工具的区别 |
| Day 3 | 建工具注册表 | 实现 `TOOL_REGISTRY` | 为什么用 dispatch 表优于 if-elif 长链 |
| Day 4 | 增加工具参数校验 | 用 Pydantic 校验工具输入 | 工具参数错误怎么处理 |
| Day 5 | 增加工具错误码 | 覆盖 `INVALID_ARGS`、`EMPTY_INPUT`、`UNKNOWN_TOOL` | 错误信息为什么要可恢复 |
| Day 6 | 记录工具调用 trace | 记录 tool、args、result、error | 如何排查工具选错 |
| Day 7 | 周复盘 | 总结工具设计原则 | 工具返回为什么不能太长 |

本周产出：

- 3 个本地工具。
- 一个工具注册表。
- 3 个工具调用失败案例。

## 第 3 周：基础 RAG 与资料引用

目标：跑通最小 RAG 链路，理解文档、chunk、检索、上下文和回答的关系。

每日目标：

| 天数 | 学习目标 | 实操任务 | 面试要能回答 |
| --- | --- | --- | --- |
| Day 1 | 理解 RAG 全链路 | 阅读并运行 `04_rag_qa.py` | RAG 解决什么问题 |
| Day 2 | 理解 chunk | 调整切分大小和 overlap | chunk 太大或太小有什么问题 |
| Day 3 | 理解 retrieval | 调整 `top_k` 为 1、3、5 | top_k 如何影响召回和噪声 |
| Day 4 | 输出引用来源 | 回答中带 source | 为什么 RAG 要给出处 |
| Day 5 | 增加无结果处理 | 检索为空时回答“不确定” | 如何减少幻觉引用 |
| Day 6 | 准备 10 条 RAG 问题 | 覆盖能命中和不能命中的问题 | 如何评估一个 RAG 是否有效 |
| Day 7 | 周复盘 | 总结 RAG 基础链路 | RAG 和普通上下文拼接的区别 |

本周产出：

- 一个带来源的基础 RAG Demo。
- 10 条基础 RAG 测试问题。

## 第 4 周：ReAct 与 Agent Loop

目标：显式掌握 ReAct 范式，把“多步执行”从普通 workflow 升级为可解释的 Agent Loop。

核心概念：

```text
Thought -> Action -> Observation -> Thought -> ...
```

注意：真实工程里不一定暴露完整思维链，但要保留可观测的计划摘要、工具动作和观察结果。

每日目标：

| 天数 | 学习目标 | 实操任务 | 面试要能回答 |
| --- | --- | --- | --- |
| Day 1 | 理解 ReAct | 阅读 ReAct 资料，写概念笔记 | ReAct 和普通 Tool Calling 的区别 |
| Day 2 | 改造 Agent Loop | 在 `09_requirement_agent_loop.py` 中加入 plan/action/observation 字段 | Agent Loop 的核心步骤 |
| Day 3 | 增加最大步数 | 加 `max_steps` | 如何避免无限循环 |
| Day 4 | 增加停止条件 | 支持 `done`、`failed`、`need_more_info` | Agent 什么时候该停 |
| Day 5 | 增加工具观察结果 | 每次工具调用后写入 observation | Observation 如何影响下一步 |
| Day 6 | 跑 5 条复杂需求 | 用 ReAct loop 处理多步骤页面需求 | ReAct 容易失败在哪里 |
| Day 7 | 周复盘 | 写 ReAct 优缺点笔记 | ReAct 为什么不能只靠 prompt |

本周产出：

- 一个最小 ReAct 风格 Agent Loop。
- 一页 ReAct 面试笔记。

面试必答点：

- ReAct 的价值是把推理和行动交替起来。
- ReAct 的风险是循环、工具误用、上下文膨胀。
- 工程上必须加 `max_steps`、stop condition、trace、错误处理。

## 第 5 周：RAG 深挖与面试高频

目标：从“会写 RAG Demo”升级到“能解释 RAG 为什么效果不好，以及怎么优化”。

每日目标：

| 天数 | 学习目标 | 实操任务 | 面试要能回答 |
| --- | --- | --- | --- |
| Day 1 | 召回率 vs 准确率 | 用 5 条问题分析漏召回和误召回 | 召回率低是什么意思 |
| Day 2 | chunk 策略优化 | 对比固定长度、标题切分、段落切分 | chunk 如何影响 RAG |
| Day 3 | metadata filter | 给文档加 `source`、`page_type`、`version` | metadata 在 RAG 里做什么 |
| Day 4 | hybrid search | 对比关键词检索和向量检索思路 | 为什么关键词和向量互补 |
| Day 5 | rerank | 理解 rerank 位置和作用，可先写伪实现 | rerank 解决什么问题 |
| Day 6 | query rewrite | 对模糊问题做查询改写 | 用户问题和文档表达不一致怎么办 |
| Day 7 | 周复盘 | 形成 RAG 优化清单 | 如何系统排查 RAG 回答差 |

本周产出：

- 一份 RAG 失败归因表。
- 一份 RAG 优化清单。
- 至少 20 条 RAG eval case。

面试必答点：

- 召回率解决“漏”，准确率解决“杂”。
- `top_k` 太小会漏，太大会引入噪声。
- metadata filter 可用于知识库、权限、时间、文档类型过滤。
- rerank 是在召回后重新排序，提升上下文质量。
- hybrid search 用关键词补向量检索的不足。

## 第 6 周：Context Engineering、Memory 与状态恢复

目标：理解 Agent 的效果不只来自 prompt，而来自上下文组织、记忆分层和状态管理。

每日目标：

| 天数 | 学习目标 | 实操任务 | 面试要能回答 |
| --- | --- | --- | --- |
| Day 1 | 上下文分层 | 创建或完善 `context_template.md` | Context Engineering 和 Prompt Engineering 区别 |
| Day 2 | context builder | 写 `build_context(...)` | 为什么不能把所有历史都塞给模型 |
| Day 3 | recent trace 摘要 | 只把失败摘要放入上下文 | 如何避免上下文污染 |
| Day 4 | Memory 分层 | 区分 working / episodic / semantic memory | Memory 和 RAG 的区别 |
| Day 5 | JSONL 会话记录 | 保存每次任务状态 | 为什么长任务需要持久状态 |
| Day 6 | resume 设计 | 模拟中断后从状态继续 | pause / resume 怎么设计 |
| Day 7 | 周复盘 | 总结上下文、记忆、状态三者关系 | Agent Harness 为什么重要 |

本周产出：

- 一份 context template。
- 一个最小 context builder。
- 一个 JSONL 状态记录样例。

## 第 7 周：Trace、Eval 与 Safety

目标：让 Agent 从“能跑”变成“能调试、能回归、能控制风险”。

每日目标：

| 天数 | 学习目标 | 实操任务 | 面试要能回答 |
| --- | --- | --- | --- |
| Day 1 | trace 结构 | 记录 trace_id、step、tool、error、duration | Trace 对 Agent 有什么用 |
| Day 2 | EvalCase 设计 | 定义 input、expected、forbidden、grader | Agent eval 和普通单测区别 |
| Day 3 | 正常任务 eval | 写 10 条正常 case | 如何证明能力没有退化 |
| Day 4 | 边界任务 eval | 写 5 条边界 case | 如何评估不完整输入 |
| Day 5 | 安全任务 eval | 写 5 条 prompt injection / 危险动作 case | Agent 安全为什么不能只靠 prompt |
| Day 6 | 权限分级 | 读自动、写 dry-run、人审确认 | human-in-the-loop 怎么设计 |
| Day 7 | 周复盘 | 输出 eval_report.md | 如何用失败归因指导下一轮优化 |

本周产出：

- 20 条 eval case。
- 一份 eval_report.md。
- 一套最小权限策略。

面试必答点：

- Agent eval 要看 trajectory，也要看 outcome。
- 外部文档、网页、工具返回都是不可信数据。
- 高风险操作必须权限分级和人工确认。
- trace 是失败归因和回归评估的基础。

## 第 8 周：Multi-Agent 入门与项目表达

目标：能讲清 Multi-Agent 的适用边界，不盲目堆角色；同时完成项目面试表达。

每日目标：

| 天数 | 学习目标 | 实操任务 | 面试要能回答 |
| --- | --- | --- | --- |
| Day 1 | 理解 Multi-Agent 边界 | 写 Multi-Agent 适用和不适用场景 | Multi-Agent 为什么不一定更强 |
| Day 2 | 角色职责划分 | 设计 planner / executor / reviewer | 每个 Agent 的输入输出是什么 |
| Day 3 | 实现最小三角色流程 | 可用普通函数模拟，不急着上框架 | supervisor 如何协调 |
| Day 4 | 增加 reviewer | reviewer 检查输出字段完整性 | reviewer 和普通校验有什么区别 |
| Day 5 | 分析 Multi-Agent 风险 | 记录上下文膨胀、循环争论、责任不清 | Multi-Agent 常见失败模式 |
| Day 6 | 整理项目材料 | 补 README、demo_script、eval_report | 如何把项目讲成工程经验 |
| Day 7 | 模拟面试讲述 | 准备 2 分钟项目介绍和 5 个追问答案 | 如何回答“为什么不用普通 workflow” |

本周产出：

- 一个最小 Multi-Agent 模拟流程。
- 一份 Multi-Agent 面试笔记。
- 一段项目简历描述。

面试必答点：

- Multi-Agent 适合子任务边界清晰、可独立完成、最后汇总的场景。
- 如果子任务频繁交换中间状态，单 Agent 或 workflow 往往更稳。
- 常见角色：planner、executor、reviewer、critic、router。
- 风险：协调成本、上下文膨胀、循环争论、责任不清。

## 最终你应该能讲清楚的 20 个问题

1. Agent 和 Workflow 的区别是什么？
2. Tool Calling 的完整执行链路是什么？
3. 为什么工具入参要用 schema？
4. ReAct 的 Thought / Action / Observation 分别是什么？
5. Agent Loop 如何避免无限循环？
6. RAG 的 chunk、retrieve、rerank 分别解决什么问题？
7. 召回率低和准确率低有什么区别？
8. metadata filter 在 RAG 里有什么用？
9. Context Engineering 和 Prompt Engineering 有什么区别？
10. Trace 如何帮助定位 Agent 失败？
11. Agent Eval 和普通单元测试有什么区别？
12. Multi-Agent 什么时候适合，什么时候不适合？
13. temperature、top_p、top_k 分别影响什么？
14. JSON Mode、Structured Output、Pydantic 校验有什么区别？
15. Embedding、Vector Store、Retriever 分别做什么？
16. cosine、dot product、euclidean distance 有什么差别？
17. LangGraph 的 State、Checkpointer、interrupt 分别解决什么问题？
18. 工具调用超时后为什么不能无脑重试？
19. 生产 Agent 如何控制成本、延迟和限流？
20. 你的项目中最失败的一次 badcase 是什么，后来怎么回流到 eval？

## 这份增强版不做什么

- 不做模型微调。
- 不做 Agentic RL。
- 不做复杂多 Agent 平台。
- 不做大而全框架横向对比。
- 不追求一次性覆盖所有论文。

核心原则：先把单 Agent、ReAct、RAG、Eval、Safety 讲深，再用 Multi-Agent 做面试补强。
