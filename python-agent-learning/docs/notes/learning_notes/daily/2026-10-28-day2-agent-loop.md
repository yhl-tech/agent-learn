# 2026-10-28 Day 2：最小 Agent Loop

## 今日主题

手写一个最小 Agent Loop，理解分步骤执行、共享状态、执行记录、最大步数和失败兜底。

## 核心结论

Agent Loop 不是一次性生成完整答案，而是把任务拆成多个步骤逐步推进。

一句话：

```text
Agent Loop = 按步骤执行 + 共享 state + 每步 trace + 明确停止条件 + 失败兜底
```

## 今天看的文件

- `09_requirement_agent_loop.py`

这个文件是教学版最小 Agent，不追求分析准确率，重点是看懂 Agent 执行骨架。

## 文件整体做什么

输入一段页面需求，然后按 5 步分析：

1. 识别页面目标。
2. 拆组件。
3. 推断状态。
4. 生成风险点。
5. 生成测试点。

每一步都会把结果写进同一个 `state`，并把执行过程写进 `trace`。

## `state` 是什么

`state` 是 Agent 的工作记忆。

这句：

```text
state = RequirementAgentState(requirement=requirement)
```

意思是创建一个 `RequirementAgentState` 对象，把原始需求放进去。

一开始只有：

- `requirement`

后续步骤会逐步写入：

- `page_goal`
- `core_components`
- `state_requirements`
- `risk_points`
- `test_points`
- `trace`
- `errors`

关键理解：

```text
不要让每一步传一堆零散变量，而是统一读写 state。
```

## `AgentStep` 和 `handler` 是什么

`AgentStep` 是步骤配置。

例子：

```text
AgentStep(
    name="identify_page_goal",
    think="先判断页面要帮助用户完成什么目标。",
    act="识别页面目标",
    handler=identify_page_goal,
)
```

这里的 `handler=identify_page_goal` 不是执行函数，而是把函数本身保存起来。

注意区别：

| 写法 | 含义 |
| --- | --- |
| `handler=identify_page_goal` | 保存函数，暂时不执行。 |
| `identify_page_goal(state)` | 立刻执行函数。 |

真正执行发生在：

```text
observation = step.handler(state)
```

如果当前 step 的 handler 是 `identify_page_goal`，这句等价于：

```text
observation = identify_page_goal(state)
```

这样做的好处：

- `run_agent_loop()` 不需要写死每个函数名。
- 当前 step 绑定哪个函数，就执行哪个函数。
- 后续增加步骤时，只需要往 `AGENT_STEPS` 里注册。

## `max_steps` 为什么存在

`max_steps` 是终止条件。

真实 Agent 可能因为模型反复规划、工具反复失败、停止条件写错而一直跑下去。

所以生产环境必须有硬上限，例如：

- 最大步骤数。
- 最大工具调用次数。
- 最大重试次数。
- 最大耗时。
- 最大 token 成本。

当前代码里：

```text
AGENT_STEPS[:max_steps]
```

表示最多只取前 `max_steps` 个步骤执行。

默认 `max_steps=5`，所以会完整跑 5 步。

如果设成 `max_steps=3`，只会跑：

1. 识别页面目标。
2. 拆组件。
3. 推断状态。

不会跑风险点和测试点。

这主要用于：

- 防止无限循环。
- 调试时只跑前几步。
- 给真实 Agent 加安全边界。

## 这个循环是不是异步的

不是。

当前代码是同步循环：

```text
for index, step in enumerate(AGENT_STEPS[:max_steps], start=1):
```

真正执行步骤的是：

```text
observation = step.handler(state)
```

这表示当前步骤执行完，才进入下一个步骤。

如果是异步，通常会看到：

- `async def`
- `await`
- `async for`

当前文件都没有，所以它是同步 Agent Loop。

## `trace` 是什么

`trace` 是执行记录。

每一步执行成功后，会创建一条 `AgentTraceStep`，记录：

- 第几步。
- 步骤名。
- 当前观察到什么。
- 为什么做这一步。
- 实际做了什么。
- 产出是什么。
- 有没有错误。

价值：

- 不只看最终答案。
- 可以定位是哪一步出错。
- 后续接入模型、工具、Eval 时方便调试。

## `try / except` 为什么存在

每一步都可能失败。

比如：

- 输入为空。
- 工具参数不对。
- 模型返回结构不合法。
- 外部接口超时。

所以单步执行放在 `try` 里：

```text
observation = step.handler(state)
```

如果失败，就进入 `except`：

- 记录错误原因。
- 写入失败 trace。
- 提前返回 `failed`。
- 不继续执行后续步骤。

原因是后续步骤通常依赖前置结果，前一步失败后继续跑容易产生更多无意义输出。

## `enumerate` 是什么

`enumerate()` 用于遍历列表时同时拿到序号和值。

例子：

```text
for index, step in enumerate(AGENT_STEPS[:max_steps], start=1):
```

含义：

- `index`：当前第几步，从 1 开始。
- `step`：当前要执行的步骤对象。

`start=1` 表示编号从 1 开始。

## `model_dump_json` 是什么

这句：

```text
print(result.model_dump_json(indent=2, ensure_ascii=False))
```

作用是把 Pydantic 对象转成格式化 JSON 并打印。

参数：

| 参数 | 含义 |
| --- | --- |
| `indent=2` | 缩进 2 个空格，输出更好读。 |
| `ensure_ascii=False` | 中文正常显示，不转成 `\uXXXX`。 |

它主要用于学习和调试，方便直接看到完整结果。

## 为什么当前用了关键词匹配

当前代码里有很多写法：

```text
if "搜索" in requirement:
    states.append("query_params")
```

这不是生产级做法。

它只是教学版假实现，用来让每一步都有可运行产出。

生产环境更常见的是：

- LLM 结构化抽取。
- Pydantic schema 校验。
- 规则和 LLM 混合。
- 检索业务知识库。
- 调用工具查组件、接口、权限配置、历史页面。

今天重点不是“关键词规则准确”，而是先理解 Agent Loop 骨架。

## 面试题补充

### 6. 为什么用 `Field(default_factory=list)`

代码：

```text
trace: List[AgentTraceStep] = Field(default_factory=list)
```

含义：

- `trace` 是一个列表字段。
- 每次创建新的 `RequirementAgentState` 对象时，都要生成一个新的空列表。

为什么不直接写：

```text
trace: List[AgentTraceStep] = []
```

原因是列表是可变对象。直接把空列表写成默认值，在一些 Python 场景里可能导致多个对象共享同一个列表，出现互相污染。

`default_factory=list` 的意思是：

```text
每次创建对象时，调用 list() 生成一个新的空列表。
```

这样每个 Agent run 都有自己的 `trace`，不会和其他 run 混在一起。

### 7. 生产环境会靠关键词匹配吗

一般不会只靠关键词匹配。

当前代码里：

```text
if "搜索" in requirement:
    states.append("query_params")
```

只是教学版写法，用来模拟每一步有确定产出。Day 2 的重点不是做准确的需求分析，而是理解 Agent Loop 的执行骨架。

生产环境更常见的做法：

- 用 LLM 做结构化抽取。
- 用 Pydantic schema 校验输出。
- 用规则处理确定性强的场景。
- 用知识库检索业务规范、组件规范、历史页面。
- 用工具查询接口、权限配置、组件库能力。

更合理的回答方式：

```text
关键词规则可以作为低风险辅助判断，但不能作为主要智能来源。
真实 Agent 应该把 LLM、结构化 schema、业务规则、工具调用和 Eval 组合起来。
```

### 8. Agent Loop 的工程安全边界

一个 Agent Loop 至少需要这些安全边界：

| 边界 | 作用 |
| --- | --- |
| `max_steps` | 限制最大执行步数，防止无限循环。 |
| `max_retries` | 限制单步最大重试次数，防止反复失败。 |
| `timeout` | 限制总耗时或单步耗时。 |
| `max_tool_calls` | 限制工具调用次数，控制成本和风险。 |
| token / cost budget | 限制模型调用成本。 |
| `try / except` | 单步失败时可读返回，不让程序直接崩。 |
| `trace` | 记录执行过程，方便调试和复盘。 |
| 输出 schema 校验 | 保证模型输出能被程序稳定消费。 |
| 人工确认 | 写文件、发消息、改数据库等高风险操作前必须确认。 |

面试表达：

```text
Agent 不能只追求能自动跑，还要能停、能查、能控风险。
所以我会给 Loop 加最大步数、超时、重试上限、工具调用上限、输出校验、trace 和高风险操作人工确认。
```

## 今天最重要的理解

不要把这个文件理解成一个强大的需求分析器。

它真正要表达的是：

```text
一个 Agent 应该如何拆步骤、传状态、记过程、控边界、处理失败。
```

## 明天衔接

Day 3 可以把当前步骤拆成工具：

- `extract_components(requirement)`
- `infer_state(requirement)`
- `generate_test_points(requirement)`

重点从“Loop 怎么跑”转向“工具边界怎么设计”。
