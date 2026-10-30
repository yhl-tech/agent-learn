"""
Day 3：需求分析 Agent 的本地工具设计 Demo

这个文件接在 09_requirement_agent_loop.py 之后看。

Day 2 的重点：
- handler 直接读取 state。
- handler 直接做分析。
- handler 直接把结果写回 state。

Day 3 的重点：
- tool 只负责一个稳定能力：输入 requirement，输出结构化结果。
- handler 负责调用 tool、检查错误、把结果写回 state。
- tool registry 负责描述工具，让模型或程序知道工具什么时候可用。

Tool Calling 不是简单地“让模型调用函数”，而是把外部能力封装成输入输出明确的工具。
工具调用前需要用 schema 校验参数，调用后要返回结构化结果；
执行过程需要记录 tool name、args、result、error 等 trace 信息。
这样即使模型选错工具、参数缺失或工具执行失败，系统也能通过错误码、失
败兜底和状态记录保持可控、可调试、可追溯。
RequirementToolInput
= 入参结构约束

RequirementToolResult
= 工具结构化返回

run_tool_call
= 工具调度 + 参数校验 + 异常兜底

RequirementToolAgentState
= Agent 工作记忆

ToolTraceStep
= 工具调用过程记录

Tool 是稳定能力单元，Agent 通过 handler 调用工具，把结构化结果写回 state，并用 trace 记录工具名、参数、结果和错误。
"""

from typing import Any, Callable, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError


def unique(items: List[str]) -> List[str]:
    """去重时保留原始顺序，方便输出稳定。"""
    result: List[str] = []
    for item in items:
        if item and item not in result:
            result.append(item)
    return result


class RequirementToolInput(BaseModel):
    # 所有 Day 3 工具先统一只接收自然语言页面需求。
    # 后续可以扩展成 requirement + components + recent_trace。
    requirement: str = Field(description="自然语言页面需求")


class RequirementToolResult(BaseModel):
    # 一个统一结果结构，方便 run_tool_call 做调度和错误处理。
    tool_name: str
    success: bool
    # payload 保存工具真正产出的结构化内容。
    # 例如 extract_components 返回 {"components": [...]}。
    payload: Dict[str, List[str]] = Field(default_factory=dict)
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class RequirementToolSpec(BaseModel):
    # 工具说明不是写给机器看的摆设，而是写给“调度者”看的边界。
    name: str
    when_to_use: str
    input_parameters: Dict[str, str]
    return_structure: Dict[str, str]
    error_codes: List[str]
    example: Dict[str, Any]


class ToolTraceStep(BaseModel):
    # Trace 记录的是工具调用过程，不只是最终答案。
    step_index: int
    step_name: str
    tool_name: str
    tool_args: Dict[str, Any]
    tool_result: RequirementToolResult
    error: Optional[str] = None


class RequirementToolAgentState(BaseModel):
    # State 仍然是 Agent 的工作记忆。
    # 区别是：中间结果来自工具，而不是 handler 自己硬算。
    requirement: str
    core_components: List[str] = Field(default_factory=list)
    state_requirements: List[str] = Field(default_factory=list)
    test_points: List[str] = Field(default_factory=list)
    trace: List[ToolTraceStep] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class AgentRunResult(BaseModel):
    status: str
    reason: str
    steps_used: int
    state: RequirementToolAgentState


class AgentStep(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    tool_name: str
    handler: Callable[[RequirementToolAgentState], RequirementToolResult]


class ToolDispatchResult(BaseModel):
    # run_tool_call 的返回值。
    # 这个结构模拟 03_tool_calling.py 中“模型提出 tool_call 后，程序真正执行工具”的结果。
    tool_name: str
    success: bool
    result: Optional[RequirementToolResult] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None


def build_error_result(tool_name: str, error_code: str, error_message: str) -> RequirementToolResult:
    return RequirementToolResult(
        tool_name=tool_name,
        success=False,
        error_code=error_code,
        error_message=error_message,
    )


def validate_requirement(tool_name: str, requirement: str) -> Optional[RequirementToolResult]:
    if not requirement.strip():
        return build_error_result(tool_name, "EMPTY_REQUIREMENT", "需求为空，无法执行工具")
    return None


def extract_components(requirement: str) -> RequirementToolResult:
    """从页面需求中拆出前端组件。"""
    tool_name = "extract_components"
    error = validate_requirement(tool_name, requirement)
    if error:
        return error

    components = ["PageLayout"]
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
        ("排序", "SortControl")
    ]

    for keyword, component in keyword_components:
        if keyword in requirement:
            components.append(component)

    if len(components) == 1:
        components.append("RequirementSummary")

    return RequirementToolResult(
        tool_name=tool_name,
        success=True,
        payload={"components": unique(components)},
    )


def infer_state(requirement: str) -> RequirementToolResult:
    """从页面需求中推断前端状态。"""
    tool_name = "infer_state"
    error = validate_requirement(tool_name, requirement)
    if error:
        return error

    # 状态字段来自页面中“会变化、要记住、会影响渲染或接口请求”的东西。
    states = ["loading", "error_message"]

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
    if "导出" in requirement:
        states.append("exporting")
    if "排序" in requirement:
        states.append("sort_order")
    return RequirementToolResult(
        tool_name=tool_name,
        success=True,
        payload={"states": unique(states)},
    )


def generate_test_points(requirement: str) -> RequirementToolResult:
    """从页面需求中生成测试点。"""
    tool_name = "generate_test_points"
    error = validate_requirement(tool_name, requirement)
    if error:
        return error

    tests = [
        "首次进入页面时展示 loading，接口成功后展示主体内容",
        "接口失败时展示可理解的错误提示",
    ]

    if "搜索" in requirement or "筛选" in requirement:
        tests.append("搜索或筛选条件变化后，列表按新条件刷新")
    if "分页" in requirement:
        tests.append("翻页后页码和列表数据保持一致")
    if "批量" in requirement:
        tests.append("未选择数据时禁用批量操作，选择后允许执行")
    if "角色" in requirement or "权限" in requirement:
        tests.append("不同角色只能看到自己有权限的操作")
    if "上传" in requirement:
        tests.append("上传成功、失败和进度更新都有明确反馈")
    if "详情" in requirement:
        tests.append("打开详情、关闭详情和详情接口失败都能正确处理")
    if "导出" in requirement:
        tests.append("导出中按钮进入禁用或 loading 状态，避免重复触发")

    return RequirementToolResult(
        tool_name=tool_name,
        success=True,
        payload={"test_points": unique(tests)},
    )


TOOL_REGISTRY = [
    RequirementToolSpec(
        name="extract_components",
        when_to_use="当需要把页面需求拆成前端组件边界时使用。",
        input_parameters={"requirement": "自然语言页面需求，不能为空字符串。"},
        return_structure={"components": "组件名称列表，例如 SearchBar、DataTable。"},
        error_codes=["EMPTY_REQUIREMENT"],
        example={
            "input": {"requirement": "做一个订单列表页，支持搜索、分页和导出。"},
            "output": {"components": ["PageLayout", "SearchBar", "Pagination", "DataTable", "ExportButton"]},
        },
    ),
    RequirementToolSpec(
        name="infer_state",
        when_to_use="当需要根据页面交互推断前端状态字段时使用。",
        input_parameters={"requirement": "自然语言页面需求，不能为空字符串。"},
        return_structure={"states": "状态字段列表，例如 loading、query_params、pagination。"},
        error_codes=["EMPTY_REQUIREMENT"],
        example={
            "input": {"requirement": "做一个订单列表页，支持搜索、分页和导出。"},
            "output": {"states": ["loading", "error_message", "query_params", "pagination", "exporting"]},
        },
    ),
    RequirementToolSpec(
        name="generate_test_points",
        when_to_use="当需要把页面需求转成可验证测试点时使用。",
        input_parameters={"requirement": "自然语言页面需求，不能为空字符串。"},
        return_structure={"test_points": "测试点列表，描述可以验证的页面行为。"},
        error_codes=["EMPTY_REQUIREMENT"],
        example={
            "input": {"requirement": "做一个订单列表页，支持搜索、分页和导出。"},
            "output": {"test_points": ["搜索条件变化后列表刷新", "翻页后页码和列表数据保持一致"]},
        },
    ),
]


TOOL_HANDLERS: Dict[str, Callable[[str], RequirementToolResult]] = {
    "extract_components": extract_components,
    "infer_state": infer_state,
    "generate_test_points": generate_test_points,
}


def run_tool_call(tool_call: Dict[str, Any]) -> ToolDispatchResult:
    # tool_call 可以理解成“模型或程序提出的工具调用请求”。
    # 真正执行工具的是这里的 Python 调度层。
    tool_name = str(tool_call.get("name", ""))
    if tool_name not in TOOL_HANDLERS:
        return ToolDispatchResult(
            tool_name=tool_name or "<missing>",
            success=False,
            error_code="UNKNOWN_TOOL",
            error_message=f"未识别的工具：{tool_name or '<missing>'}",
        )

    try:
        tool_input = RequirementToolInput.model_validate(tool_call.get("args", {}))
    except ValidationError as error:
        return ToolDispatchResult(
            tool_name=tool_name,
            success=False,
            error_code="INVALID_ARGS",
            error_message=f"工具参数不合法：{error}",
        )

    try:
        result = TOOL_HANDLERS[tool_name](tool_input.requirement)
        return ToolDispatchResult(tool_name=tool_name, success=result.success, result=result)
    except Exception as error:
        return ToolDispatchResult(
            tool_name=tool_name,
            success=False,
            error_code="TOOL_EXECUTION_FAILED",
            error_message=f"{type(error).__name__}: {error}",
        )


def handle_extract_components(state: RequirementToolAgentState) -> RequirementToolResult:
    result = extract_components(state.requirement)
    if result.success:
        state.core_components = result.payload["components"]
    return result


def handle_infer_state(state: RequirementToolAgentState) -> RequirementToolResult:
    result = infer_state(state.requirement)
    if result.success:
        state.state_requirements = result.payload["states"]
    return result


def handle_generate_test_points(state: RequirementToolAgentState) -> RequirementToolResult:
    result = generate_test_points(state.requirement)
    if result.success:
        state.test_points = result.payload["test_points"]
    return result


AGENT_STEPS = [
    AgentStep(
        name="extract_components_step",
        tool_name="extract_components",
        handler=handle_extract_components,
    ),
    AgentStep(
        name="infer_state_step",
        tool_name="infer_state",
        handler=handle_infer_state,
    ),
    AgentStep(
        name="generate_test_points_step",
        tool_name="generate_test_points",
        handler=handle_generate_test_points,
    ),
]


FAILURE_TOOL_CALLS = [
    {
        "name": "extract_components",
        "args": {"requirement": ""},
    },
    {
        "name": "infer_state",
        "args": {},
    },
    {
        "name": "unknown_tool",
        "args": {"requirement": "做一个订单列表页，支持搜索和分页。"},
    },
]


def run_requirement_tool_agent(requirement: str, max_steps: int = 3) -> AgentRunResult:
    state = RequirementToolAgentState(requirement=requirement)

    if max_steps <= 0:
        reason = "max_steps 必须大于 0"
        state.errors.append(reason)
        return AgentRunResult(status="failed", reason=reason, steps_used=0, state=state)

    for index, step in enumerate(AGENT_STEPS[:max_steps], start=1):
        result = step.handler(state)
        error = None
        if not result.success:
            error = f"{result.error_code}: {result.error_message}"
            state.errors.append(error)

        state.trace.append(
            ToolTraceStep(
                step_index=index,
                step_name=step.name,
                tool_name=step.tool_name,
                tool_args={"requirement": requirement},
                tool_result=result,
                error=error,
            )
        )

        if error:
            return AgentRunResult(status="failed", reason=error, steps_used=index, state=state)

    if len(state.trace) < len(AGENT_STEPS):
        return AgentRunResult(
            status="stopped",
            reason=f"达到最大步数 {max_steps}，工具 Agent 提前停止",
            steps_used=len(state.trace),
            state=state,
        )

    return AgentRunResult(
        status="completed",
        reason="3 个本地工具已完成",
        steps_used=len(state.trace),
        state=state,
    )


def main() -> None:
    requirement = "做一个订单列表页，支持按订单号搜索、状态筛选、分页和导出。"

    print("工具注册表：")
    for tool_spec in TOOL_REGISTRY:
        print(tool_spec.model_dump_json(indent=2, ensure_ascii=False))

    print("\n工具 Agent 执行结果：")
    result = run_requirement_tool_agent(requirement)
    print(result.model_dump_json(indent=2, ensure_ascii=False))

    print("\n工具调用失败样例：")
    for tool_call in FAILURE_TOOL_CALLS:
        dispatch_result = run_tool_call(tool_call)
        print(dispatch_result.model_dump_json(indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
