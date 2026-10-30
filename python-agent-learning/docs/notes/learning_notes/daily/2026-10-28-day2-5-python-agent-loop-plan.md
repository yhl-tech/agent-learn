# 2026-10-28 Day 2.5：Python 基础补强 + Agent Loop 复盘计划

## 为什么加 Day 2.5

当前学习同时卡在两条线：

- Python 基础语法还不熟。
- Agent 工程概念刚开始建立。

如果直接进入 Day 3 工具调用，会出现“代码越来越多，但底层执行链路没吃透”的问题。

所以 Day 2.5 的目标不是推进新功能，而是把 `09_requirement_agent_loop.py` 真正讲清楚。

## 今日目标

能不看答案，口述清楚这条执行链路：

```text
main()
  -> run_agent_loop()
  -> 创建 state
  -> 遍历 AGENT_STEPS
  -> step.handler(state)
  -> 写入 state
  -> 写入 trace
  -> 返回 AgentRunResult
  -> model_dump_json 打印结果
```

## 学习范围

只围绕这一个文件：

- `09_requirement_agent_loop.py`

暂时不引入：

- LangGraph
- 真实 LLM
- LangChain Tool Calling
- 新框架
- 复杂新功能

## Python 基础补强

### 1. `class` 和对象

重点理解：

- `RequirementAgentState` 是一个类。
- `RequirementAgentState(requirement=requirement)` 是创建对象。
- `state.page_goal` 是读取或修改对象字段。

#### 1.1 `class` 是什么

`class` 可以理解成“对象模板”。

它定义一类对象应该有哪些字段、字段是什么类型、默认值是什么。

在当前文件中：

```text
class RequirementAgentState(BaseModel):
    requirement: str
    page_goal: str = ""
    core_components: List[str] = Field(default_factory=list)
    trace: List[AgentTraceStep] = Field(default_factory=list)
```

意思是定义一种叫 `RequirementAgentState` 的数据结构。

它规定这个对象里会有：

| 字段 | 含义 |
| --- | --- |
| `requirement` | 原始页面需求。 |
| `page_goal` | 页面目标。 |
| `core_components` | 组件拆分结果。 |
| `trace` | 执行记录。 |

#### 1.2 类和对象的区别

类是模板，对象是根据模板创建出来的具体数据。

| 概念 | 例子 | 含义 |
| --- | --- | --- |
| 类 | `RequirementAgentState` | 一种状态结构的定义。 |
| 对象 | `state` | 某次运行中真实保存数据的状态对象。 |

这句：

```text
state = RequirementAgentState(requirement=requirement)
```

可以理解成：

```text
按照 RequirementAgentState 这个模板，创建一个具体 state 对象。
```

#### 1.3 为什么创建时只传 `requirement`

因为 `requirement` 没有默认值，是必填字段。

而其他字段有默认值：

| 字段 | 默认值 |
| --- | --- |
| `page_goal` | `""` |
| `core_components` | 空列表 |
| `state_requirements` | 空列表 |
| `risk_points` | 空列表 |
| `test_points` | 空列表 |
| `trace` | 空列表 |
| `errors` | 空列表 |

所以创建对象时只需要传：

```text
RequirementAgentState(requirement=requirement)
```

后续步骤再逐步补充其他字段。

#### 1.4 字段怎么读写

创建对象后，用点号访问字段。

读取字段：

```text
state.requirement
state.page_goal
state.core_components
```

修改字段：

```text
state.page_goal = "审批工作台"
state.core_components = ["PageLayout", "DataTable"]
```

在 Agent Loop 里，每一步本质上就是读写 `state`：

| 步骤 | 写入字段 |
| --- | --- |
| `identify_page_goal(state)` | `state.page_goal` |
| `extract_components(state)` | `state.core_components` |
| `infer_state_requirements(state)` | `state.state_requirements` |
| `generate_risk_points(state)` | `state.risk_points` |
| `generate_test_points(state)` | `state.test_points` |

#### 1.5 `BaseModel` 是什么

`RequirementAgentState` 继承了 Pydantic 的 `BaseModel`：

```text
class RequirementAgentState(BaseModel):
```

这表示它不是普通 Python 类，而是 Pydantic 数据模型。

好处：

- 可以定义字段类型。
- 可以设置默认值。
- 可以做基础校验。
- 可以用 `model_dump_json()` 转成 JSON。

比如 `AgentRunResult` 也是 `BaseModel`，所以最后可以：

```text
result.model_dump_json(indent=2, ensure_ascii=False)
```

把结果打印成结构化 JSON。

#### 1.6 和 TypeScript 的类比

可以粗略类比为：

| Python | TypeScript 理解 |
| --- | --- |
| `class RequirementAgentState(BaseModel):` | 定义一个状态类型 / class。 |
| `state = RequirementAgentState(requirement=requirement)` | `const state = new RequirementAgentState({ requirement })` |
| `state.page_goal = "审批工作台"` | `state.pageGoal = "审批工作台"` |
| `state.core_components` | `state.coreComponents` |

区别：

- Python 字段常用 snake_case，例如 `page_goal`。
- TypeScript 字段常用 camelCase，例如 `pageGoal`。
- Pydantic 会在运行时做部分数据校验，普通 TypeScript 类型主要是编译期检查。

验收：

```text
能解释 state 为什么一开始只有 requirement，后面会逐步多出 page_goal、core_components、trace。
```

### 2. 函数作为变量

重点理解：

- `handler=identify_page_goal` 是保存函数，不是执行函数。
- `step.handler(state)` 才是真正执行。

验收：

```text
能说出 handler=identify_page_goal 和 identify_page_goal(state) 的区别。
```

### 3. `for` 和 `enumerate`

重点理解：

- `for index, step in enumerate(..., start=1)` 会同时拿到序号和当前步骤。
- `index` 用来记录第几步。
- `step` 是当前要执行的 `AgentStep`。

验收：

```text
能解释 index 和 step 分别是什么。
```

### 4. `try / except`

重点理解：

- `try` 里执行单个步骤。
- `except` 里记录错误并提前返回。
- 某一步失败后，不继续执行后续步骤。

验收：

```text
能解释空需求为什么返回 failed，而不是程序直接崩溃。
```

### 5. `Field(default_factory=list)`

重点理解：

- 每次创建对象时生成新的空列表。
- 避免多个对象共享同一个列表。

验收：

```text
能解释为什么 trace/errors/core_components 这类字段不用 [] 直接当默认值。
```

## Agent 概念复盘

### 1. `state`

`state` 是 Agent 的工作记忆。

它保存：

- 原始需求。
- 中间分析结果。
- 执行记录。
- 错误信息。

### 2. `step`

`step` 是一个执行步骤。

每个 step 包含：

- `name`
- `think`
- `act`
- `handler`

### 3. `handler`

`handler` 是这个步骤真正执行的函数。

循环里统一调用：

```text
step.handler(state)
```

当前 step 绑定哪个函数，就执行哪个函数。

### 4. `trace`

`trace` 是执行记录。

它不是最终答案，而是记录每一步：

- 看到了什么。
- 为什么执行。
- 做了什么。
- 得到了什么。
- 有没有失败。

### 5. `max_steps`

`max_steps` 是最大步骤数限制。

它的作用：

- 防止无限循环。
- 控制成本和耗时。
- 调试时只跑前几步。

### 6. 三种结果状态

| 状态 | 含义 |
| --- | --- |
| `completed` | 5 个步骤全部跑完。 |
| `stopped` | 没失败，但因为 `max_steps` 提前停止。 |
| `failed` | 某一步报错，提前失败。 |

## 实操任务

### 任务 1：正常执行

命令：

```bash
cd /Users/bytedance/Desktop/code/agent/python-agent-learning
.venv/bin/python 09_requirement_agent_loop.py
```

观察：

- 每条 case 是否都是 `completed`。
- `steps_used` 是否是 `5`。
- `trace` 是否有 5 条。

### 任务 2：最大步数提前停止

临时调用：

```text
run_agent_loop("做一个订单列表页，支持搜索和分页", max_steps=2)
```

观察：

- `status` 应该是 `stopped`。
- `steps_used` 应该是 `2`。
- 不会生成风险点和测试点。

### 任务 3：失败路径

临时调用：

```text
run_agent_loop("")
```

观察：

- `status` 应该是 `failed`。
- `reason` 里应该包含 `需求为空`。
- `errors` 里应该有失败原因。

## 自测问题

1. `state` 为什么是 Agent 的工作记忆？
2. `handler=identify_page_goal` 为什么不是执行函数？
3. `step.handler(state)` 为什么能执行不同步骤？
4. `trace` 和最终答案有什么区别？
5. `max_steps=2` 为什么返回 `stopped`？
6. 空需求为什么返回 `failed`？
7. 关键词匹配为什么只是教学版？
8. 生产环境会怎么替换关键词匹配？

## 通过标准

今天不以“写了多少代码”为标准。

通过标准是：

```text
能从 main() 开始，完整口述 09_requirement_agent_loop.py 的执行链路。
```

如果能讲清楚：

- 输入怎么进来。
- state 怎么创建。
- step 怎么执行。
- handler 怎么调用。
- trace 怎么记录。
- result 怎么返回。

就可以进入 Day 3。

## 后续衔接

Day 3 再进入工具设计。

重点从：

```text
Loop 怎么跑
```

切换到：

```text
工具边界怎么设计
```

预计要设计的工具：

- `extract_components(requirement)`
- `infer_state(requirement)`
- `generate_test_points(requirement)`
