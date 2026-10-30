"""
最小 Agent Loop 技术导读

1. 这个技术是什么
   Agent Loop 是让程序围绕目标反复执行 observe -> think -> act -> observe。
   每一轮只推进一个小步骤，并把中间结果写回状态。

2. 它解决什么问题
   一次性让模型输出完整答案时，很难知道哪一步漏了、错了或需要重试。
   Loop 会把任务拆成多个可观察步骤，方便调试、兜底和后续接入工具。

3. 当前练习做什么
   这里不接 LangGraph，也不接模型服务。
   只用普通 Python 循环模拟一个页面需求分析 Agent：
   - 识别页面目标。
   - 拆组件。
   - 推断状态。
   - 生成风险点。
   - 生成测试点。

4. 为什么不用真实 LLM
   Day 2 的重点是理解 Loop、状态、最大步数和失败返回。
   先把控制流写清楚，再把某些步骤替换成模型或工具会更稳。
"""

# Callable 表示“可调用对象”，这里用来标注每个 step 绑定的处理函数。
# List / Optional 用来把状态字段写得更明确，方便 IDE、Pydantic 和读代码的人理解数据结构。
from typing import Callable, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentTraceStep(BaseModel):
    # Trace 是 Agent 的“执行记录”。
    # 做 Agent 开发时，不能只看最终结果；更重要的是知道每一步看到什么、想做什么、做了什么、产生了什么结果。
    # 后续接入真实模型、工具调用或 Eval 时，trace 会成为定位问题的核心依据。
    step_index: int
    # step_name 用稳定英文名，方便后续做日志检索、Eval 统计或失败归因。
    step_name: str
    # observe 对应 Loop 里的“观察”：当前这一步拿到的输入和上下文。
    observe: str
    # think 对应 Loop 里的“思考”：这一步为什么要这么做。
    think: str
    # act 对应 Loop 里的“行动”：这一步实际执行的动作名称。
    act: str
    # observation 是行动后的新观察结果，也就是这一步写回状态后的摘要。
    observation: str
    # error 为 None 表示步骤成功；有值表示这一步失败，Loop 会提前终止。
    error: Optional[str] = None


class RequirementAgentState(BaseModel):
    # State 是 Agent Loop 的“工作记忆”。
    # 每个步骤不要互相传一堆零散变量，而是统一读写 state。
    # 这样做的好处是：中间结果可观察、可测试、可序列化，也更容易迁移到 LangGraph 这类状态图框架。
    requirement: str
    # page_goal 由第 1 步写入，后续步骤可以基于它继续分析。
    page_goal: str = ""
    # core_components 由第 2 步写入，描述前端可以拆成哪些组件。
    core_components: List[str] = Field(default_factory=list)
    # state_requirements 由第 3 步写入，描述页面需要维护哪些前端状态。
    state_requirements: List[str] = Field(default_factory=list)
    # risk_points 由第 4 步写入，描述实现时最容易出问题的地方。
    risk_points: List[str] = Field(default_factory=list)
    # test_points 由第 5 步写入，描述后续可以如何验证页面行为。
    test_points: List[str] = Field(default_factory=list)
    # trace 保存完整执行过程，不只保存最终答案。
    trace: List[AgentTraceStep] = Field(default_factory=list)
    # errors 保存可读失败原因，避免异常直接把程序打断后丢失上下文。
    errors: List[str] = Field(default_factory=list)


class AgentRunResult(BaseModel):
    # status 用来表达本次 Loop 的最终状态：
    # - completed：所有步骤都完成。
    # - stopped：达到 max_steps，主动提前停止。
    # - failed：某一步异常，提前失败。
    status: str
    # reason 是给人看的结果说明，方便命令行、日志或测试直接判断。
    reason: str
    # steps_used 表示实际跑了几步，用来验证最大步数和提前失败是否生效。
    steps_used: int
    # state 保存最终工作记忆，即使失败也会返回，方便排查失败前已经完成了什么。
    state: RequirementAgentState


class AgentStep(BaseModel):
    # AgentStep 里包含 handler 函数。Pydantic 默认更擅长校验普通数据，
    # 所以这里显式允许 Callable 这种 Python 对象作为字段。
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # name 是稳定步骤名，后续可以用于 trace、统计和测试断言。
    name: str
    # think 是这一步的思考说明。真实 Agent 里这部分可能来自模型推理或规划节点。
    think: str
    # act 是这一步的动作说明。真实 Agent 里这部分可能对应工具调用或函数执行。
    act: str
    # handler 是真正执行这一步的 Python 函数。
    # 它接收同一个 state，并把本步骤的分析结果写回 state。
    handler: Callable[[RequirementAgentState], str]


def unique(items: List[str]) -> List[str]:
    # 去重时保留原始顺序。
    # 这里不用 set，因为 set 会打乱顺序；学习脚本输出稳定，才方便对比和写测试。
    result: List[str] = []
    for item in items:
        # item 为空时跳过；item 已存在时跳过。
        # 这样组件、状态、风险点里不会出现重复项。
        if item and item not in result:
            result.append(item)
    return result


def identify_page_goal(state: RequirementAgentState) -> str:
    # 第 1 步：从自然语言需求里判断页面目标。
    # 当前版本用关键词规则模拟“思考”，后续可以把这里替换成 LLM 结构化输出。
    requirement = state.requirement.strip()
    if not requirement:
        # 失败边界要明确返回，而不是让后续步骤在空输入上继续生成无意义结果。
        raise ValueError("需求为空，无法识别页面目标")

    # 这里是非常轻量的规则分流。
    # Day 2 的重点是 Loop 控制流，不是语义识别准确率，所以先保持简单。
    if "审批" in requirement:
        state.page_goal = "审批工作台，帮助用户查看、筛选并处理审批任务"
    elif "订单" in requirement:
        state.page_goal = "订单管理页，帮助用户检索、查看并处理订单"
    elif "登录" in requirement:
        state.page_goal = "登录页，帮助用户完成身份认证并进入系统"
    elif "上传" in requirement:
        state.page_goal = "上传任务页，帮助用户提交文件并跟踪处理进度"
    elif "看板" in requirement or "图表" in requirement:
        state.page_goal = "数据看板页，帮助用户查看关键指标和趋势"
    else:
        state.page_goal = "业务页面，将自然语言需求转成可执行的前端实现方案"

    return f"页面目标：{state.page_goal}"


def extract_components(state: RequirementAgentState) -> str:
    # 第 2 步：把页面需求拆成前端组件。
    # 组件拆分是前端可执行性的第一层：页面不是一段描述，而是一组可以开发、测试和复用的 UI 单元。
    requirement = state.requirement
    # PageLayout 是所有页面的基础容器，所以先默认加入。
    components = ["PageLayout"]

    # keyword_components 模拟一个最小“本地工具”：
    # 输入是自然语言需求，输出是可能需要的组件名。
    # 后续 Day 3 做工具设计时，可以把这段逻辑拆成 extract_components(requirement) 工具。
    keyword_components = [
        ("搜索", "SearchBar"),
        ("筛选", "FilterPanel"),
        ("分页", "Pagination"),
        ("列表", "DataTable"),
        ("表格", "DataTable"),
        ("批量", "BatchActionBar"),
        ("详情", "DetailDrawer"),
        ("表单", "Form"),
        ("提交", "SubmitButton"),
        ("登录", "LoginForm"),
        ("上传", "UploadArea"),
        ("进度", "ProgressIndicator"),
        ("图表", "ChartPanel"),
        ("看板", "MetricCards"),
        ("导出", "ExportButton"),
        ("角色", "PermissionGuard"),
        ("权限", "PermissionGuard"),
        ("错误", "ErrorAlert"),
        ("失败", "ErrorAlert"),
    ]

    for keyword, component in keyword_components:
        # 命中关键词就加入对应组件。
        # 例如需求里出现“分页”，就说明页面大概率需要 Pagination。
        if keyword in requirement:
            components.append(component)

    if len(components) == 1:
        # 如果没有命中任何具体组件，仍然给一个兜底组件，表示需求需要进一步澄清。
        components.append("RequirementSummary")

    # 写回 state，供后续状态推断和测试点生成使用。
    state.core_components = unique(components)
    return f"组件拆分：{', '.join(state.core_components)}"


def infer_state_requirements(state: RequirementAgentState) -> str:
    # 第 3 步：根据需求和组件推断页面状态。
    # Agent Loop 的关键点是“前一步结果会影响后一步”；这里先直接基于 requirement 做规则推断。
    requirement = state.requirement
    # loading 和 error_message 是大多数前端页面的基础状态。
    states = ["loading", "error_message"]

    # 搜索、筛选、分页、批量选择等交互都会引入额外状态。
    # 把这些状态显式列出，后续开发时才不会遗漏 URL 同步、禁用态、错误态等细节。
    if "搜索" in requirement or "筛选" in requirement:
        states.append("query_params")
    if "分页" in requirement:
        states.append("pagination")
    if "批量" in requirement:
        states.append("selected_row_ids")
    if "详情" in requirement:
        states.append("active_detail_id")
    if "角色" in requirement or "权限" in requirement:
        states.append("current_user_role")
    if "上传" in requirement or "进度" in requirement:
        states.append("upload_progress")
    if "图表" in requirement or "看板" in requirement:
        states.append("metric_filters")

    state.state_requirements = unique(states)
    return f"状态设计：{', '.join(state.state_requirements)}"


def generate_risk_points(state: RequirementAgentState) -> str:
    # 第 4 步：生成实现风险。
    # 风险点不是泛泛提醒，而是要对应到需求里的具体交互、权限或异常场景。
    requirement = state.requirement
    risks = []

    if "角色" in requirement or "权限" in requirement:
        risks.append("不同角色的按钮和数据权限需要前后端一致校验")
    if "批量" in requirement:
        risks.append("批量操作需要处理部分成功、部分失败和重复提交")
    if "搜索" in requirement or "筛选" in requirement or "分页" in requirement:
        risks.append("查询条件、分页和 URL 状态同步容易出现不一致")
    if "失败" in requirement or "错误" in requirement:
        risks.append("接口失败原因需要明确展示，避免只给通用错误")
    if "上传" in requirement:
        risks.append("上传中断、超时和重复上传需要有可恢复策略")
    if "导出" in requirement:
        risks.append("大数据量导出可能超时，需要明确异步任务或分页导出策略")

    if not risks:
        # 如果没有识别到明确风险，不代表没有风险，而是说明需求太粗。
        # 这种情况下要提示补充需求，而不是假装“一切正常”。
        risks.append("需求描述较粗，需要补充接口字段、空状态和异常状态")

    state.risk_points = unique(risks)
    return f"风险点：{'; '.join(state.risk_points)}"


def generate_test_points(state: RequirementAgentState) -> str:
    # 第 5 步：把前面的分析转成测试点。
    # 测试点依赖组件拆分结果，所以这里会读取 state.core_components。
    tests = [
        # 基础测试点覆盖所有页面。
        "首次进入页面时展示 loading，接口成功后展示主体内容",
        "接口失败时展示可理解的错误提示",
    ]

    if "SearchBar" in state.core_components or "FilterPanel" in state.core_components:
        tests.append("搜索或筛选条件变化后，列表按新条件刷新")
    if "Pagination" in state.core_components:
        tests.append("翻页后页码和列表数据保持一致")
    if "BatchActionBar" in state.core_components:
        tests.append("未选择数据时禁用批量操作，选择后允许执行")
    if "PermissionGuard" in state.core_components:
        tests.append("不同角色只能看到自己有权限的操作")
    if "UploadArea" in state.core_components:
        tests.append("上传成功、失败和进度更新都有明确反馈")
    if "DetailDrawer" in state.core_components:
        tests.append("打开详情、关闭详情和详情接口失败都能正确处理")

    state.test_points = unique(tests)
    return f"测试点：{'; '.join(state.test_points)}"


AGENT_STEPS = [
    # AGENT_STEPS 是 Loop 的步骤注册表。
    # 它把“步骤顺序”和“每一步做什么”集中定义，run_agent_loop 只负责按顺序调度。
    # 这种写法比在 run_agent_loop 里硬写 5 个函数调用更容易扩展、调试和测试。
    AgentStep(
        name="identify_page_goal",
        think="先判断页面要帮助用户完成什么目标。",
        act="识别页面目标",
        handler=identify_page_goal,
    ),
    AgentStep(
        name="extract_components",
        think="页面目标确定后，再拆出前端可实现的组件边界。",
        act="拆组件",
        handler=extract_components,
    ),
    AgentStep(
        name="infer_state_requirements",
        think="组件会产生交互状态，需要把状态显式列出来。",
        act="推断状态",
        handler=infer_state_requirements,
    ),
    AgentStep(
        name="generate_risk_points",
        think="状态和交互越多，实现风险越需要提前暴露。",
        act="生成风险点",
        handler=generate_risk_points,
    ),
    AgentStep(
        name="generate_test_points",
        think="最后把目标、组件和风险转成可验证的测试点。",
        act="生成测试点",
        handler=generate_test_points,
    ),
]


def run_agent_loop(requirement: str, max_steps: int = 5) -> AgentRunResult:
    # run_agent_loop 是这个文件的核心：
    # 1. 创建 state。
    # 2. 按 AGENT_STEPS 顺序执行。
    # 3. 每一步写 trace。
    # 4. 失败时返回可读错误。
    # 5. 达到最大步数时主动停止。
    state = RequirementAgentState(requirement=requirement)

    if max_steps <= 0:
        # max_steps 是终止条件的一部分。
        # 真实 Agent 必须有终止条件，否则可能因为模型反复规划或工具反复失败而无限循环。
        reason = "max_steps 必须大于 0"
        state.errors.append(reason)
        return AgentRunResult(status="failed", reason=reason, steps_used=0, state=state)

    for index, step in enumerate(AGENT_STEPS[:max_steps], start=1):
        # observe 表示当前步骤能看到的上下文。
        # 这里为了教学只放原始需求；真实项目里还可以放上一步结果、工具返回、失败摘要等。
        observe = f"当前需求：{state.requirement.strip() or '<空需求>'}"
        try:
            # handler 会执行具体步骤，并把结果写回同一个 state。
            # 例如 extract_components 会写入 state.core_components。
            observation = step.handler(state)
            trace_step = AgentTraceStep(
                step_index=index,
                step_name=step.name,
                observe=observe,
                think=step.think,
                act=step.act,
                observation=observation,
            )
            state.trace.append(trace_step)
        except Exception as error:
            # 单步失败时，不继续执行后续步骤。
            # 因为后续步骤通常依赖前置结果，继续跑只会制造更多无意义输出。
            reason = f"{step.name} 失败：{type(error).__name__}: {error}"
            state.errors.append(reason)
            state.trace.append(
                AgentTraceStep(
                    step_index=index,
                    step_name=step.name,
                    observe=observe,
                    think=step.think,
                    act=step.act,
                    observation="步骤失败，Loop 提前终止",
                    error=reason,
                )
            )
            return AgentRunResult(status="failed", reason=reason, steps_used=index, state=state)

    if len(state.trace) < len(AGENT_STEPS):
        # 跑到这里说明没有异常，但因为 max_steps 小于总步骤数，所以主动停止。
        # 这对应 Agent Loop 里的“最大步数终止条件”。
        return AgentRunResult(
            status="stopped",
            reason=f"达到最大步数 {max_steps}，Loop 提前停止",
            steps_used=len(state.trace),
            state=state,
        )

    return AgentRunResult(
        # 所有步骤都跑完，才算 completed。
        status="completed",
        reason="5 个步骤已完成",
        steps_used=len(state.trace),
        state=state,
    )


SAMPLE_REQUIREMENTS = [
    # 5 条样例覆盖常见页面类型：
    # 列表页、登录页、上传页、数据看板。
    # 这些样例用于观察 Loop 输出，不是严格 Eval；真正 Eval 会在 Day 5 / Day 7 建立。
    "做一个审批列表页，支持搜索、筛选、分页、批量通过、查看审批详情。不同角色看到的操作按钮不同，审批失败需要展示错误原因。",
    "做一个订单列表页，支持按订单号搜索、状态筛选、分页和导出。",
    "做一个登录页，支持手机号验证码登录，失败时展示错误原因。",
    "做一个文件上传页，支持上传进度、失败重试和上传完成后的结果列表。",
    "做一个运营数据看板，展示核心指标卡片、趋势图表和时间筛选。",
]


def main() -> None:
    # 命令行直接运行本文件时，依次跑 5 条固定需求。
    # 输出完整 JSON，方便观察最终 state 和每一步 trace。
    for case_index, requirement in enumerate(SAMPLE_REQUIREMENTS, start=1):
        print(f"\n=== Case {case_index} ===")
        result = run_agent_loop(requirement)
        print(result.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
