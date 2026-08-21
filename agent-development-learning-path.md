# 前端开发者转 Agent 开发：LangChain 与 LangGraph 学习路径

> 目标读者：有 React / TypeScript / Node.js 基础，希望从前端开发转向 AI Agent 应用开发的工程师。
>
> 核心目标：不是只学 API，而是理解 Agent 系统如何被拆成可测试、可观测、可迭代的工程模块。

## 1. 转型视角：从前端工程到 Agent 工程

前端开发关注的是“用户输入 -> 状态变化 -> UI 输出”。Agent 开发关注的是“用户目标 -> 模型推理 -> 工具调用 -> 状态推进 -> 可验证结果”。

| 前端开发概念 | Agent 开发对应概念 | 说明 |
| --- | --- | --- |
| 组件 Component | Chain / Node / Tool | 将复杂能力拆成可组合单元 |
| 状态 State | Agent State / Memory | 保存任务上下文、中间结果、用户偏好 |
| 路由 Router | Graph Edge / Conditional Edge | 决定下一步走哪个节点 |
| 表单输入 | Prompt / Message | 用户意图、系统约束、上下文注入 |
| API 请求 | Tool Calling | 让模型调用外部系统、数据库、搜索、业务接口 |
| Loading / Error UI | Streaming / Retry / Fallback | 长任务、失败恢复、降级策略 |
| 埋点与日志 | Tracing / Observability | 记录模型输入输出、工具调用、耗时与失败 |
| 单元测试 / E2E | Eval / Regression Test | 检查回答质量、工具选择、任务完成率 |

结论：你已有的工程能力很有价值。Agent 开发不是“写提示词”，而是把 LLM 放进一个可靠的软件系统里。

## 2. LangChain 与 LangGraph 的定位

### 2.1 LangChain 解决什么问题

LangChain 更像 Agent 应用的“工具箱”和“组合层”，主要提供：

- 模型封装：统一调用 OpenAI、Anthropic、通义、豆包、火山等模型。
- Prompt 模板：把系统约束、用户输入、上下文拼装成稳定输入。
- Output Parser：把模型输出解析成 JSON、结构化对象或业务字段。
- Tool Calling：定义工具，让模型按 schema 调用外部能力。
- RAG：文档加载、切分、向量化、检索、重排、生成。
- Memory：短期对话记忆、长期用户偏好、业务上下文。
- Tracing / Callback：记录运行过程，便于调试和评估。

### 2.2 LangGraph 解决什么问题

LangGraph 更像 Agent 应用的“状态机 / 工作流引擎”，用于构建可控 Agent：

- 显式 State：定义任务全过程的状态结构。
- Node：每一步处理逻辑，例如规划、检索、调用工具、总结。
- Edge：节点之间的流转关系。
- Conditional Edge：根据当前状态决定下一步。
- Cyclic Graph：支持反复规划、执行、观察、修正。
- Human-in-the-loop：关键步骤等待人工确认。
- Checkpoint：保存中间状态，支持恢复、回放和长任务。

简单理解：

- LangChain 适合做“单步能力”和“基础组件”。
- LangGraph 适合做“多步骤、可恢复、可观测、可干预”的 Agent 系统。

## 3. 推荐技术栈

前端开发者建议优先走 TypeScript 路线：

```bash
npm install langchain @langchain/core @langchain/openai @langchain/community @langchain/langgraph zod
```

常见项目组合：

- Web 框架：Next.js / Remix / Vite + Express / NestJS
- Agent 层：LangChain.js + LangGraph.js
- 数据存储：PostgreSQL / Redis / SQLite
- 向量数据库：pgvector / Chroma / Qdrant / Milvus
- 可观测性：LangSmith / OpenTelemetry / 自建日志
- 部署：Node.js 服务、Serverless、容器化服务

Python 生态在 Agent 方向资料更多，适合后续补齐：

```bash
pip install langchain langgraph langchain-openai
```

但对前端转型而言，第一阶段不建议同时深挖两套语言，否则会分散精力。先用 TypeScript 做出可运行项目，再补 Python。

## 4. 学习路径总览

建议按 6 个阶段推进，每个阶段都绑定一个项目。

| 阶段 | 主题 | 目标项目 |
| --- | --- | --- |
| 第 1 阶段 | LLM 基础与 Prompt 工程 | CLI 问答助手 |
| 第 2 阶段 | LangChain 基础链路 | 结构化需求分析助手 |
| 第 3 阶段 | Tool Calling | 前端项目脚手架助手 |
| 第 4 阶段 | RAG | 团队知识库问答系统 |
| 第 5 阶段 | LangGraph Agent | Bug 分析与修复建议 Agent |
| 第 6 阶段 | 生产化 | 可观测、可评估、可回滚的 Agent 服务 |

## 5. 第 1 阶段：LLM 基础与 Prompt 工程

### 5.1 必学理论

你需要理解这些概念：

- Token：模型处理文本的基本单位，影响成本、上下文长度和延迟。
- Context Window：模型一次能看到的最大上下文。
- System / User / Assistant Message：不同角色消息的优先级和用途。
- Temperature：控制随机性，越低越稳定，越高越发散。
- Structured Output：让模型输出固定 JSON 结构，方便程序消费。
- Hallucination：模型编造事实，需要用检索、工具和校验降低风险。

### 5.2 项目：CLI 问答助手

目标：写一个最小可用 LLM 调用程序，理解消息结构与参数。

```ts
import { ChatOpenAI } from "@langchain/openai";

const model = new ChatOpenAI({
  model: "gpt-4o-mini",
  temperature: 0.2,
});

const response = await model.invoke([
  ["system", "你是一个严格、简洁的前端技术导师。"],
  ["user", "解释 React useMemo 的适用场景，并给出反例。"],
]);

console.log(response.content);
```

练习：

- 改变 temperature，对比输出稳定性。
- 加入 system prompt，限制回答格式。
- 让模型输出 Markdown、JSON、表格三种格式。

## 6. 第 2 阶段：LangChain 基础链路

### 6.1 必学理论

LangChain 的核心思想是 Runnable。你可以把 Prompt、Model、Parser 像管道一样组合。

典型链路：

```txt
用户输入 -> PromptTemplate -> ChatModel -> OutputParser -> 业务代码
```

这和前端中的数据流类似：

```txt
用户事件 -> 状态更新 -> 组件渲染 -> 副作用处理
```

### 6.2 项目：结构化需求分析助手

目标：输入一段产品需求，输出前端开发关心的结构化字段。

```ts
import { ChatOpenAI } from "@langchain/openai";
import { ChatPromptTemplate } from "@langchain/core/prompts";
import { StructuredOutputParser } from "@langchain/core/output_parsers";
import { z } from "zod";

const parser = StructuredOutputParser.fromZodSchema(
  z.object({
    pageGoal: z.string().describe("页面目标"),
    userRoles: z.array(z.string()).describe("用户角色"),
    coreInteractions: z.array(z.string()).describe("核心交互"),
    apiDependencies: z.array(z.string()).describe("可能依赖的 API"),
    riskPoints: z.array(z.string()).describe("实现风险"),
  }),
);

const prompt = ChatPromptTemplate.fromMessages([
  ["system", "你是资深前端技术负责人。请把需求拆成可执行的前端开发信息。"],
  ["user", "{requirement}\n\n输出格式要求：\n{formatInstructions}"],
]);

const model = new ChatOpenAI({
  model: "gpt-4o-mini",
  temperature: 0,
});

const chain = prompt.pipe(model).pipe(parser);

const result = await chain.invoke({
  requirement: "做一个审批列表页，支持搜索、筛选、批量通过、查看审批详情。",
  formatInstructions: parser.getFormatInstructions(),
});

console.log(result);
```

练习：

- 把结果展示到 React 页面。
- 保存历史分析记录。
- 对输出 JSON 做 zod 校验，失败时重试。

## 7. 第 3 阶段：Tool Calling

### 7.1 必学理论

Agent 与普通 Chatbot 的关键区别：Agent 可以调用工具改变外部世界。

工具可以是：

- 搜索工具：查询文档、网页、代码库。
- 数据工具：读写数据库、调用业务 API。
- 文件工具：读取、生成、修改文件。
- 执行工具：运行测试、构建、Lint。
- 人工确认工具：等待用户审批。

前端工程视角下，Tool Calling 很像“模型决定何时调用哪个后端接口”，但接口 schema 必须严格。

### 7.2 项目：前端项目脚手架助手

目标：用户描述页面需求，Agent 调用工具生成文件计划。

```ts
import { ChatOpenAI } from "@langchain/openai";
import { tool } from "@langchain/core/tools";
import { z } from "zod";

const createFilePlan = tool(
  async ({ pageName, files }) => {
    return JSON.stringify({
      pageName,
      files,
      message: "文件计划已生成，等待人工确认后再写入磁盘。",
    });
  },
  {
    name: "create_file_plan",
    description: "根据页面需求生成前端文件计划，但不直接写文件。",
    schema: z.object({
      pageName: z.string(),
      files: z.array(
        z.object({
          path: z.string(),
          purpose: z.string(),
        }),
      ),
    }),
  },
);

const model = new ChatOpenAI({
  model: "gpt-4o-mini",
  temperature: 0,
}).bindTools([createFilePlan]);

const response = await model.invoke([
  ["system", "你是前端工程助手。需要生成文件计划时必须调用工具。"],
  ["user", "我要做一个订单列表页，支持搜索、分页、导出。"],
]);

console.log(response.tool_calls);
```

练习：

- 增加 `readPackageJson` 工具，识别项目技术栈。
- 增加 `listRoutes` 工具，避免生成重复路由。
- 增加人工确认步骤，确认后再写文件。

## 8. 第 4 阶段：RAG 知识库问答

### 8.1 必学理论

RAG 是 Retrieval-Augmented Generation，即“检索增强生成”。

基础流程：

```txt
文档 -> 切分 Chunk -> Embedding -> 向量库
用户问题 -> Embedding -> 相似度检索 -> 拼上下文 -> LLM 生成答案
```

RAG 的关键不是“把文档塞给模型”，而是解决这些工程问题：

- Chunk 怎么切：太大浪费上下文，太小丢失语义。
- Metadata 怎么设计：文件路径、标题、版本、权限、更新时间。
- 检索怎么评估：是否召回了正确文档。
- 答案如何引用来源：降低幻觉，方便用户验证。
- 权限如何控制：不同用户只能检索自己有权限的内容。

### 8.2 项目：团队知识库问答系统

目标：把团队 Markdown 文档接入 RAG，做一个带引用来源的问答系统。

```ts
import { ChatOpenAI, OpenAIEmbeddings } from "@langchain/openai";
import { MemoryVectorStore } from "langchain/vectorstores/memory";
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";
import { Document } from "@langchain/core/documents";

const rawDocs = [
  new Document({
    pageContent: "组件库 Button 支持 primary、secondary、danger 三种类型。",
    metadata: { source: "docs/components/button.md" },
  }),
  new Document({
    pageContent: "表单提交前必须做 zod schema 校验，并展示字段级错误。",
    metadata: { source: "docs/forms/validation.md" },
  }),
];

const splitter = new RecursiveCharacterTextSplitter({
  chunkSize: 500,
  chunkOverlap: 80,
});

const chunks = await splitter.splitDocuments(rawDocs);

const vectorStore = await MemoryVectorStore.fromDocuments(
  chunks,
  new OpenAIEmbeddings(),
);

const retriever = vectorStore.asRetriever({ k: 3 });
const question = "Button 有哪些类型？表单提交前要做什么？";
const relatedDocs = await retriever.invoke(question);

const model = new ChatOpenAI({ model: "gpt-4o-mini", temperature: 0 });
const answer = await model.invoke([
  ["system", "请只根据给定上下文回答，并在答案末尾列出来源。"],
  [
    "user",
    `问题：${question}

上下文：
${relatedDocs
  .map((doc) => `来源：${doc.metadata.source}\n内容：${doc.pageContent}`)
  .join("\n\n")}`,
  ],
]);

console.log(answer.content);
```

练习：

- 把 MemoryVectorStore 换成 pgvector / Chroma。
- 增加“答案必须带来源链接”的输出约束。
- 做一组测试问题，记录命中率和回答质量。

## 9. 第 5 阶段：LangGraph Agent

### 9.1 必学理论

当任务变成多步骤时，单条 Chain 会变得难维护。LangGraph 用图来描述 Agent 的运行过程。

一个典型 Agent 循环：

```txt
接收任务 -> 规划 -> 执行工具 -> 观察结果 -> 判断是否完成
                         ↑              |
                         └──── 继续修正 ┘
```

LangGraph 的核心对象：

- State：贯穿全流程的数据。
- Node：处理 State 的函数。
- Edge：固定流转。
- Conditional Edge：条件流转。
- START / END：图的开始与结束。

### 9.2 项目：Bug 分析与修复建议 Agent

目标：输入 Bug 描述，Agent 自动拆解为“复现路径、可能原因、排查命令、修复建议”。

```ts
import { Annotation, END, START, StateGraph } from "@langchain/langgraph";
import { ChatOpenAI } from "@langchain/openai";

const BugState = Annotation.Root({
  bugReport: Annotation<string>(),
  analysis: Annotation<string | undefined>(),
  commands: Annotation<string[] | undefined>(),
  finalAnswer: Annotation<string | undefined>(),
});

const model = new ChatOpenAI({
  model: "gpt-4o-mini",
  temperature: 0,
});

async function analyzeBug(state: typeof BugState.State) {
  const response = await model.invoke([
    ["system", "你是资深前端排障工程师。"],
    ["user", `分析这个 Bug 的可能原因：${state.bugReport}`],
  ]);

  return {
    analysis: String(response.content),
  };
}

async function proposeCommands(state: typeof BugState.State) {
  const response = await model.invoke([
    ["system", "请给出用于验证 Bug 的命令，只输出命令列表。"],
    ["user", `Bug：${state.bugReport}\n分析：${state.analysis}`],
  ]);

  return {
    commands: String(response.content)
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean),
  };
}

async function summarize(state: typeof BugState.State) {
  return {
    finalAnswer: [
      "## Bug 分析",
      state.analysis,
      "",
      "## 建议排查命令",
      ...(state.commands ?? []).map((command) => `- \`${command}\``),
    ].join("\n"),
  };
}

const graph = new StateGraph(BugState)
  .addNode("analyzeBug", analyzeBug)
  .addNode("proposeCommands", proposeCommands)
  .addNode("summarize", summarize)
  .addEdge(START, "analyzeBug")
  .addEdge("analyzeBug", "proposeCommands")
  .addEdge("proposeCommands", "summarize")
  .addEdge("summarize", END)
  .compile();

const result = await graph.invoke({
  bugReport: "点击保存后按钮一直 loading，接口实际已经返回 200。",
});

console.log(result.finalAnswer);
```

练习：

- 加一个 `readFile` 工具，让 Agent 读取相关源码。
- 加一个 `runTest` 工具，让 Agent 执行指定测试。
- 加 Conditional Edge：如果信息不足，先追问用户；如果足够，再给修复建议。

## 10. 第 6 阶段：生产化 Agent 工程

### 10.1 必学理论

真实 Agent 项目最难的不是 Demo，而是生产化：

- 稳定性：模型输出不稳定，工具调用可能失败。
- 成本：Token、Embedding、检索、重试都会产生成本。
- 延迟：多轮工具调用会显著变慢。
- 权限：Agent 可能访问敏感数据或执行危险操作。
- 可观测性：必须知道每一步输入、输出、耗时和失败原因。
- 可评估性：需要用测试集持续评估 Agent 表现。
- 可回滚性：Prompt、工具和模型版本变化都可能引入回归。

### 10.2 项目：可上线的 Agent 服务

建议架构：

```txt
前端页面
  |
  | SSE / WebSocket Streaming
  v
Next.js API / Node.js 服务
  |
  | 调用
  v
LangGraph Agent
  |
  | 工具调用
  v
业务 API / 数据库 / 向量库 / 文件系统
  |
  v
Tracing / Logs / Eval Dataset
```

关键工程能力：

- Streaming：前端实时展示 Agent 进度。
- Interrupt：允许用户停止任务。
- Human Approval：危险工具执行前必须确认。
- Retry：工具失败时有限重试。
- Timeout：防止 Agent 无限运行。
- Rate Limit：限制用户调用频率。
- Eval：固定问题集回归测试。
- Versioning：Prompt、工具 schema、模型版本都要记录。

## 11. 面向前端开发者的项目路线

### 项目 1：AI 需求拆解助手

输入：产品需求文档。

输出：

- 页面结构
- 组件拆分
- API 依赖
- 状态管理方案
- 风险点

你会学到：

- Prompt Template
- Structured Output
- Zod Schema
- 前端工程语义建模

### 项目 2：组件库问答助手

输入：组件库文档。

输出：带来源引用的回答。

你会学到：

- Document Loader
- Text Splitter
- Embedding
- Vector Store
- Retriever
- RAG 评估

### 项目 3：代码库理解助手

输入：用户问题，例如“这个页面保存逻辑在哪里？”。

输出：相关文件、函数、调用链解释。

你会学到：

- 代码检索
- AST / 文件索引
- Tool Calling
- 权限控制
- 引用来源

### 项目 4：前端 Bug 排障 Agent

输入：Bug 描述、截图、日志。

输出：

- 复现路径
- 可能原因
- 排查命令
- 相关文件
- 修复建议

你会学到：

- LangGraph State
- 多节点工作流
- 条件分支
- 工具调用
- 人工确认

### 项目 5：PR Review Agent

输入：Git diff。

输出：

- 风险代码
- 行级 Review 意见
- 缺失测试
- 性能或可访问性问题

你会学到：

- Diff 解析
- Review 规则设计
- Eval 数据集
- 误报控制

## 12. 关键能力清单

### 12.1 LLM 应用基础

- 理解 Chat Model、Embedding Model、Rerank Model 的区别。
- 会设计 system prompt、few-shot examples、输出格式约束。
- 会处理 JSON 解析失败、模型拒答、上下文超长。
- 会做 Prompt 版本管理。

### 12.2 LangChain 能力

- 会使用 ChatOpenAI / 其他模型适配器。
- 会使用 ChatPromptTemplate。
- 会使用 Runnable pipe。
- 会定义 tool schema。
- 会使用 StructuredOutputParser。
- 会构建 RAG 链路。

### 12.3 LangGraph 能力

- 会定义 State。
- 会拆 Node。
- 会设计 Edge 和 Conditional Edge。
- 会处理循环。
- 会接入工具调用。
- 会做人机协同。
- 会保存和恢复执行状态。

### 12.4 Agent 工程能力

- 会设计工具权限边界。
- 会给危险操作加人工确认。
- 会记录每一步模型输入输出。
- 会做失败重试与超时。
- 会评估 Agent 输出质量。
- 会优化成本和延迟。

## 13. 推荐学习顺序

### 第 1 周：LLM 与 LangChain 入门

- 跑通模型调用。
- 掌握 PromptTemplate。
- 掌握结构化输出。
- 完成“需求拆解助手”。

验收标准：

- 输入任意需求，可以稳定输出 JSON。
- JSON 字段能被前端页面直接渲染。
- 输出失败时有重试或错误提示。

### 第 2 周：Tool Calling

- 学会定义工具 schema。
- 学会让模型选择工具。
- 学会在工具前后记录日志。
- 完成“项目脚手架助手”。

验收标准：

- Agent 能根据需求生成文件计划。
- 文件写入前必须等待确认。
- 工具参数由 zod 校验。

### 第 3 周：RAG

- 学会文档切分。
- 学会 Embedding。
- 学会向量检索。
- 完成“组件库问答助手”。

验收标准：

- 回答必须带来源。
- 对 20 个固定问题做命中率测试。
- 无来源的问题必须回答“不确定”。

### 第 4 周：LangGraph

- 学会 StateGraph。
- 学会多节点任务拆分。
- 学会条件分支。
- 完成“Bug 排障 Agent”。

验收标准：

- Agent 输出过程可追踪。
- 信息不足时会追问。
- 可以把每个节点单独测试。

### 第 5-6 周：生产化

- 接入前端 Streaming UI。
- 加权限、超时、重试、日志。
- 建立 Eval 数据集。
- 完成一个可内部使用的 Agent 服务。

验收标准：

- 每次调用有 trace。
- Prompt 和工具版本可追踪。
- 固定评测集通过率可量化。

## 14. 前端项目中的 Agent UI 设计

Agent UI 和普通 Chat UI 不同。不要只做一个输入框和消息列表。

建议展示：

- 当前阶段：规划中、检索中、执行工具、等待确认、总结中。
- 工具调用：工具名称、参数摘要、执行结果。
- 引用来源：文档链接、代码文件、行号。
- 可干预操作：停止、重试、编辑输入、批准执行。
- 结果结构化：任务摘要、风险点、下一步建议。

示例状态：

```ts
type AgentRunStatus =
  | "idle"
  | "planning"
  | "retrieving"
  | "calling_tool"
  | "waiting_approval"
  | "summarizing"
  | "completed"
  | "failed";
```

前端页面可以按 Agent 事件流渲染：

```ts
type AgentEvent =
  | { type: "message"; content: string }
  | { type: "tool_start"; toolName: string; input: unknown }
  | { type: "tool_end"; toolName: string; output: unknown }
  | { type: "approval_required"; actionId: string; summary: string }
  | { type: "error"; message: string };
```

## 15. 常见误区

### 误区 1：把 Agent 当成大 Prompt

大 Prompt 会越来越难维护。正确做法是拆成：

- Prompt
- State
- Tool
- Node
- Eval
- Trace

### 误区 2：一开始就做全自动

生产环境中，全自动 Agent 风险很高。建议先做：

- 只读工具优先。
- 写操作必须人工确认。
- 高风险操作必须展示 diff 或执行计划。

### 误区 3：只看回答效果，不做评估

Agent 能力必须用测试集衡量。至少维护：

- 典型问题集
- 边界问题集
- 错误输入集
- 历史失败案例

### 误区 4：忽略前端体验

Agent 任务可能耗时很长，用户需要看到过程。Streaming、进度、可取消、可重试都很重要。

## 16. 最小作品集建议

如果你想转 Agent 开发，建议做 3 个能展示工程能力的项目：

1. RAG 知识库问答：证明你会做检索、引用、权限和评估。
2. Tool Calling 助手：证明你会把模型和真实系统连接。
3. LangGraph 工作流 Agent：证明你会处理多步骤任务、状态和恢复。

每个项目都建议包含：

- README：说明问题、架构、运行方式。
- Demo：截图或录屏。
- Eval：至少 10-20 条测试样例。
- Trace：展示一次完整 Agent 运行过程。
- 风险控制：说明权限、重试、超时和人工确认。

## 17. 进阶方向

完成基础项目后，可以继续深入：

- Multi-Agent：多个 Agent 分工协作，例如 Planner、Researcher、Coder、Reviewer。
- Agent Memory：用户偏好、项目上下文、长期知识沉淀。
- Code Agent：代码搜索、编辑、测试、提交。
- Browser Agent：自动浏览网页、填写表单、抓取信息。
- Data Agent：自然语言查数、生成报表、数据分析。
- Evaluation：自动评测 Agent 的准确率、工具选择和任务完成率。
- Guardrails：敏感信息过滤、权限边界、输出校验。

## 18. 建议阅读与实践材料

官方文档：

- LangChain.js 文档：https://js.langchain.com/
- LangGraph.js 文档：https://langchain-ai.github.io/langgraphjs/
- LangSmith 文档：https://docs.smith.langchain.com/

建议关注的主题：

- LangChain Expression Language
- Tool Calling
- Structured Output
- Retrieval-Augmented Generation
- LangGraph StateGraph
- Human-in-the-loop
- Checkpointing
- Evaluation

## 19. 最终路线图

```txt
前端开发基础
  |
  v
LLM 调用与 Prompt
  |
  v
LangChain：Prompt / Model / Parser / Tool / RAG
  |
  v
LangGraph：State / Node / Edge / Loop / Checkpoint
  |
  v
Agent UI：Streaming / Progress / Approval / Trace
  |
  v
生产化：权限 / 日志 / 评估 / 成本 / 稳定性
  |
  v
Agent 开发工程师
```

## 20. 你的下一步行动

建议先做第一个项目：AI 需求拆解助手。

最小功能：

- 一个输入框：粘贴产品需求。
- 一个后端接口：调用 LangChain。
- 一个结构化输出：页面目标、组件拆分、API 依赖、风险点。
- 一个结果页面：按模块展示 JSON。

完成后再扩展：

- 保存历史记录。
- 支持导出 Markdown。
- 接入团队组件库文档做 RAG。
- 用 LangGraph 拆成“需求理解 -> 组件建议 -> API 推断 -> 风险评估”四个节点。

这条路线最适合前端转型，因为它不会脱离你的已有经验，同时能逐步补齐 Agent 开发真正需要的模型、工具、状态机、评估和生产化能力。

## 21. Python 实践仓库补充路线

如果当前目标是尽快达到 Agent 初级开发水平，可以先用 Python 仓库完成一轮实践，再回到 TypeScript / 前端集成。

实践目录：

```txt
python-agent-learning/
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

这些文件对应的能力：

| 文件 | 练习能力 | 前端开发类比 |
| --- | --- | --- |
| `01_cli_chat.py` | 模型调用、消息结构 | 调接口拿响应 |
| `02_requirement_analyzer.py` | 结构化输出、Pydantic schema | 表单 schema / DTO |
| `03_tool_calling.py` | 工具定义、工具执行、错误兜底 | 后端接口调用和错误处理 |
| `04_rag_qa.py` | 本地知识库、检索、上下文拼接 | 搜索接口 + 详情渲染 |
| `05_langgraph_bug_agent.py` | State、Node、条件分支 | 状态机 / 页面流程 |
| `06_agent_api.py` | FastAPI 封装 Agent 服务 | BFF / API Route |
| `07_eval_regression.py` | 固定样例回归 | 单测 / E2E 回归 |
| `08_human_approval_file_writer.py` | 人工确认、安全边界 | 危险操作二次确认 |

### 必须跑通的命令

```bash
cd python-agent-learning
source .venv/bin/activate

python 01_cli_chat.py
python 02_requirement_analyzer.py
python 03_tool_calling.py
python 04_rag_qa.py --no-model "Button 有哪些类型？"
python 05_langgraph_bug_agent.py "点击保存后按钮一直 loading，接口实际已经返回 200。"
python 07_eval_regression.py
pytest -q
```

启动 API：

```bash
python 06_agent_api.py
```

请求 API：

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/rag/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Tool Calling 失败怎么处理？","use_model":false}'
```

人工确认练习：

```bash
python 08_human_approval_file_writer.py
```

### 初级 Agent 开发验收标准

不要以“看懂了”为验收，要以“能独立改出来”为验收：

- 能新增一个结构化输出字段，并让模型稳定返回。
- 能新增一个只读工具，并处理工具执行失败。
- 能在 `data/kb` 新增文档，并让 RAG 检索命中。
- 能给 LangGraph 新增一个节点和一个条件分支。
- 能给 FastAPI 新增一个 Agent 接口。
- 能新增 EvalCase，证明改动没有破坏核心能力。
- 能新增 pytest，覆盖确定性工具逻辑。
- 能解释为什么危险工具必须人工确认。

做到这些后，你已经具备 Agent 初级开发的核心工程基本功：模型调用、结构化输出、工具调用、RAG、状态机、API、评估和安全边界。
