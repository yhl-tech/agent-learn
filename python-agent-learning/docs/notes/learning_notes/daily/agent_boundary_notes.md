# 页面需求分析 Agent 边界笔记

## 当前目标

基于 `02_requirement_analyzer.py`，构建一个页面需求分析 Agent 的最小起点。

它当前要解决的问题是：

> 把自然语言页面需求拆成前端可执行的结构化信息。

当前不是要做完整 Agent，而是先确认项目边界：输入是什么、输出是什么、哪些事情暂时不做、失败时如何识别。

## 输入

输入是一段自然语言页面需求，例如：

```text
做一个审批列表页，支持搜索、筛选、分页、批量通过、查看审批详情。
不同角色看到的操作按钮不同，审批失败需要展示错误原因。
```

真实项目中，输入可以来自：

- 产品需求描述。
- PRD 片段。
- 设计稿说明。
- 用户口述的页面目标。

## 输出

当前输出由 `RequirementAnalysis` 约束，是一个 Pydantic 结构化对象。

字段包括：

- `page_goal`：页面目标。
- `user_roles`：用户角色。
- `core_interactions`：核心交互。
- `api_dependencies`：可能依赖的 API。
- `component_plan`：建议拆分的前端组件。
- `state_design`：前端状态设计建议。
- `risk_points`：实现风险。
- `test_cases`：建议补充的测试用例。

当前输出的价值是让模型结果能继续被程序消费，而不是只生成一段自然语言建议。

## 为什么不是普通 Workflow

如果只是固定字段提取，普通 Workflow 足够。

这个方向需要 Agent 的原因是：

- 页面需求可能不完整，需要先识别缺失信息。
- 不同页面类型需要不同拆解策略。
- 后续会接入工具，例如组件拆分、状态推断、测试点生成。
- 后续需要根据工具结果继续修正分析结果。
- 后续需要 trace 和 eval 判断每一步是否可靠。

因此当前阶段先做结构化输出，后续再逐步演进到 Agent Loop。

## 当前最小流程

```text
自然语言页面需求
  -> RequirementAnalysis schema
  -> 模型结构化输出
  -> Pydantic 对象
  -> JSON 结果
```

当前 `02_requirement_analyzer.py` 还没有：

- 工具调用。
- 多步 Agent Loop。
- 上下文模板分层。
- trace 日志。
- eval case。
- 人工确认。

## 工具边界

Day 1 暂时不接工具。

后续可扩展的工具包括：

- `extract_components(requirement)`：拆分组件。
- `infer_state(requirement)`：推断前端状态。
- `generate_test_points(requirement)`：生成测试点。

这些工具应保持只读，不做文件写入、网络请求或真实业务变更。

## 失败边界

当前已知失败类型：

1. 字段缺失。
2. 字段内容太泛，无法指导开发。
3. 组件拆分不符合实际前端实现。
4. 状态设计遗漏 loading、error、empty、permission 等场景。
5. 测试点只停留在泛泛描述。
6. 模型调用失败。
7. 本地网络或证书配置失败。

## 当前运行结果

执行命令：

```bash
source .venv/bin/activate && python 02_requirement_analyzer.py
```

结果：

```text
openai.APIConnectionError: Connection error.
CERTIFICATE_VERIFY_FAILED: certificate verify failed: unable to get local issuer certificate
```

说明：

- 代码已经进入模型调用阶段。
- 当前失败不是业务逻辑失败，而是本地 SSL 证书校验或代理链路问题。
- Day 1 的边界梳理可以继续推进。
- 后续要真正跑通模型调用，需要单独处理证书、代理或模型服务配置。

## Day 1 结论

`02_requirement_analyzer.py` 当前适合作为页面需求分析 Agent 的起点。

现阶段项目边界应保持克制：

- 先做好结构化输出。
- 不急着接 LangGraph。
- 不急着做多 Agent。
- 不急着接 MCP。
- 先确认字段设计是否能真实服务前端开发。

下一步进入 Day 2：

> 手写一个最小 Agent Loop，把页面需求分析拆成 5 个明确步骤，并为每一步记录可读失败原因。
