# Agent 开发线每日课程与代码详解

> 配套路线：
>
> - `agent_development_interview_enhanced_8_week_plan.md`
> - `agent_development_learning_plan.md`
>
> 当前版本先覆盖前 15 天：第 1 周 7 天、第 2 周 7 天、第 3 周第 1 天。
>
> 目标不是每天读完很多资料，而是每天完成一个“概念理解 -> 代码练习 -> 面试表达 -> 验收”的小闭环。

## 使用方式

### 每天建议用时

每天按下面的顺序学习，建议 90-120 分钟：

1. 课程阅读：20-30 分钟。
2. 运行现有脚本：10-20 分钟。
3. 完成代码练习：30-50 分钟。
4. 面试口述：10 分钟。
5. 写学习笔记：10 分钟。

如果当天遇到模型 Key、网络或依赖问题，不要停在环境排查上。优先使用脚本已有的本地逻辑、`--no-model` 参数或固定样例完成控制流练习。

### 代码注释要求

本文件中的示例代码故意写了较详细的中文注释。实际写代码时，注释重点解释：

- 这段代码在 Agent 链路中的职责。
- 为什么需要这一步。
- 输入和输出分别是什么。
- 出错时应该如何处理。

不要给每一行都写“给变量赋值”这类无信息注释。代码本身已经清楚的语法，重点理解其业务作用。

### 现有脚本索引

| 学习主题 | 主要脚本 |
| --- | --- |
| 最小模型调用 | `01_cli_chat.py` |
| Pydantic 结构化输出 | `02_requirement_analyzer.py` |
| Tool Calling 基础 | `03_tool_calling.py` |
| RAG 基础 | `04_rag_qa.py` |
| LangGraph 状态图 | `05_langgraph_bug_agent.py` |
| Agent API | `06_agent_api.py` |
| Eval 回归 | `07_eval_regression.py` |
| Human-in-the-loop | `08_human_approval_file_writer.py` |
| 手写 Agent Loop | `09_requirement_agent_loop.py` |
| 工具化需求 Agent | `10_requirement_tool_agent.py` |

### 前 15 天 Demo 对照

| 天数 | 关联 Demo | 这个 Demo 支撑的当天知识 |
| --- | --- | --- |
| Day 1 | [`demos/day01_task_boundary_demo.py`](../../demos/day01_task_boundary_demo.py) | Chatbot、Workflow、Agent 的边界 |
| Day 2 | [`01_cli_chat.py`](../../01_cli_chat.py) | `system`、`human`、`invoke`、`response.content` |
| Day 3 | [`02_requirement_analyzer.py`](../../02_requirement_analyzer.py) | `BaseModel`、`Field`、结构化输出 |
| Day 4 | [`demos/day04_schema_design_demo.py`](../../demos/day04_schema_design_demo.py) | 字段职责和可消费的输出结构 |
| Day 5 | [`demos/day05_output_validation_demo.py`](../../demos/day05_output_validation_demo.py) | 结构校验和业务校验的区别 |
| Day 6 | [`demos/day06_requirement_cases_demo.py`](../../demos/day06_requirement_cases_demo.py) | 正常、边界、权限、异常样例 |
| Day 7 | [`demos/day07_week_review_demo.py`](../../demos/day07_week_review_demo.py) | 覆盖缺口统计和周复盘 |
| Day 8 | [`demos/day04_schema_design_demo.py`](../../demos/day04_schema_design_demo.py) | 字段职责与下游用途 |
| Day 9 | [`demos/day09_nested_model_demo.py`](../../demos/day09_nested_model_demo.py) | 嵌套模型和 `model_validate` |
| Day 10 | [`demos/day06_requirement_cases_demo.py`](../../demos/day06_requirement_cases_demo.py) | 需求样例和可重复检查 |
| Day 11 | [`demos/day11_quality_score_demo.py`](../../demos/day11_quality_score_demo.py) | 完整性、相关性、可执行性、风险意识评分 |
| Day 12 | [`demos/day12_cross_field_validation_demo.py`](../../demos/day12_cross_field_validation_demo.py) | 跨字段业务规则 |
| Day 13 | [`demos/day13_layered_validation_demo.py`](../../demos/day13_layered_validation_demo.py) | 外部数据、schema、业务校验分层 |
| Day 14 | [`demos/day13_layered_validation_demo.py`](../../demos/day13_layered_validation_demo.py) | 结构化输出面试复盘和错误分层 |
| Day 15 | [`03_tool_calling.py`](../../03_tool_calling.py)、[`10_requirement_tool_agent.py`](../../10_requirement_tool_agent.py)、[`demos/day15_tool_dispatch_demo.py`](../../demos/day15_tool_dispatch_demo.py) | Tool Calling 请求、工具执行、注册表和错误处理 |

### 每日笔记位置

每日复盘继续写到：

```text
python-agent-learning/docs/notes/learning_notes/daily/
```

推荐文件名：

```text
YYYY-MM-DD-dayN-主题.md
```

## 第 1 周：LLM 调用与结构化输出基础

第 1 周的面试目标：

- 能说清 Chatbot、Workflow、Agent 的区别。
- 能解释一次模型调用的消息、参数和返回值。
- 能说明为什么业务代码不能直接信任模型输出。
- 能用 Pydantic 定义一个可校验的输出结构。

### Day 1：建立 Chatbot、Workflow、Agent 边界

#### 当日课程

关联 Demo：[`demos/day01_task_boundary_demo.py`](../../demos/day01_task_boundary_demo.py)

运行：

```bash
.venv/bin/python demos/day01_task_boundary_demo.py
```

观察输出中的四个任务分别被归类为什么，并说明最后一个模糊任务为什么只能得到保守判断。

先理解三个概念：

| 概念 | 核心特征 | 页面需求分析中的例子 |
| --- | --- | --- |
| Chatbot | 用户问一次，模型答一次 | 解释“分页组件怎么做” |
| Workflow | 步骤和分支由程序提前规定 | 固定执行“读取需求 -> 调模型 -> 输出 JSON” |
| Agent | 模型根据当前状态决定下一步动作 | 先判断信息是否完整，再决定追问、调用工具或生成结果 |

重点不是把 Agent 说得复杂，而是判断“下一步是否需要动态决定”：

- 如果步骤固定，优先使用 Workflow。
- 如果只是自然语言问答，Chatbot 就够了。
- 如果需要根据观察结果选择工具、重试或追问，才有 Agent 的必要。

阅读：

- `01_cli_chat.py` 文件顶部的技术导读。
- `02_requirement_analyzer.py` 文件顶部的结构化输出说明。
- 主路线中的“什么时候需要 Agent，什么时候普通 Workflow 就够了”。

#### 代码练习：用确定性规则区分任务类型

这段代码不调用模型，目的是先训练边界判断。可以临时放在学习笔记中运行。

```python
from typing import Literal


# Literal 用来限制函数只能返回下面三个固定值。
# 在 Agent 代码里，这类固定状态可以减少“返回任意字符串”带来的分支错误。
TaskType = Literal["chatbot", "workflow", "agent"]


def classify_task(task: str) -> TaskType:
    """根据任务特征做一个粗粒度判断。

    这不是生产级分类器，只用于训练判断习惯：
    先问自己“流程是否固定”，再决定是否需要 Agent。
    """
    normalized_task = task.strip()

    # 没有复杂流程、只是解释或总结时，普通 Chatbot 就够了。
    if any(keyword in normalized_task for keyword in ("解释", "总结", "翻译")):
        return "chatbot"

    # 如果需求明确列出了固定步骤，程序可以直接按顺序执行。
    if "固定步骤" in normalized_task or "依次执行" in normalized_task:
        return "workflow"

    # 需要根据工具返回结果决定下一步，或者需要动态追问时，
    # 才更接近 Agent。
    if any(keyword in normalized_task for keyword in ("选择工具", "根据结果", "动态追问")):
        return "agent"

    # 信息不足时，保守地按 Workflow 处理。
    # 面试中要说明：这是示例兜底，不是说所有未知需求都必须用 Workflow。
    return "workflow"


examples = [
    "解释 React useMemo 的适用场景",
    "依次执行读取需求、生成 JSON、保存结果三个固定步骤",
    "根据检索结果决定继续搜索还是直接回答",
]

for example in examples:
    print(classify_task(example), example)
```

#### 面试自测

用自己的话回答：

1. 为什么不能看到“AI”就使用 Agent？
2. 页面需求分析项目中，哪些步骤可以固定成 Workflow？
3. 哪个环节需要 Agent 的动态决策？

参考回答方向：

> 固定流程优先用 Workflow，因为更稳定、便于测试；只有当系统需要根据当前观察选择工具、追问用户或决定是否重试时，才引入 Agent。

#### 当日验收

- 能分别举出一个 Chatbot、Workflow、Agent 例子。
- 能说明“页面需求分析”为什么可以先用 Workflow，再逐步加入 Agent Loop。
- 完成一篇笔记，至少包含一个“不应该用 Agent”的场景。

### Day 2：跑通一次最小 LLM 调用

#### 当日课程

关联 Demo：[`01_cli_chat.py`](../../01_cli_chat.py)

运行：

```bash
.venv/bin/python 01_cli_chat.py
```

如果暂时没有模型 Key，先阅读文件顶部导读和 `model.invoke(...)` 调用结构；不要为了运行命令跳过消息和参数的理解。

阅读并运行：

```bash
cd /Users/bytedance/Desktop/code/agent/python-agent-learning
.venv/bin/python 01_cli_chat.py
```

理解一次调用中的四个部分：

1. `load_dotenv()`：读取环境变量，不把密钥写进代码。
2. `ChatOpenAI(...)`：创建统一的聊天模型客户端。
3. `system`：定义角色、边界和输出规则。
4. `human`：传入本次具体任务。
5. `response.content`：读取模型生成的文本。

重点理解：`invoke()` 只是一次模型调用，它本身还不是 Agent。没有状态、工具和循环时，它更接近一个 LLM 能力函数。

#### 代码练习：把模型调用封装成可复用函数

在学习笔记或临时文件中练习下面的最小封装。理解后再对照 `01_cli_chat.py`。

```python
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def ask_model(question: str) -> str:
    """调用模型回答一个问题，并返回纯文本。

    这个函数只负责模型调用，不负责：
    - 保存对话历史；
    - 调用外部工具；
    - 校验复杂业务结果；
    - 判断任务是否完成。

    把职责限制在“输入问题 -> 返回文本”，
    有助于后续把它替换成结构化输出或 Agent 节点。
    """
    # 读取 .env 中的 API Key、Base URL 等配置。
    # 密钥不应该直接硬编码在 Python 文件里。
    load_dotenv()

    # 从环境变量读取模型名；没有配置时使用学习脚本的默认模型。
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # temperature 控制输出的随机程度。
    # 学习结构化任务时先使用 0 或较低值，便于比较不同实验结果。
    model = ChatOpenAI(
        model=model_name,
        temperature=0,
    )

    # system 规定模型的角色和总体行为，
    # human 传入本次具体问题。
    response = model.invoke(
        [
            ("system", "你是严格、简洁的前端技术导师。"),
            ("human", question),
        ]
    )

    # response.content 是模型生成的文本。
    # 这里转成 str，保证调用方拿到统一的字符串类型。
    return str(response.content)


print(ask_model("用一句话解释什么是前端组件状态。"))
```

#### 实验任务

分别把 `temperature` 设置成 `0`、`0.2`、`0.8`，对同一个问题运行 3 次，记录：

- 结果是否出现不同表达。
- 是否出现额外发挥。
- 哪个值更适合后续结构化需求分析。

#### 面试自测

1. `system` 和 `human` 消息分别负责什么？
2. `temperature` 越低是不是绝对确定？
3. 为什么生产代码不能只打印模型结果，不记录请求和错误？

回答重点：

- `temperature` 影响采样倾向，但不应简单等同于绝对确定性。
- 生产环境还要考虑模型服务、网络、限流、超时、成本和 trace。

#### 当日验收

- 能运行 `01_cli_chat.py`。
- 能解释 `model.invoke()` 返回的对象和 `response.content` 的区别。
- 能说出一次模型调用失败时至少要记录哪些信息。

### Day 3：理解 Pydantic 结构化输出

#### 当日课程

关联 Demo：[`02_requirement_analyzer.py`](../../02_requirement_analyzer.py)

运行：

```bash
.venv/bin/python 02_requirement_analyzer.py
```

重点观察 `result` 已经是 `RequirementAnalysis` 对象，而不是普通字符串。

阅读并运行：

```bash
.venv/bin/python 02_requirement_analyzer.py
```

重点理解：

- `BaseModel`：定义数据结构和校验规则。
- `Field(description=...)`：补充字段语义，帮助模型理解字段。
- `with_structured_output(...)`：让模型按指定 schema 返回。
- `model_dump_json(...)`：把 Pydantic 对象转成 JSON。

结构化输出解决的是“程序如何稳定消费模型结果”，不是单纯让回答更漂亮。

#### 代码练习：定义一个最小需求分析 schema

```python
from typing import List

from pydantic import BaseModel, Field


class MiniRequirementAnalysis(BaseModel):
    # page_goal 是单个字符串，因为页面目标通常是一句话概括。
    page_goal: str = Field(description="页面要帮助用户完成的核心目标")

    # 组件可能有多个，所以使用 List[str]。
    # 类型标注同时服务于 IDE、Pydantic 校验和模型 schema 生成。
    components: List[str] = Field(
        description="页面需要拆分的前端组件名称列表"
    )

    # 风险点也可能有多个，要求模型用列表返回，
    # 便于后续前端或测试流程逐条展示。
    risks: List[str] = Field(
        description="实现页面时需要重点关注的风险列表"
    )


def validate_result(result: MiniRequirementAnalysis) -> None:
    """演示程序如何继续消费结构化结果。"""
    # 这里的判断发生在模型返回之后。
    # 即使模型成功返回了合法 JSON，也可以继续做业务层校验。
    if not result.page_goal.strip():
        raise ValueError("页面目标不能为空")

    if not result.components:
        raise ValueError("至少需要识别一个页面组件")


# 下面这段模拟模型已经返回的结构。
# 实际使用时，structured_model.invoke(...) 会返回同类型对象。
result = MiniRequirementAnalysis(
    page_goal="让用户检索并处理订单",
    components=["SearchBar", "DataTable", "Pagination"],
    risks=["分页与查询条件可能不同步"],
)

validate_result(result)
print(result.model_dump_json(indent=2))
```

#### 面试自测

1. 为什么 `BaseModel` 比直接让模型输出字符串更适合业务？
2. `Field(description=...)` 只是注释吗？
3. Pydantic 校验通过后，是否代表业务语义一定正确？

回答重点：

- schema 能约束字段类型和结构，但不能自动保证业务判断正确。
- 仍然需要业务校验、Eval 和人工抽样。

#### 当日验收

- 能指出 `02_requirement_analyzer.py` 中 schema 的每个字段用途。
- 能把 `result.model_dump_json()` 和普通 `str(result)` 区分开。
- 能说明“结构合法”和“语义正确”是两件事。

### Day 4：设计页面需求分析字段

#### 当日课程

关联 Demo：[`demos/day04_schema_design_demo.py`](../../demos/day04_schema_design_demo.py)

运行：

```bash
.venv/bin/python demos/day04_schema_design_demo.py
```

观察每个字段如何对应一个下游用途，再把同样的字段职责合并到 `02_requirement_analyzer.py`。

今天不急着增加很多字段，而是先明确字段职责。推荐使用下面的最小字段集合：

| 字段 | 类型 | 职责 |
| --- | --- | --- |
| `page_type` | `str` | 页面类型，例如列表页、详情页、表单页 |
| `target_users` | `List[str]` | 页面面向的角色 |
| `core_components` | `List[str]` | 需要开发的前端组件 |
| `state_requirements` | `List[str]` | 页面需要维护的状态 |
| `api_assumptions` | `List[str]` | 根据需求推断的接口假设 |
| `risk_points` | `List[str]` | 交互、权限和异常风险 |
| `test_points` | `List[str]` | 后续可以验证的行为 |

每个字段只承担一个职责。面试时要能解释为什么不把所有内容塞进一个 `analysis: str`。

#### 代码练习：扩展 `RequirementAnalysis`

把下面字段合并到 `02_requirement_analyzer.py` 的模型中：

```python
from typing import List

from pydantic import BaseModel, Field


class RequirementAnalysis(BaseModel):
    # 页面类型用于帮助后续决定组件结构和常见交互。
    # 例如列表页通常需要查询、分页和空状态。
    page_type: str = Field(
        description="页面类型，例如列表页、详情页、表单页、看板页"
    )

    # 角色不是装饰信息，它会影响按钮展示、数据范围和后端权限校验。
    target_users: List[str] = Field(
        description="可以使用该页面的用户角色列表"
    )

    # 组件列表要尽量使用可开发的边界，而不是写成一大段描述。
    core_components: List[str] = Field(
        description="需要拆分和开发的前端组件列表"
    )

    # 这里描述的是需要在前端保存、变化或驱动渲染的状态。
    state_requirements: List[str] = Field(
        description="页面需要维护的状态字段列表"
    )

    # API 假设必须带“假设”意识，不能把模型推断的接口当成真实接口。
    api_assumptions: List[str] = Field(
        description="根据需求推断出的接口、参数或返回字段假设"
    )

    risk_points: List[str] = Field(
        description="权限、异常、并发、交互一致性等实现风险"
    )

    test_points: List[str] = Field(
        description="可用于验收页面行为的测试点列表"
    )
```

#### 对比练习

分别用“一个大字符串”和“多个明确字段”表达下面需求：

```text
做一个审批列表页，支持搜索、状态筛选、分页、批量通过和查看详情。
管理员可以批量操作，普通用户只能查看自己有权限的记录。
```

记录两种方案的差异：

- 哪种方案更容易被前端代码消费？
- 哪种方案更容易做字段级 Eval？
- 哪种方案更容易发现模型漏掉权限和分页状态？

#### 当日验收

- 每个字段都能用一句话解释职责。
- 能指出至少 2 个“不应该混在同一字段里”的信息。
- 运行 `02_requirement_analyzer.py` 后，新增字段能够输出。

### Day 5：识别模型输出的失败边界

#### 当日课程

关联 Demo：[`demos/day05_output_validation_demo.py`](../../demos/day05_output_validation_demo.py)

运行：

```bash
.venv/bin/python demos/day05_output_validation_demo.py
```

观察同一个 Demo 如何分别报告“结构校验失败”和“业务校验失败”。

今天学习“模型输出合法”不等于“结果可用”。常见失败分三层：

1. **解析失败**：不是合法 JSON，或者字段类型错误。
2. **结构失败**：JSON 合法，但漏了必需字段或列表为空。
3. **语义失败**：字段存在，但内容不符合需求，例如把“管理员”识别成“普通用户”。

面试回答不能只说“加重试”。要能说明先区分失败类型，再决定：

- 解析失败：schema、结构化输出、格式修正或重试。
- 结构失败：程序校验并返回明确错误。
- 语义失败：Eval、样例优化、人工标注和提示词改进。

#### 代码练习：分层校验结构化结果

```python
from typing import List

from pydantic import BaseModel, Field, ValidationError


class CheckedAnalysis(BaseModel):
    # Pydantic 负责第一层：字段类型和基本结构。
    page_type: str
    core_components: List[str] = Field(min_length=1)
    test_points: List[str] = Field(min_length=1)


def validate_business_result(result: CheckedAnalysis) -> List[str]:
    """做第二层业务校验，返回可读的问题列表。

    返回问题列表而不是立刻抛异常，便于学习阶段一次看到所有缺陷。
    生产代码可以根据调用链决定是抛异常、重试还是降级。
    """
    problems: List[str] = []

    # strip 后为空，说明虽然类型是 str，但业务上仍然不可用。
    if not result.page_type.strip():
        problems.append("page_type 不能为空")

    # 组件名为空时，模型虽然返回了列表，但没有产生可执行信息。
    if any(not component.strip() for component in result.core_components):
        problems.append("core_components 中不能包含空名称")

    # 测试点太泛时，无法支撑页面验收。
    if any(len(test_point.strip()) < 4 for test_point in result.test_points):
        problems.append("test_points 中存在过于简略的测试点")

    return problems


raw_result = {
    "page_type": "列表页",
    "core_components": ["SearchBar", "DataTable"],
    "test_points": ["", "接口失败时展示错误"],
}

try:
    # model_validate 会先检查字典是否满足 Pydantic schema。
    checked_result = CheckedAnalysis.model_validate(raw_result)
except ValidationError as error:
    # 这里处理的是结构或类型错误，例如 core_components 不是列表。
    print("结构校验失败：")
    print(error)
else:
    # 能进入这里，只代表结构合法，还要继续做业务语义校验。
    problems = validate_business_result(checked_result)
    if problems:
        print("业务校验失败：")
        for problem in problems:
            print(f"- {problem}")
```

#### 当日验收

- 能用自己的话区分解析失败、结构失败、语义失败。
- 能手动构造一个 `ValidationError`。
- 能说明为什么业务校验不能完全交给 Pydantic。

### Day 6：准备并标注第一批需求样例

#### 当日课程

关联 Demo：[`demos/day06_requirement_cases_demo.py`](../../demos/day06_requirement_cases_demo.py)

运行：

```bash
.venv/bin/python demos/day06_requirement_cases_demo.py
```

先看 Demo 中四类样例，再把其中的 `simulated_outputs` 替换成 `02_requirement_analyzer.py` 的真实输出。

今天开始建立面试项目的最小数据集。不要只准备“容易成功”的样例，要同时包含：

- 正常样例：信息完整、表达清楚。
- 边界样例：缺少角色、接口或异常说明。
- 模糊样例：只有“做一个管理页面”。
- 冲突样例：既要求普通用户可操作，又限制其没有权限。

一个好的样例至少包含：

```text
输入需求
期望必须出现的字段
期望必须出现的关键信息
不允许出现的错误判断
人工评分
```

#### 代码练习：定义需求样例和检查规则

```python
from dataclasses import dataclass
from typing import List


@dataclass
class RequirementCase:
    # name 方便在评测失败时快速定位是哪条样例。
    name: str
    # requirement 是传给 Agent 的原始需求。
    requirement: str
    # required_terms 是人工认为结果中必须覆盖的关键语义。
    required_terms: List[str]
    # forbidden_terms 用于检查明显错误，例如把“无权限”说成“可直接操作”。
    forbidden_terms: List[str]


CASES = [
    RequirementCase(
        name="审批列表正常样例",
        requirement="做一个审批列表页，支持搜索、筛选、分页和查看详情。",
        required_terms=["列表", "搜索", "分页", "详情"],
        forbidden_terms=["不需要错误提示"],
    ),
    RequirementCase(
        name="权限边界样例",
        requirement="管理员可以批量通过，普通用户只能查看自己有权限的审批记录。",
        required_terms=["管理员", "普通用户", "权限"],
        forbidden_terms=["所有用户都可以批量通过"],
    ),
    RequirementCase(
        name="模糊需求样例",
        requirement="做一个管理页面。",
        required_terms=["需要补充"],
        forbidden_terms=["已经明确所有接口"],
    ),
]


def check_text_result(text: str, case: RequirementCase) -> List[str]:
    """只做最基础的人工辅助检查，不替代真正的语义评估。"""
    problems: List[str] = []

    # required_terms 任意缺失，都说明结果可能没有覆盖需求重点。
    for term in case.required_terms:
        if term not in text:
            problems.append(f"缺少关键信息：{term}")

    # 命中 forbidden_terms 时，记录一个明确失败原因。
    for term in case.forbidden_terms:
        if term in text:
            problems.append(f"出现禁止判断：{term}")

    return problems


for case in CASES:
    # 这里先用假结果演示检查流程。
    # 后续可以把 result.model_dump_json() 的结果传进来。
    fake_result = f"样例：{case.name}；需求：{case.requirement}"
    print(case.name, check_text_result(fake_result, case))
```

#### 当日验收

- 至少准备 5 条需求样例。
- 样例至少覆盖列表页、表单页、权限场景、模糊需求和异常需求。
- 每条样例都有“必须覆盖”和“禁止出现”的检查项。

### Day 7：第 1 周复盘与 3 分钟口述

#### 当日课程

关联 Demo：[`demos/day07_week_review_demo.py`](../../demos/day07_week_review_demo.py)

运行：

```bash
.venv/bin/python demos/day07_week_review_demo.py
```

观察报告如何把单条失败和高频缺口分开记录；这就是后续 Eval 和 badcase 回流的基础。

用 3 分钟讲清楚下面这条链路：

```text
用户需求
  -> LLM 理解
  -> Pydantic 结构化输出
  -> 程序业务校验
  -> 前端可消费结果
```

复盘时重点回答：

- 为什么不直接返回自然语言？
- 为什么 schema 不能代替 Eval？
- 为什么一次 `invoke()` 还不是 Agent？

#### 代码练习：统计样例覆盖情况

```python
from typing import Dict, List


def summarize_case_result(
    required_terms: List[str],
    actual_text: str,
) -> Dict[str, object]:
    """把一次样例检查结果整理成可读摘要。

    这个函数不调用模型，故意保持确定性。
    评估辅助逻辑越确定，越容易写测试和定位问题。
    """
    matched_terms = [
        # 只保留实际出现在结果中的关键语义。
        term for term in required_terms if term in actual_text
    ]
    missing_terms = [
        # 记录没有覆盖的关键语义，后续可以沉淀成 badcase。
        term for term in required_terms if term not in actual_text
    ]

    # 用字典返回结构化统计，后续可以写入 JSON 或 Markdown 报告。
    return {
        "matched_terms": matched_terms,
        "missing_terms": missing_terms,
        "coverage": len(matched_terms) / len(required_terms)
        if required_terms
        else 1.0,
    }


summary = summarize_case_result(
    required_terms=["列表", "搜索", "分页", "权限"],
    actual_text="这是一个支持列表、搜索和分页的页面。",
)
print(summary)
```

#### 面试自测

回答：

> 如果面试官说“你的 Agent 只是调用了一次模型，为什么叫 Agent”，你怎么回应？

推荐回答方向：

> 当前最小版本确实更接近结构化 LLM Workflow。只有加入动态工具选择、状态循环、根据观察结果决定下一步等能力后，才更接近 Agent。学习阶段先从稳定的结构化输出开始，是为了避免一开始把概念和工程复杂度混在一起。

#### 当日验收

- 能在 3 分钟内讲清本周主线。
- 能指出当前项目仍然是“结构化 LLM + 固定流程”，还没有完整 Agent Loop。
- 形成一篇第 1 周复盘笔记。

## 第 2 周：结构化需求分析深入练习

第 2 周的面试目标：

- 能设计字段，而不是只会照抄 schema。
- 能解释嵌套模型、列表字段和校验错误。
- 能用固定样例检查输出质量。
- 能把模型生成、程序校验和人工评估分层。

### Day 8：明确每个输出字段的职责

#### 当日课程

关联 Demo：[`demos/day04_schema_design_demo.py`](../../demos/day04_schema_design_demo.py)

运行：

```bash
.venv/bin/python demos/day04_schema_design_demo.py
```

今天重新运行这个 Demo，但重点从“字段有哪些”切换到“每个字段交给哪个下游步骤使用”。

今天不改代码，先做 schema 设计。把每个字段写成一句“输入是什么、输出给谁、后续怎么用”的职责说明。

示例：

```text
core_components：
输入是页面需求，输出是可开发的组件边界，供前端拆分任务和测试范围使用。
```

避免下面这种模糊字段：

```text
analysis: str
```

因为它有三个问题：

- 程序无法稳定读取组件、状态和风险。
- 评估时无法知道具体漏了哪个字段。
- 前端开发者还要重新从自然语言里找信息。

#### 代码练习：用字段说明表达后续用途

```python
from typing import List

from pydantic import BaseModel, Field


class RequirementAnalysis(BaseModel):
    # page_type 影响页面模板和交互预期，
    # 例如列表页通常需要分页，详情页通常需要加载详情数据。
    page_type: str = Field(
        description="页面类型，供后续决定页面结构和常见交互"
    )

    # target_users 会影响按钮展示、数据过滤和后端权限校验。
    target_users: List[str] = Field(
        description="页面使用角色，供权限和数据范围分析使用"
    )

    # core_components 是前端开发任务的直接输入。
    core_components: List[str] = Field(
        description="可独立开发和测试的组件边界"
    )

    # state_requirements 是状态设计阶段的输入，
    # 例如 query_params、pagination、loading。
    state_requirements: List[str] = Field(
        description="页面中会变化、需要保存或驱动渲染的状态"
    )

    # api_assumptions 必须强调是“假设”，防止把模型推断当成真实接口契约。
    api_assumptions: List[str] = Field(
        description="根据需求推断的接口和字段假设，不能替代后端接口文档"
    )
```

#### 当日验收

- 为 8 个字段分别写一句职责说明。
- 能指出哪些字段属于“结果”，哪些字段属于“风险”。
- 能解释为什么 `api_assumptions` 不能直接当真实 API 契约。

### Day 9：嵌套 Pydantic 模型与 `model_validate`

#### 当日课程

关联 Demo：[`demos/day09_nested_model_demo.py`](../../demos/day09_nested_model_demo.py)

运行：

```bash
.venv/bin/python demos/day09_nested_model_demo.py
```

观察第一个 payload 如何成功转换，以及缺少 `responsibility` 时如何被 Pydantic 拦截。

学习两个面试高频点：

1. 为什么要用嵌套模型：让相关数据拥有明确边界。
2. `model_validate` 做什么：把外部字典校验并转换成模型实例。

模型输出来自外部系统，不能假设一定已经是目标类型。`model_validate` 是“进入程序边界时做校验和转换”的常见入口。

#### 代码练习：建立嵌套需求结构

```python
from typing import List

from pydantic import BaseModel, Field, ValidationError


class ComponentPlan(BaseModel):
    # name 是组件名称，例如 DataTable。
    name: str = Field(description="组件名称")
    # responsibility 说明组件负责什么，避免只有一个无法执行的名称。
    responsibility: str = Field(description="组件职责")


class RequirementPlan(BaseModel):
    # page_type 描述整体页面类别。
    page_type: str

    # components 是嵌套模型列表。
    # 这样每个组件都必须同时拥有 name 和 responsibility。
    components: List[ComponentPlan] = Field(min_length=1)


raw_payload = {
    "page_type": "审批列表页",
    "components": [
        {
            "name": "DataTable",
            "responsibility": "展示审批记录并支持分页",
        }
    ],
}

try:
    # model_validate 的输入可以是字典。
    # Pydantic 会递归校验 components 中的嵌套对象。
    plan = RequirementPlan.model_validate(raw_payload)
except ValidationError as error:
    # 只要外部数据缺字段或类型不对，就会进入这里。
    print("输入不符合 RequirementPlan：")
    print(error)
else:
    # 通过校验后，可以用属性访问，而不是到处手动取字典键。
    print(plan.page_type)
    print(plan.components[0].name)
```

#### 面试自测

1. 哪些类可以调用 `model_validate`？
2. 普通 Python 类为什么没有这个方法？
3. `model_validate` 和 `model_dump` 的方向有什么区别？

回答重点：

- 继承 `pydantic.BaseModel` 的模型类具备 `model_validate`。
- `model_validate` 是外部数据进入模型；`model_dump` 是模型对象导出为字典。

#### 当日验收

- 能写一个一层嵌套模型。
- 能手动构造一个缺少 `responsibility` 的错误输入。
- 能解释校验失败发生在模型调用之后、业务处理之前。

### Day 10：准备 5 条完整页面需求

#### 当日课程

关联 Demo：[`demos/day06_requirement_cases_demo.py`](../../demos/day06_requirement_cases_demo.py)

运行：

```bash
.venv/bin/python demos/day06_requirement_cases_demo.py
```

在现有四条样例基础上，补充一个详情页或表单页，并为它写 `required_terms` 和 `forbidden_terms`。

今天把样例从“文本列表”升级成可以反复运行的输入集。推荐五条：

1. 审批列表页：搜索、筛选、分页、批量操作、详情。
2. 用户详情页：基本信息、编辑、权限、保存失败。
3. 文件上传页：拖拽上传、进度、失败重试、取消。
4. 数据看板：时间筛选、指标卡、图表、空状态。
5. 模糊管理页：只写“做一个管理后台”，要求 Agent 先指出信息不足。

每条输入都要写预期覆盖点，避免只看最终回答“像不像”。

#### 代码练习：批量运行确定性检查

```python
from dataclasses import dataclass
from typing import List


@dataclass
class PageCase:
    # name 用于报告中展示样例名称。
    name: str
    # requirement 是交给需求分析 Agent 的原始输入。
    requirement: str
    # must_mention 是人工确认必须覆盖的概念。
    must_mention: List[str]


PAGE_CASES = [
    PageCase(
        name="审批列表",
        requirement="审批列表支持搜索、筛选、分页、批量通过和查看详情。",
        must_mention=["搜索", "分页", "批量", "详情"],
    ),
    PageCase(
        name="用户详情",
        requirement="用户详情页支持编辑资料和权限，保存失败要展示原因。",
        must_mention=["编辑", "权限", "失败"],
    ),
    PageCase(
        name="文件上传",
        requirement="文件上传支持进度、取消、失败重试和重复提交保护。",
        must_mention=["进度", "取消", "重试", "重复"],
    ),
    PageCase(
        name="数据看板",
        requirement="数据看板支持时间筛选、指标卡、趋势图和无数据状态。",
        must_mention=["时间", "指标", "趋势", "无数据"],
    ),
    PageCase(
        name="模糊管理页",
        requirement="做一个管理后台。",
        must_mention=["信息不足"],
    ),
]


def missing_terms(text: str, expected_terms: List[str]) -> List[str]:
    """返回输出中没有覆盖的重点。

    这是一个简单的词语检查器，不等于完整语义评测。
    它的价值是先把人工检查标准写出来，后续再替换成更强的 grader。
    """
    return [term for term in expected_terms if term not in text]


for case in PAGE_CASES:
    # 用一个占位字符串模拟 Agent 输出。
    # 实际练习时，将这里替换成 result.model_dump_json() 或 result.model_dump()。
    simulated_output = f"待填充输出：{case.requirement}"
    missing = missing_terms(simulated_output, case.must_mention)
    print(case.name, "缺少：" if missing else "通过", missing)
```

#### 当日验收

- 完成 5 条需求文本。
- 每条需求有至少 3 个可检查的关键语义。
- 模糊需求必须包含“应该追问或标记信息不足”的预期。

### Day 11：人工检查结构化输出质量

#### 当日课程

关联 Demo：[`demos/day11_quality_score_demo.py`](../../demos/day11_quality_score_demo.py)

运行：

```bash
.venv/bin/python demos/day11_quality_score_demo.py
```

修改四个维度的分数，观察总分和质量等级如何变化，再给自己的 5 份输出打分。

今天学习“字段存在”之外的质量检查。建议每份输出从四个维度打分：

| 维度 | 检查问题 |
| --- | --- |
| 完整性 | 关键字段有没有漏？ |
| 相关性 | 是否只围绕当前需求？ |
| 可执行性 | 前端能否据此拆任务？ |
| 风险意识 | 是否覆盖权限、异常、空状态、重复提交？ |

评分不是为了制造复杂流程，而是为了让“感觉不错”变成可讨论的结果。

#### 代码练习：建立人工评分结构

```python
from dataclasses import dataclass
from typing import Dict


@dataclass
class QualityScore:
    # 每个维度使用 0-2 分：
    # 0 = 没有覆盖，1 = 部分覆盖，2 = 覆盖且具体。
    completeness: int
    relevance: int
    executability: int
    risk_awareness: int

    def total(self) -> int:
        # 总分用于快速比较多个输出版本。
        return (
            self.completeness
            + self.relevance
            + self.executability
            + self.risk_awareness
        )


def grade_output(score: QualityScore) -> Dict[str, object]:
    """把人工评分整理成可记录的结果。"""
    total = score.total()

    # 这里的阈值只是学习阶段约定，
    # 真正项目应通过多条样例和人工标注校准。
    if total >= 7:
        level = "可继续使用"
    elif total >= 4:
        level = "需要人工修改"
    else:
        level = "不合格"

    return {
        "total": total,
        "level": level,
        "dimensions": {
            "completeness": score.completeness,
            "relevance": score.relevance,
            "executability": score.executability,
            "risk_awareness": score.risk_awareness,
        },
    }


print(
    grade_output(
        QualityScore(
            completeness=2,
            relevance=2,
            executability=1,
            risk_awareness=1,
        )
    )
)
```

#### 当日验收

- 给 5 份输出分别打分。
- 每份输出至少写一个“具体缺陷”，不能只写“感觉一般”。
- 选出一个最容易被面试官追问的失败样例。

### Day 12：补充字段和业务校验

#### 当日课程

关联 Demo：[`demos/day12_cross_field_validation_demo.py`](../../demos/day12_cross_field_validation_demo.py)

运行：

```bash
.venv/bin/python demos/day12_cross_field_validation_demo.py
```

先观察 Demo 报出的两个跨字段问题，再补齐 `selected_row_ids` 和权限风险，确认结果变为通过。

今天把校验分成两类：

- **字段级校验**：字段不能为空、列表至少有一项、类型正确。
- **跨字段业务校验**：如果页面有批量操作，就应该出现选择状态和权限风险；如果是模糊需求，就不应假装接口已经明确。

面试时要强调：Pydantic 更适合第一类，第二类需要业务函数或专门的 validator。

#### 代码练习：使用 `field_validator` 和业务校验

```python
from typing import List

from pydantic import BaseModel, Field, field_validator


class ValidatedAnalysis(BaseModel):
    # min_length=1 保证列表不能为空。
    core_components: List[str] = Field(min_length=1)
    state_requirements: List[str] = Field(min_length=1)
    risk_points: List[str] = Field(min_length=1)

    @field_validator("core_components", "state_requirements", "risk_points")
    @classmethod
    def items_must_not_be_blank(cls, items: List[str]) -> List[str]:
        """校验列表中的每一项都不是空字符串。"""
        # 这里处理的是同一类字段级规则，所以可以复用一个 validator。
        if any(not item.strip() for item in items):
            raise ValueError("列表项不能是空字符串")
        return items


def validate_cross_field_rules(analysis: ValidatedAnalysis) -> List[str]:
    """检查多个字段之间的业务关系。"""
    problems: List[str] = []

    # 页面如果支持批量操作，通常必须有选中项状态。
    if "BatchActionBar" in analysis.core_components:
        if "selected_row_ids" not in analysis.state_requirements:
            problems.append("存在批量操作，但缺少 selected_row_ids 状态")

    # 页面涉及权限时，风险列表必须提醒前后端权限一致校验。
    if "PermissionGuard" in analysis.core_components:
        if not any("权限" in risk for risk in analysis.risk_points):
            problems.append("存在权限组件，但风险点没有覆盖权限校验")

    return problems
```

#### 当日验收

- 至少写一个字段级校验。
- 至少写一个跨字段业务校验。
- 能解释为什么“字段都存在”仍然可能是错误结果。

### Day 13：理解模型生成与程序校验的分工

#### 当日课程

关联 Demo：[`demos/day13_layered_validation_demo.py`](../../demos/day13_layered_validation_demo.py)

运行：

```bash
.venv/bin/python demos/day13_layered_validation_demo.py
```

对比三个输入：完整输入、业务内容为空、字段类型错误，确认它们分别在哪一层失败。

今天把一条完整边界说清楚：

```text
模型：理解自然语言、提出结构化候选结果
Pydantic：验证字段和类型
业务代码：验证业务关系和权限边界
Eval：验证整体质量是否达到目标
人工：处理高风险或难以自动判断的情况
```

不要把所有问题都交给 Prompt，也不要把所有问题都交给模型自我检查。

#### 代码练习：建立分层处理函数

```python
from typing import Any, Dict

from pydantic import BaseModel, ValidationError


class SimpleAnalysis(BaseModel):
    page_type: str
    components: list[str]


def parse_and_validate(raw_data: Dict[str, Any]) -> SimpleAnalysis:
    """把外部结果转成可被业务代码信任的模型对象。"""
    try:
        # 第一层：Pydantic 校验输入结构。
        analysis = SimpleAnalysis.model_validate(raw_data)
    except ValidationError as error:
        # 这里应该返回结构化错误或触发一次修正重试，
        # 不能把未校验的 raw_data 继续交给后续工具。
        raise ValueError(f"模型输出结构不合法：{error}") from error

    # 第二层：业务语义校验。
    if not analysis.page_type.strip():
        raise ValueError("模型输出缺少有效 page_type")
    if not analysis.components:
        raise ValueError("模型输出没有任何组件")

    # 通过两层校验后，才把结果交给下游流程。
    return analysis


valid_data = {
    "page_type": "列表页",
    "components": ["DataTable"],
}

print(parse_and_validate(valid_data))
```

#### 面试自测

如果面试官问“模型已经返回 JSON 了，为什么还要校验”，回答：

> JSON 只说明文本格式可以被解析，不代表字段类型、必填项和业务语义正确。生产链路需要至少经过 schema 校验和业务校验；高风险结果还要经过权限检查或人工确认。

#### 当日验收

- 能画出“模型 -> schema -> 业务校验 -> 下游”的链路。
- 能说明 `try/except ValidationError` 在哪个边界负责什么。
- 能列出一个不能由 Prompt 单独解决的问题。

### Day 14：第 2 周复盘与结构化输出面试题

#### 当日课程

关联 Demo：[`demos/day13_layered_validation_demo.py`](../../demos/day13_layered_validation_demo.py) 和 [`02_requirement_analyzer.py`](../../02_requirement_analyzer.py)

运行：

```bash
.venv/bin/python demos/day13_layered_validation_demo.py
.venv/bin/python 02_requirement_analyzer.py
```

先运行 Demo 复习校验边界，再运行真实结构化输出脚本，口述“模型生成、schema、业务校验、Eval”四者的分工。

复盘以下面试题：

1. JSON Mode、Structured Output、Function Calling 有什么区别？
2. Pydantic 的 `BaseModel` 为什么适合 Tool schema？
3. 结构化输出失败后，是重试、降级还是人工处理？
4. 如何评估模型输出是否真的可用于前端开发？

建议回答框架：

```text
先说明目标
-> 再说明 schema 约束
-> 再说明程序校验
-> 最后说明 Eval 和失败兜底
```

#### 代码练习：生成一份结构化复盘摘要

```python
from typing import List


def build_interview_summary(
    known_points: List[str],
    unclear_points: List[str],
) -> str:
    """把学习结果整理成面试前可快速复习的文本。"""
    lines = ["## 已掌握"]

    # 已掌握内容逐条输出，避免复习时只看到一大段文字。
    lines.extend(f"- {point}" for point in known_points)

    lines.append("")
    lines.append("## 仍需补强")

    # 把不确定点单独列出，下一周可以转成新的练习或面试题。
    lines.extend(f"- {point}" for point in unclear_points)

    return "\n".join(lines)


print(
    build_interview_summary(
        known_points=[
            "能用 Pydantic 定义结构化输出",
            "能解释 schema 校验和业务校验的区别",
        ],
        unclear_points=[
            "还不能完整解释 Function Calling 的多轮执行",
            "还没有把结构化输出接入 Agent Loop",
        ],
    )
)
```

#### 当日验收

- 不看资料回答第 1-4 周相关的结构化输出问题。
- 从 5 个样例中选出一个 badcase，并说明根因。
- 完成第 2 周复盘笔记。

## 第 3 周：Tool Calling 第 1 天

### Day 15：理解 Tool Calling 的完整边界

#### 当日课程

关联 Demo：[`03_tool_calling.py`](../../03_tool_calling.py)、[`10_requirement_tool_agent.py`](../../10_requirement_tool_agent.py)、[`demos/day15_tool_dispatch_demo.py`](../../demos/day15_tool_dispatch_demo.py)

运行：

```bash
.venv/bin/python demos/day15_tool_dispatch_demo.py
.venv/bin/python 10_requirement_tool_agent.py
.venv/bin/python 03_tool_calling.py
```

先运行无模型依赖的 `day15_tool_dispatch_demo.py`，确认未知工具和非法路径会被拒绝；再看 `10_requirement_tool_agent.py` 的工具化 Agent，最后运行真实模型 Tool Calling。

阅读并运行：

```bash
.venv/bin/python 03_tool_calling.py
.venv/bin/python 10_requirement_tool_agent.py
```

重点理解两条链路：

```text
模型提出 tool_call
  -> 程序读取 name 和 args
  -> schema 校验参数
  -> Python 函数执行
  -> 返回结构化结果
  -> handler 更新 Agent state
```

以及：

```text
tool：只负责稳定能力的输入和输出
handler：负责调用工具、检查错误、写回 state
registry：描述工具什么时候使用、返回什么、有哪些错误
```

对照阅读：

- `03_tool_calling.py`：真实模型提出 `tool_calls`，程序执行 `create_file_plan`。
- `10_requirement_tool_agent.py`：把页面需求拆成多个确定性工具，并记录工具 trace。

#### 代码练习：手写一个最小工具调度器

这段代码重点展示“模型请求”和“工具执行”之间的边界。

```python
from typing import Any, Callable, Dict


def read_project_readme(path: str) -> Dict[str, Any]:
    """一个只读工具的示例。

    真实工具可以读取文件、查询数据库或调用 HTTP API。
    这里用固定返回值演示结构，不直接依赖外部服务。
    """
    # 真实代码中应该检查 path 是否允许访问，
    # 不能因为模型传入了路径就无条件读取任意文件。
    if path != "README.md":
        return {
            "success": False,
            "error_code": "PATH_NOT_ALLOWED",
            "error_message": "示例工具只允许读取 README.md",
        }

    return {
        "success": True,
        "data": {
            "summary": "这是 Python Agent Learning 项目说明文件。",
        },
    }


# 注册表把“工具名称”映射到“真正执行的 Python 函数”。
# 模型返回的是字符串 name，程序通过注册表找到对应函数。
TOOL_REGISTRY: Dict[str, Callable[..., Dict[str, Any]]] = {
    "read_project_readme": read_project_readme,
}


def dispatch_tool_call(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """校验并执行一次工具调用请求。"""
    # 先读取模型请求中的工具名。
    tool_name = tool_call.get("name")
    # args 是模型生成的参数，缺失时使用空字典，避免直接 KeyError。
    args = tool_call.get("args", {})

    # 未注册的工具不能执行。
    # 这是工具白名单的最小形式，也能避免模型随意拼接函数名。
    tool = TOOL_REGISTRY.get(tool_name)
    if tool is None:
        return {
            "success": False,
            "error_code": "UNKNOWN_TOOL",
            "error_message": f"未注册的工具：{tool_name}",
        }

    try:
        # 只有程序走到这里，才真正执行 Python 工具函数。
        result = tool(**args)
    except TypeError as error:
        # 参数名缺失或类型不匹配时，返回可读错误，
        # 不让一次错误调用直接打断整个 Agent。
        return {
            "success": False,
            "error_code": "INVALID_ARGS",
            "error_message": f"工具参数错误：{error}",
        }
    except Exception as error:
        # 真实项目中还应该记录 trace_id、工具名和耗时。
        return {
            "success": False,
            "error_code": "TOOL_EXECUTION_FAILED",
            "error_message": f"工具执行失败：{type(error).__name__}: {error}",
        }

    return result


print(
    dispatch_tool_call(
        {
            "name": "read_project_readme",
            "args": {"path": "README.md"},
        }
    )
)

print(
    dispatch_tool_call(
        {
            "name": "unknown_tool",
            "args": {},
        }
    )
)
```

#### 面试自测

1. `response.tool_calls` 是不是已经执行了工具？
2. 为什么工具需要 schema？
3. 工具失败后为什么要返回结构化错误，而不是直接抛出一大段异常？
4. 为什么工具注册表属于程序控制，而不是让模型随意调用任意函数？

推荐回答：

> `tool_calls` 只是模型提出的调用计划。程序需要校验工具名和参数，再调用真实 Python 函数。工具层返回结构化成功或失败结果，handler 再决定重试、降级、追问或终止。

#### 当日验收

- 能运行 `03_tool_calling.py`。
- 能运行 `10_requirement_tool_agent.py` 并说明三个工具各自职责。
- 能手动构造 `UNKNOWN_TOOL` 和 `INVALID_ARGS` 两个失败案例。
- 能清楚区分“模型决定调用什么”和“程序真正执行什么”。

## 前 15 天总验收

完成前 15 天后，至少应该达到下面的程度：

### 概念

- 能区分 Chatbot、Workflow、Agent。
- 能解释一次 LLM 调用的输入、输出和关键参数。
- 能解释结构化输出、Pydantic schema、业务校验和 Eval 的分工。
- 能解释 Tool Calling 不是模型直接执行 Python。

### 代码

- 能运行并修改 `01_cli_chat.py`。
- 能扩展 `02_requirement_analyzer.py` 的输出字段。
- 能使用 `BaseModel`、`Field`、`model_validate`。
- 能写字段级和跨字段业务校验。
- 能使用工具注册表调度确定性函数。

### 面试

不看资料回答：

1. 为什么 Agent 开发不能只靠 Prompt？
2. 结构化输出合法但语义错误时怎么办？
3. `BaseModel`、`model_validate`、`model_dump_json` 分别做什么？
4. Tool Calling 的完整链路是什么？
5. 为什么工具必须有权限边界和错误码？

### 代码运行检查

```bash
cd /Users/bytedance/Desktop/code/agent/python-agent-learning

# 前 15 天涉及的主要脚本。
.venv/bin/python 01_cli_chat.py
.venv/bin/python 02_requirement_analyzer.py
.venv/bin/python 03_tool_calling.py
.venv/bin/python 10_requirement_tool_agent.py

# 确定性逻辑和已有工具 Agent 测试。
.venv/bin/python -m pytest -q
```

如果没有模型 Key，优先完成：

```bash
.venv/bin/python 04_rag_qa.py --no-model "Button 有哪些类型？"
```

模型调用部分可以暂缓，但 schema、工具、校验、测试和面试口述仍然可以继续。
