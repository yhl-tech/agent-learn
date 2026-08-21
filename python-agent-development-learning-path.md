# Python 语言学习 LangChain 与 LangGraph：前端转 Agent 开发路线

> 目标：直接使用 Python 学习 Agent 开发，重点掌握 LangChain、LangGraph、RAG、Tool Calling、状态机工作流和生产化能力。
>
> 适合背景：有前端工程经验，想转向 Agent 应用开发、AI 工程、LLM 应用工程。

## 1. 为什么建议用 Python 学 Agent

Python 是当前 Agent 生态最完整的语言：

- LangChain、LangGraph 的核心文档和示例更丰富。
- 向量数据库、Embedding、Rerank、数据处理生态成熟。
- 机器学习、数据分析、自动化脚本都天然适配 Python。
- 大量 Agent 框架、评测工具、开源 Demo 都优先支持 Python。

前端经验不会浪费。你可以把原来的认知迁移过来：

| 前端开发 | Agent 开发 |
| --- | --- |
| Component | Chain / Node / Tool |
| State | Agent State / Memory |
| Router | Graph Edge |
| API Client | Tool Calling |
| Loading / Error | Streaming / Retry / Fallback |
| E2E Test | Eval / Regression Test |
| 埋点日志 | Trace / Observability |

Agent 开发的核心不是“会写 Prompt”，而是把 LLM、工具、状态、权限、日志和评估组合成稳定系统。

## 2. 环境准备

建议使用 Python 3.11+。

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
```

安装基础依赖：

```bash
pip install langchain langchain-core langchain-openai langgraph pydantic python-dotenv
```

如果要做 RAG：

```bash
pip install langchain-community langchain-text-splitters chromadb tiktoken
```

如果要做 Web API：

```bash
pip install fastapi uvicorn sse-starlette
```

`.env` 示例：

```bash
OPENAI_API_KEY=你的模型服务 Key
```

如果你使用公司内部模型或其他兼容 OpenAI 协议的服务，通常需要额外配置：

```bash
OPENAI_API_KEY=xxx
OPENAI_BASE_URL=https://your-compatible-endpoint/v1
```

## 3. 学习路径总览

建议按 6 个阶段推进，每个阶段都做一个小项目。

| 阶段 | 主题 | 项目 |
| --- | --- | --- |
| 第 1 阶段 | LLM 调用与 Prompt | CLI 问答助手 |
| 第 2 阶段 | 结构化输出 | 需求拆解助手 |
| 第 3 阶段 | Tool Calling | 前端项目规划助手 |
| 第 4 阶段 | RAG | 团队知识库问答 |
| 第 5 阶段 | LangGraph | Bug 排障 Agent |
| 第 6 阶段 | 生产化 | 可观测 Agent API 服务 |

## 4. 第 1 阶段：LLM 调用与 Prompt

### 4.1 必学理论

你需要先理解：

- Message：`system`、`human`、`ai` 消息。
- Token：模型处理文本的基本单位。
- Context Window：模型一次能看到的上下文长度。
- Temperature：控制输出随机性。
- Prompt：把任务、角色、约束、格式告诉模型。
- Hallucination：模型可能编造，需要检索、工具和校验兜底。

### 4.2 项目：CLI 问答助手

新建 `01_cli_chat.py`：

```python
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.2,
)

response = model.invoke(
    [
        ("system", "你是一个严格、简洁的前端技术导师。"),
        ("human", "解释 React useMemo 的适用场景，并给出反例。"),
    ]
)

print(response.content)
```

运行：

```bash
python 01_cli_chat.py
```

练习：

- 把 `temperature` 改成 `0`、`0.7`，比较输出稳定性。
- 修改 system prompt，让回答固定输出为 Markdown。
- 增加循环输入，做成命令行 Chatbot。

## 5. 第 2 阶段：结构化输出

### 5.1 必学理论

真实业务里，模型输出通常要被程序继续消费，所以不能只输出自然语言。

你需要掌握：

- Pydantic：定义结构化数据模型。
- Structured Output：让模型按 schema 输出。
- Validation：校验输出字段是否符合预期。
- Retry：解析失败时重试。

### 5.2 项目：AI 需求拆解助手

目标：输入产品需求，输出前端开发可用的结构化信息。

新建 `02_requirement_analyzer.py`：

```python
from typing import List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()


class RequirementAnalysis(BaseModel):
    page_goal: str = Field(description="页面目标")
    user_roles: List[str] = Field(description="用户角色")
    core_interactions: List[str] = Field(description="核心交互")
    api_dependencies: List[str] = Field(description="可能依赖的 API")
    state_design: List[str] = Field(description="前端状态设计建议")
    risk_points: List[str] = Field(description="实现风险")


model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
structured_model = model.with_structured_output(RequirementAnalysis)

requirement = """
做一个审批列表页，支持搜索、筛选、分页、批量通过、查看审批详情。
不同角色看到的操作按钮不同，审批失败需要展示错误原因。
"""

result = structured_model.invoke(
    [
        ("system", "你是资深前端技术负责人，请把需求拆成可执行的前端开发信息。"),
        ("human", requirement),
    ]
)

print(result.model_dump_json(indent=2, ensure_ascii=False))
```

运行：

```bash
python 02_requirement_analyzer.py
```

练习：

- 增加 `components` 字段，输出组件拆分。
- 增加 `test_cases` 字段，输出测试用例。
- 把结果保存为 Markdown 文件。

## 6. 第 3 阶段：Tool Calling

### 6.1 必学理论

普通 Chatbot 只能回答，Agent 可以调用工具。

工具可以是：

- 读文件
- 查数据库
- 搜索文档
- 调用业务 API
- 运行测试
- 生成文件计划
- 等待人工确认

Tool Calling 的工程重点：

- 工具 schema 必须严格。
- 工具返回要可被模型理解。
- 危险操作必须人工确认。
- 工具执行要有日志、超时和重试。

### 6.2 项目：前端项目规划助手

目标：用户描述页面需求，模型调用工具生成文件计划。

新建 `03_tool_calling.py`：

```python
from typing import List

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

load_dotenv()


class FileItem(BaseModel):
    path: str = Field(description="文件路径")
    purpose: str = Field(description="文件用途")


class FilePlanInput(BaseModel):
    page_name: str = Field(description="页面名称")
    files: List[FileItem] = Field(description="需要创建或修改的文件")


@tool(args_schema=FilePlanInput)
def create_file_plan(page_name: str, files: List[FileItem]) -> str:
    """根据页面需求生成前端文件计划，但不直接写文件。"""
    lines = [f"页面：{page_name}", "文件计划："]
    for item in files:
        lines.append(f"- {item.path}: {item.purpose}")
    return "\n".join(lines)


model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
model_with_tools = model.bind_tools([create_file_plan])

response = model_with_tools.invoke(
    [
        ("system", "你是前端工程助手。需要生成文件计划时必须调用工具。"),
        ("human", "我要做一个订单列表页，支持搜索、分页、导出。"),
    ]
)

print(response.tool_calls)

for tool_call in response.tool_calls:
    if tool_call["name"] == "create_file_plan":
        result = create_file_plan.invoke(tool_call["args"])
        print(result)
```

练习：

- 增加 `read_package_json` 工具，识别项目技术栈。
- 增加 `list_routes` 工具，避免重复路由。
- 增加人工确认，确认后再真正写文件。

## 7. 第 4 阶段：RAG 知识库问答

### 7.1 必学理论

RAG 是 Retrieval-Augmented Generation，检索增强生成。

基础流程：

```txt
文档 -> 切分 Chunk -> Embedding -> 向量库
用户问题 -> Embedding -> 检索相关 Chunk -> 拼上下文 -> LLM 回答
```

关键工程点：

- Chunk 太大会浪费上下文，太小会丢语义。
- Metadata 要保存来源、标题、路径、权限、更新时间。
- 回答必须带引用来源。
- 无来源时要允许回答“不确定”。
- 要用测试集评估召回率和回答质量。

### 7.2 项目：团队知识库问答

新建 `04_rag_qa.py`：

```python
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

load_dotenv()

docs = [
    Document(
        page_content="组件库 Button 支持 primary、secondary、danger 三种类型。",
        metadata={"source": "docs/components/button.md"},
    ),
    Document(
        page_content="表单提交前必须做 pydantic schema 校验，并展示字段级错误。",
        metadata={"source": "docs/forms/validation.md"},
    ),
]

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=80,
)
chunks = splitter.split_documents(docs)

vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=OpenAIEmbeddings(),
)

retriever = vector_store.as_retriever(search_kwargs={"k": 3})
question = "Button 有哪些类型？表单提交前要做什么？"
related_docs = retriever.invoke(question)

context = "\n\n".join(
    f"来源：{doc.metadata['source']}\n内容：{doc.page_content}"
    for doc in related_docs
)

model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
answer = model.invoke(
    [
        ("system", "请只根据给定上下文回答。答案末尾必须列出来源。"),
        ("human", f"问题：{question}\n\n上下文：\n{context}"),
    ]
)

print(answer.content)
```

运行：

```bash
python 04_rag_qa.py
```

练习：

- 把内存文档换成本地 Markdown 文件。
- 把 Chroma 持久化到本地目录。
- 给每个答案输出来源文件路径。
- 准备 20 个固定问题，做命中率评估。

## 8. 第 5 阶段：LangGraph Agent

### 8.1 必学理论

当任务需要多步骤执行时，单条 Chain 会变得难维护。LangGraph 用“状态图”管理 Agent 流程。

核心概念：

- State：贯穿整个任务的状态。
- Node：处理某一步的函数。
- Edge：固定流转。
- Conditional Edge：根据状态决定下一步。
- START / END：图的开始和结束。
- Checkpoint：保存中间状态，支持恢复。

典型 Agent 循环：

```txt
接收任务 -> 分析 -> 执行工具 -> 观察结果 -> 判断是否完成
                         ↑              |
                         └──── 继续修正 ┘
```

### 8.2 项目：Bug 排障 Agent

新建 `05_bug_agent.py`：

```python
from typing import List, Optional, TypedDict

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

load_dotenv()


class BugState(TypedDict):
    bug_report: str
    analysis: Optional[str]
    commands: Optional[List[str]]
    final_answer: Optional[str]


model = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def analyze_bug(state: BugState) -> BugState:
    response = model.invoke(
        [
            ("system", "你是资深前端排障工程师。"),
            ("human", f"分析这个 Bug 的可能原因：{state['bug_report']}"),
        ]
    )
    return {"analysis": str(response.content)}


def propose_commands(state: BugState) -> BugState:
    response = model.invoke(
        [
            ("system", "请给出用于验证 Bug 的命令，只输出命令列表。"),
            (
                "human",
                f"Bug：{state['bug_report']}\n分析：{state.get('analysis')}",
            ),
        ]
    )
    commands = [
        line.strip("- ").strip()
        for line in str(response.content).splitlines()
        if line.strip()
    ]
    return {"commands": commands}


def summarize(state: BugState) -> BugState:
    commands = state.get("commands") or []
    final_answer = "\n".join(
        [
            "## Bug 分析",
            state.get("analysis") or "",
            "",
            "## 建议排查命令",
            *[f"- `{command}`" for command in commands],
        ]
    )
    return {"final_answer": final_answer}


graph_builder = StateGraph(BugState)
graph_builder.add_node("analyze_bug", analyze_bug)
graph_builder.add_node("propose_commands", propose_commands)
graph_builder.add_node("summarize", summarize)

graph_builder.add_edge(START, "analyze_bug")
graph_builder.add_edge("analyze_bug", "propose_commands")
graph_builder.add_edge("propose_commands", "summarize")
graph_builder.add_edge("summarize", END)

graph = graph_builder.compile()

result = graph.invoke(
    {
        "bug_report": "点击保存后按钮一直 loading，接口实际已经返回 200。",
        "analysis": None,
        "commands": None,
        "final_answer": None,
    }
)

print(result["final_answer"])
```

练习：

- 增加 `read_file` 工具，读取相关源码。
- 增加 `run_test` 工具，执行指定测试命令。
- 增加条件分支：信息不足时先追问，信息足够时再总结。
- 增加人工确认：执行命令前让用户确认。

## 9. LangGraph 条件分支示例

真实 Agent 需要根据状态决定下一步。

示例：如果 Bug 描述太短，先追问；否则进入分析。

```python
from typing import Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph


class AskState(TypedDict):
    user_input: str
    question: Optional[str]
    answer: Optional[str]


def check_input(state: AskState) -> AskState:
    return state


def ask_more(state: AskState) -> AskState:
    return {
        "question": "请补充复现步骤、期望表现、实际表现和相关日志。"
    }


def answer(state: AskState) -> AskState:
    return {
        "answer": f"开始分析：{state['user_input']}"
    }


def route_after_check(state: AskState) -> Literal["ask_more", "answer"]:
    if len(state["user_input"]) < 20:
        return "ask_more"
    return "answer"


builder = StateGraph(AskState)
builder.add_node("check_input", check_input)
builder.add_node("ask_more", ask_more)
builder.add_node("answer", answer)

builder.add_edge(START, "check_input")
builder.add_conditional_edges("check_input", route_after_check)
builder.add_edge("ask_more", END)
builder.add_edge("answer", END)

graph = builder.compile()
print(graph.invoke({"user_input": "保存失败", "question": None, "answer": None}))
```

## 10. 第 6 阶段：生产化 Agent API

### 10.1 必学理论

上线 Agent 时要关注：

- Streaming：任务长时要持续返回进度。
- Timeout：防止无限执行。
- Retry：工具失败可以有限重试。
- Human Approval：危险操作人工确认。
- Trace：记录每一步输入、输出、耗时。
- Eval：用固定测试集回归。
- Versioning：记录 Prompt、模型、工具 schema 版本。
- Permission：控制工具访问范围。

### 10.2 FastAPI 示例

新建 `06_agent_api.py`：

```python
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

load_dotenv()

app = FastAPI()
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    response = model.invoke(
        [
            ("system", "你是 Agent 开发学习助手。"),
            ("human", request.message),
        ]
    )
    return ChatResponse(answer=str(response.content))
```

运行：

```bash
uvicorn 06_agent_api:app --reload --port 8000
```

请求：

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"解释 LangGraph 的 State 是什么"}'
```

## 11. 推荐项目路线

### 项目 1：AI 需求拆解助手

输入：产品需求。

输出：

- 页面目标
- 组件拆分
- API 依赖
- 状态设计
- 风险点
- 测试用例

使用能力：

- ChatOpenAI
- Pydantic
- Structured Output
- Markdown 导出

### 项目 2：团队知识库 RAG

输入：Markdown 文档、FAQ、组件库说明。

输出：

- 带来源引用的答案
- 不确定时拒答
- 相关文档链接

使用能力：

- Document Loader
- Text Splitter
- Embedding
- Chroma
- Retriever

### 项目 3：前端 Bug 排障 Agent

输入：Bug 描述、日志、相关文件路径。

输出：

- 复现路径
- 可能原因
- 排查命令
- 修复建议

使用能力：

- LangGraph
- Tool Calling
- 条件分支
- 人工确认

### 项目 4：PR Review Agent

输入：Git diff。

输出：

- 风险代码
- 行级建议
- 缺失测试
- 可访问性问题
- 性能问题

使用能力：

- 文件读取工具
- Diff 解析
- Review 规则
- Eval 测试集

## 12. 4 周学习计划

### 第 1 周：Python 与 LangChain 基础

目标：

- 跑通模型调用。
- 掌握 Prompt。
- 掌握 Pydantic 结构化输出。
- 完成需求拆解助手。

验收标准：

- 输入任意需求，可以稳定输出 JSON。
- 输出能被 Python 程序继续处理。
- 失败时有错误提示。

### 第 2 周：Tool Calling

目标：

- 学会定义工具。
- 学会让模型调用工具。
- 学会处理工具返回。
- 完成前端项目规划助手。

验收标准：

- Agent 能生成文件计划。
- 工具参数经过 schema 校验。
- 写操作前必须人工确认。

### 第 3 周：RAG

目标：

- 学会文档切分。
- 学会向量化。
- 学会检索。
- 完成知识库问答。

验收标准：

- 回答必须带来源。
- 无来源时回答“不确定”。
- 至少准备 20 个测试问题。

### 第 4 周：LangGraph

目标：

- 学会 StateGraph。
- 学会节点拆分。
- 学会条件分支。
- 完成 Bug 排障 Agent。

验收标准：

- 每个节点可以单独测试。
- Agent 过程可追踪。
- 信息不足时会追问。

## 13. 必须补齐的 Python 能力

你不需要先成为 Python 专家，但这些能力必须掌握：

- 虚拟环境：`venv`
- 包管理：`pip`
- 类型标注：`typing`
- 数据模型：`pydantic`
- 文件操作：`pathlib`
- HTTP 服务：`fastapi`
- 环境变量：`python-dotenv`
- 日志：`logging`
- 测试：`pytest`
- 异步：`asyncio`

推荐学习顺序：

```txt
Python 基础语法
  -> typing 类型标注
  -> pydantic 数据模型
  -> pathlib 文件操作
  -> fastapi Web API
  -> pytest 测试
  -> asyncio 异步任务
```

## 14. Agent 工程能力清单

### LLM 基础

- 会调用 Chat Model。
- 会设置 system prompt。
- 会控制 temperature。
- 会处理上下文长度。
- 会处理结构化输出失败。

### LangChain

- 会使用 `ChatOpenAI`。
- 会使用 Prompt。
- 会使用 Tool Calling。
- 会使用 Pydantic structured output。
- 会构建 RAG。

### LangGraph

- 会定义 State。
- 会拆 Node。
- 会连 Edge。
- 会写 Conditional Edge。
- 会处理循环。
- 会保存中间状态。

### 生产化

- 会记录 trace。
- 会设置超时。
- 会做失败重试。
- 会做人机确认。
- 会做权限边界。
- 会做 Eval 回归。

## 15. 常见误区

### 误区 1：只写 Prompt

Prompt 只是 Agent 的一部分。真实系统还需要：

- State
- Tool
- Memory
- Trace
- Eval
- Permission

### 误区 2：过早全自动

初期建议：

- 只读工具优先。
- 写操作必须人工确认。
- 高风险操作展示执行计划。

### 误区 3：不做评估

Agent 不稳定，必须有测试集。

至少准备：

- 典型问题
- 边界问题
- 错误输入
- 历史失败案例

### 误区 4：忽略前端体验

即使用 Python 写 Agent，最终也常常要接前端页面。Agent UI 应该展示：

- 当前执行阶段
- 工具调用过程
- 引用来源
- 错误信息
- 可取消、可重试、可确认操作

## 16. 最终路线图

```txt
Python 基础
  |
  v
LangChain：模型调用 / Prompt / 结构化输出
  |
  v
Tool Calling：让模型调用外部能力
  |
  v
RAG：让模型基于知识库回答
  |
  v
LangGraph：状态机、多步骤 Agent、条件分支
  |
  v
FastAPI：把 Agent 封装成服务
  |
  v
Trace / Eval / 权限 / 人工确认
  |
  v
Agent 开发工程师
```

## 17. 你的下一步

建议直接从这个最小目录开始：

```txt
python-agent-learning/
  .env
  requirements.txt
  data/kb/
  01_cli_chat.py
  02_requirement_analyzer.py
  03_tool_calling.py
  04_rag_qa.py
  05_langgraph_bug_agent.py
  06_agent_api.py
  07_eval_regression.py
  08_human_approval_file_writer.py
```

`requirements.txt`：

```txt
langchain
langchain-core
langchain-text-splitters
langchain-openai
langgraph
pydantic
python-dotenv
fastapi
uvicorn
pytest
```

最优先完成：

1. `01_cli_chat.py`：确认模型能调用。
2. `02_requirement_analyzer.py`：掌握结构化输出。
3. `03_tool_calling.py`：理解工具 schema、`tool_calls` 和 `.invoke()`。
4. `04_rag_qa.py`：理解本地知识库、chunk、检索和上下文拼接。
5. `05_langgraph_bug_agent.py`：理解 LangGraph 状态流转和条件分支。
6. `06_agent_api.py`：把 Agent 能力封装成 API。
7. `07_eval_regression.py`：用固定样例做回归评估。
8. `08_human_approval_file_writer.py`：理解危险操作前的人机确认。

这些脚本跑通并完成改造练习后，你就已经从“会调模型”进入“会构建 Agent 工作流”的门槛。

## 18. 7 天实践强化路线

如果目标是尽快达到 Agent 初级开发水平，建议按下面节奏练。每天都必须跑代码、改代码、做验收。

### 第 1 天：LLM 调用和结构化输出

运行：

```bash
python 01_cli_chat.py
python 02_requirement_analyzer.py
```

必须改动：

- 修改 system prompt，观察输出风格变化。
- 给 `RequirementAnalysis` 增加 `acceptance_criteria` 字段。
- 把需求文本换成你熟悉的前端页面需求。

验收标准：

- 能解释 `system`、`human`、`response.content`。
- 能解释 Pydantic schema 为什么能约束模型输出。
- 能拿结构化结果继续写业务逻辑，而不是只打印字符串。

### 第 2 天：Tool Calling

运行：

```bash
python 03_tool_calling.py
```

必须改动：

- 增加一个只读工具，例如 `read_project_readme`。
- 手动构造错误参数，观察 `try/except` 返回的错误信息。
- 给工具返回值增加更适合前端展示的结构。

验收标准：

- 能解释 `@tool`、`args_schema`、`response.tool_calls`、`.invoke()`。
- 能说明模型只是生成工具调用请求，Python 才是真正执行工具的一方。
- 能给工具执行失败加错误兜底。

### 第 3 天：RAG

运行：

```bash
python 04_rag_qa.py --no-model "Button 有哪些类型？"
python 04_rag_qa.py --no-model "表单提交前要做什么？"
```

必须改动：

- 在 `data/kb` 新增一篇 Markdown 文档。
- 新增一个能命中该文档的问题。
- 把 `k` 从 3 改成 1 和 5，观察检索上下文变化。

验收标准：

- 能解释文档、chunk、retrieval、context、answer 的关系。
- 能输出来源，避免无依据回答。
- 能说明后续如何把关键词检索替换成 Embedding + 向量库。

### 第 4 天：LangGraph

运行：

```bash
python 05_langgraph_bug_agent.py "保存失败"
python 05_langgraph_bug_agent.py "点击保存后按钮一直 loading，接口实际已经返回 200。"
```

必须改动：

- 新增一个节点，例如 `classify_severity`。
- 新增一个条件分支，例如高风险 Bug 先要求人工确认。
- 在最终总结里输出当前走过的节点。

验收标准：

- 能定义 State。
- 能拆 Node。
- 能用 Edge 和 Conditional Edge 控制流程。
- 能解释为什么复杂 Agent 要用状态机，而不是一个大函数。

### 第 5 天：Agent API

运行：

```bash
python 06_agent_api.py
```

另开终端请求：

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/rag/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Tool Calling 失败怎么处理？","use_model":false}'
```

必须改动：

- 新增一个 `/bug/analyze` 接口，调用 `05_langgraph_bug_agent.py` 的图。
- 给响应增加 `trace_id` 字段。
- 给错误情况返回清晰的错误信息。

验收标准：

- 能用 FastAPI 暴露 Agent 能力。
- 能设计请求和响应 schema。
- 能让前端通过 HTTP 调用 Agent，而不是只能本地运行脚本。

### 第 6 天：Eval 回归

运行：

```bash
python 07_eval_regression.py
pytest -q
```

必须改动：

- 新增 2 个 `EvalCase`。
- 故意改坏检索逻辑，确认 Eval 会失败。
- 修复检索逻辑，再确认 Eval 通过。
- 至少新增 1 条 pytest，覆盖你改动过的确定性逻辑。

验收标准：

- 能解释为什么 Agent 项目必须有固定评测集。
- 能区分“人工试了一下”和“可重复回归验证”。
- 能把历史失败案例沉淀为 EvalCase。

### 第 7 天：人工确认和权限边界

运行：

```bash
python 08_human_approval_file_writer.py
```

必须改动：

- 输入非 `yes`，确认不会写文件。
- 输入 `yes`，确认只写入 `generated` 目录。
- 尝试构造 `../danger.txt`，确认路径越界会被拦截。

验收标准：

- 能解释哪些工具属于危险操作。
- 能实现“先生成计划，再人工确认，再执行”的流程。
- 能限制文件写入范围。

## 19. 初级 Agent 开发最低能力清单

完成上面练习后，你至少应该能独立完成：

- 调用 Chat Model，并能解释消息结构和 temperature。
- 使用 Pydantic 做结构化输出。
- 定义 LangChain tool，并处理工具参数错误。
- 实现一个带来源的只读 RAG 问答。
- 使用 LangGraph 拆出多节点流程和条件分支。
- 使用 FastAPI 暴露 Agent 接口。
- 编写 Eval 脚本，覆盖核心路径。
- 给写文件、执行命令等危险操作加人工确认。

如果这些都能自己写出来，并能向别人解释每一步为什么这么设计，就已经达到 Agent 初级开发的入门线。
