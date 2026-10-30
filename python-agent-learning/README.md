# Python Agent Learning

这个目录用于按 Python 路线学习 LangChain / LangGraph。目标不是只看 Demo，而是通过可运行脚本补齐初级 Agent 开发必须掌握的主链路：

1. LLM 调用与 Prompt：`01_cli_chat.py`
2. Pydantic 结构化输出：`02_requirement_analyzer.py`
3. Tool Calling：`03_tool_calling.py`
4. RAG 本地知识库问答：`04_rag_qa.py`
5. LangGraph 状态机 Agent：`05_langgraph_bug_agent.py`
6. FastAPI Agent 服务：`06_agent_api.py`
7. Eval 回归评估：`07_eval_regression.py`
8. 人工确认写文件：`08_human_approval_file_writer.py`
9. 手写最小 Agent Loop：`09_requirement_agent_loop.py`
10. 工具化需求 Agent：`10_requirement_tool_agent.py`

前 15 天的配套小 Demo 位于 `demos/`：

- `day01_task_boundary_demo.py`：判断 Chatbot、Workflow、Agent 边界。
- `day04_schema_design_demo.py`：设计结构化需求字段。
- `day05_output_validation_demo.py`：区分结构校验和业务校验。
- `day06_requirement_cases_demo.py`：准备需求样例和检查规则。
- `day07_week_review_demo.py`：生成第一周复盘摘要。
- `day09_nested_model_demo.py`：练习嵌套 Pydantic 模型。
- `day11_quality_score_demo.py`：对结构化输出做人工质量评分。
- `day12_cross_field_validation_demo.py`：执行跨字段业务校验。
- `day13_layered_validation_demo.py`：练习分层校验。
- `day15_tool_dispatch_demo.py`：演示 Tool Calling 请求和程序执行的边界。

## 当前环境

当前项目使用 pyenv 管理 Python 版本：

```bash
pyenv local 3.11.9
python --version
# Python 3.11.9
```

项目虚拟环境位置：

```bash
python-agent-learning/.venv
```

已安装核心依赖：

```txt
langchain==0.3.30
langchain-core==0.3.86
langchain-text-splitters==0.3.11
langchain-openai==0.3.35
langgraph==0.6.11
pydantic==2.13.4
python-dotenv==1.2.1
fastapi==0.124.2
uvicorn==0.38.0
pytest==9.0.2
urllib3==1.26.20
```

当前 Python 3.11.9 是通过 pyenv 编译安装的。核心模块和 OpenSSL 正常：

```txt
OpenSSL 3.2.1
```

已知限制：当前编译环境缺少 xz/lzma 开发库，所以 Python 的 `_lzma` 扩展未编译。前三阶段 LangChain / LangGraph 学习不依赖它；如果后续要处理 `.xz` / lzma 压缩文件，需要补齐 xz 后重新编译 Python。

## 使用方式

进入项目：

```bash
cd python-agent-learning
source .venv/bin/activate
```

配置模型 Key：

```bash
cp .env.example .env
```

然后在 `.env` 中填写：

```bash
OPENAI_API_KEY=你的模型服务 Key
```

如果使用兼容 OpenAI 协议的内部模型服务，可以同时配置：

```bash
OPENAI_BASE_URL=https://your-compatible-endpoint/v1
```

运行示例：

```bash
python 01_cli_chat.py
python 02_requirement_analyzer.py
python 03_tool_calling.py
python 04_rag_qa.py --no-model "Button 有哪些类型？"
python 05_langgraph_bug_agent.py "点击保存后按钮一直 loading，接口实际已经返回 200。"
python 07_eval_regression.py
python 09_requirement_agent_loop.py
pytest -q
```

## 学习顺序

先跑通 `01_cli_chat.py`，确认模型服务可用。

再看 `02_requirement_analyzer.py`，重点理解 `pydantic` schema 如何把模型输出约束成可被程序消费的数据。

最后看 `03_tool_calling.py`，重点理解工具 schema、模型返回的 `tool_calls`、以及如何把工具调用结果交回程序。

## 初级 Agent 开发练习路线

### 第 1 天：模型调用和结构化输出

目标：

- 能解释 `system`、`human`、`response.content`。
- 能用 Pydantic 定义模型输出结构。
- 能把模型输出当成 Python 对象继续处理。

命令：

```bash
python 01_cli_chat.py
python 02_requirement_analyzer.py
```

验收：

- 修改需求文本后，`02_requirement_analyzer.py` 仍能稳定输出结构化 JSON。
- 给 `RequirementAnalysis` 增加一个字段，例如 `acceptance_criteria`，并让输出包含它。

### 第 2 天：Tool Calling

目标：

- 能解释 `@tool`、`args_schema`、`response.tool_calls`、`.invoke()`。
- 能处理工具执行失败，不让程序直接崩溃。
- 能区分“模型生成工具调用请求”和“Python 真正执行工具”。

命令：

```bash
python 03_tool_calling.py
```

验收：

- 手动构造一个缺少字段的 `tool_call["args"]`，观察 `try/except` 返回的错误信息。
- 增加一个只读工具，例如 `read_project_readme`，返回 README 摘要。

### 第 3 天：RAG

目标：

- 能说清楚 `Document`、chunk、retrieval、context、answer 的关系。
- 能先用本地关键词检索跑通 RAG 流程。
- 能把本地 Markdown 文档作为知识库来源。

命令：

```bash
python 04_rag_qa.py --no-model "表单提交前要做什么？"
python 04_rag_qa.py --no-model "Agent UI 为什么需要 waiting_approval？"
```

验收：

- 在 `data/kb` 新增一篇 Markdown 文档。
- 新增一个问题，能检索到你刚加的文档。

### 第 4 天：LangGraph

目标：

- 能定义 `State`。
- 能拆分 `Node`。
- 能用 `add_conditional_edges` 做条件分支。
- 能解释为什么多步骤 Agent 不应该写成一个超长函数。

命令：

```bash
python 05_langgraph_bug_agent.py "保存失败"
python 05_langgraph_bug_agent.py "点击保存后按钮一直 loading，接口实际已经返回 200。"
```

验收：

- 输入很短时，Agent 会先追问。
- 输入足够时，Agent 会走分析、命令建议、总结流程。

### 第 5 天：API 服务

目标：

- 能把 Agent 能力封装成 HTTP API。
- 能设计请求和响应 schema。
- 能让前端或 curl 调用 Agent 服务。

命令：

```bash
python 06_agent_api.py
```

另开终端：

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/rag/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Tool Calling 失败怎么处理？","use_model":false}'
```

验收：

- `/health` 能返回服务状态。
- `/rag/ask` 能返回答案、来源和是否调用模型。

### 第 6 天：Eval 回归

目标：

- 能理解 Agent 不能只靠肉眼试用。
- 能用固定样例评估检索命中率。
- 能在修改检索逻辑后跑回归，防止能力退化。

命令：

```bash
python 07_eval_regression.py
pytest -q
```

验收：

- 所有样例通过。
- 新增 2 个 `EvalCase`，覆盖你新增的知识库文档。
- 至少新增 1 条 pytest，覆盖你改动过的确定性逻辑。

### 第 7 天：人工确认和安全边界

目标：

- 能解释为什么写文件、删文件、执行命令必须人工确认。
- 能限制工具写入目录，避免路径越界。
- 能做“先生成草稿，再确认执行”的流程。

命令：

```bash
python 08_human_approval_file_writer.py
```

验收：

- 输入非 `yes` 时不会写入文件。
- 输入 `yes` 后只会写入 `generated` 目录。

## 初级 Agent 开发最低验收标准

你至少要能独立完成：

- 定义一个 Pydantic schema，并让模型按 schema 输出。
- 定义一个 LangChain tool，并处理参数校验失败。
- 实现一个只读 RAG 问答流程，并返回引用来源。
- 用 LangGraph 拆出至少 3 个节点和 1 个条件分支。
- 用 FastAPI 暴露一个 Agent 接口。
- 写一个最小 Eval 脚本，保证核心场景不退化。
- 给危险操作加人工确认和目录权限边界。
