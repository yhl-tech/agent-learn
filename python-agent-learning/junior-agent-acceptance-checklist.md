# Agent 开发初级开发 14 天验收表

> 使用方式：完成 14 天练习后，逐项自测。不要只看“能不能跑”，重点看是否能独立解释、修改、验证。

## 初级验收线总表

| 序号 | 验收能力 | 对应练习文件 | 你要能独立完成什么 | 自测方式 | 达标标准 | 是否达标 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Chat Model 基础调用 | `01_cli_chat.py` | 调用模型，理解 `system`、`human`、`response.content`、`temperature` | 修改 Prompt 和 temperature 后重新运行 | 能解释不同消息角色的作用，并说明 temperature 如何影响稳定性 | ⬜ |
| 2 | Pydantic 结构化输出 | `02_requirement_analyzer.py` | 定义输出 schema，并让模型按结构返回结果 | 新增 `acceptance_criteria` 字段并运行脚本 | 输出结果包含新增字段，且能用 Python 对象继续处理 | ⬜ |
| 3 | LangChain Tool 定义 | `03_tool_calling.py` | 使用 `@tool` 和 `args_schema` 定义工具 | 新增一个只读工具，例如 `read_project_readme` | 能看到模型返回 `tool_calls`，并能用 `.invoke()` 执行工具 | ⬜ |
| 4 | 工具失败处理 | `03_tool_calling.py` | 给工具调用加错误兜底 | 手动构造缺字段或类型错误的 `tool_call["args"]` | 程序不崩溃，能返回错误类型和错误信息 | ⬜ |
| 5 | RAG 基础流程 | `04_rag_qa.py`、`data/kb/*.md` | 读取本地文档，切 chunk，检索上下文，输出来源 | 执行 `python 04_rag_qa.py --no-model "Button 有哪些类型？"` | 能解释 Document、chunk、retrieval、context、answer 的关系 | ⬜ |
| 6 | RAG 文档扩展 | `data/kb/*.md`、`04_rag_qa.py` | 新增知识库文档，并让问题命中新文档 | 新增 Markdown 后提问验证 | 检索结果包含新文档来源，且上下文内容相关 | ⬜ |
| 7 | LangGraph 状态流转 | `05_langgraph_bug_agent.py` | 定义 State、Node、Edge 和条件分支 | 分别输入短 Bug 和完整 Bug 描述 | 短输入会追问，完整输入会进入分析流程 | ⬜ |
| 8 | LangGraph 流程改造 | `05_langgraph_bug_agent.py` | 新增一个节点和一个条件分支 | 新增 `classify_severity` 或类似节点 | 图中至少 4 个节点，且有清晰条件路由 | ⬜ |
| 9 | FastAPI Agent 服务 | `06_agent_api.py` | 把 Agent 能力封装成 HTTP API | 运行服务并请求 `/health`、`/rag/ask` | curl 能拿到结构化响应，包含 answer、sources、used_model | ⬜ |
| 10 | API 扩展能力 | `06_agent_api.py`、`05_langgraph_bug_agent.py` | 新增一个 Agent API，例如 `/bug/analyze` | 用 curl 传入 Bug 描述 | API 能调用 LangGraph，并返回分析结果 | ⬜ |
| 11 | Eval 回归评估 | `07_eval_regression.py` | 用固定样例验证 RAG 检索质量 | 新增 2 个 `EvalCase` 后运行脚本 | Eval 全部通过；改坏检索逻辑时 Eval 能失败 | ⬜ |
| 12 | pytest 确定性测试 | `tests/test_learning_scripts.py` | 给确定性逻辑写单测 | 执行 `pytest -q` | 测试通过，且至少覆盖一个你新增或修改的函数 | ⬜ |
| 13 | 人工确认机制 | `08_human_approval_file_writer.py` | 实现“先生成草稿，再人工确认，再执行” | 分别输入 `yes` 和非 `yes` | 非 `yes` 不写入；`yes` 后才写入文件 | ⬜ |
| 14 | 工具权限边界 | `08_human_approval_file_writer.py` | 限制危险工具的执行范围 | 构造 `../danger.txt` 之类路径 | 路径越界会被拦截，只允许写入 `generated` 目录 | ⬜ |
| 15 | 综合小项目整合 | 全部练习文件 | 串联“需求分析 -> 文件计划 -> RAG 查询 -> API 输出” | 自己实现一个最小 Agent 流程 | 能独立讲清架构、数据流、工具边界和验证方式 | ⬜ |

## 必须跑通的命令

```bash
cd /Users/bytedance/Desktop/code/agent/python-agent-learning
source .venv/bin/activate

python 01_cli_chat.py
python 02_requirement_analyzer.py
python 03_tool_calling.py
python 04_rag_qa.py --no-model "Button 有哪些类型？"
python 05_langgraph_bug_agent.py "点击保存后按钮一直 loading，接口实际已经返回 200。"
python 07_eval_regression.py
pytest -q
```

启动 API 服务：

```bash
python 06_agent_api.py
```

另开终端验证 API：

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/rag/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"Tool Calling 失败怎么处理？","use_model":false}'
```

## 评分建议

| 通过项数量 | 水平判断 | 下一步 |
| --- | --- | --- |
| 0-5 项 | 仍处在 Demo 跑通阶段 | 回到基础脚本，逐行理解代码 |
| 6-10 项 | 已掌握部分 Agent 基础能力 | 重点补 Tool、RAG、LangGraph 的改造练习 |
| 11-14 项 | 接近初级 Agent 开发水平 | 开始做一个完整小项目 |
| 15 项 | 达到初级 Agent 开发入门线 | 可以尝试接入真实业务文档、真实 API 和前端页面 |

## 最终达标口径

你不是只要“看懂代码”，而是要能做到：

- 独立定义结构化输出 schema。
- 独立定义并执行 LangChain Tool。
- 能处理工具参数错误和执行失败。
- 能实现带来源的只读 RAG。
- 能用 LangGraph 管理多步骤 Agent 流程。
- 能用 FastAPI 暴露 Agent 服务。
- 能用 Eval 和 pytest 验证核心能力。
- 能给写文件、执行命令等危险操作加人工确认和权限边界。
