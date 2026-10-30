"""Day 4 / Day 8 Demo：设计页面需求分析的结构化字段。

这个 Demo 不调用模型，先用一个 Pydantic 模型把字段职责固定下来。
这样做的目的，是先确定“程序需要什么数据”，再让模型去填这些数据。

运行：

    .venv/bin/python demos/day04_schema_design_demo.py
"""

from typing import List

from pydantic import BaseModel, Field


class RequirementAnalysis(BaseModel):
    # page_type 影响页面模板和常见交互。
    # 例如列表页通常需要分页，表单页通常需要提交状态。
    page_type: str = Field(
        description="页面类型，例如列表页、详情页、表单页、看板页"
    )

    # target_users 会影响按钮展示、数据范围和权限校验。
    target_users: List[str] = Field(
        description="可以使用该页面的用户角色列表"
    )

    # 组件边界要能直接转成前端开发任务，
    # 因此不使用一个很长的 analysis 字符串代替。
    core_components: List[str] = Field(
        description="可独立开发和测试的前端组件列表"
    )

    # 这里描述页面中会变化、需要保存或驱动渲染的状态。
    state_requirements: List[str] = Field(
        description="页面需要维护的状态字段列表"
    )

    # 明确写“假设”，提醒下游：这些内容不能替代真实接口文档。
    api_assumptions: List[str] = Field(
        description="根据需求推断的接口和字段假设"
    )

    risk_points: List[str] = Field(
        description="权限、异常、并发和交互一致性风险"
    )

    test_points: List[str] = Field(
        description="可以用于验收页面行为的测试点列表"
    )


def main() -> None:
    # 这里模拟经过模型结构化输出后的数据。
    # 在 02_requirement_analyzer.py 中，这些字段由模型填写。
    result = RequirementAnalysis(
        page_type="审批列表页",
        target_users=["管理员", "普通审批人"],
        core_components=["SearchBar", "FilterPanel", "DataTable", "Pagination"],
        state_requirements=["query_params", "pagination", "loading"],
        api_assumptions=["GET /approvals 支持 status 和 page 参数"],
        risk_points=["前后端权限判断必须一致"],
        test_points=["无权限用户不能看到批量通过按钮"],
    )

    # model_dump_json 适合把模型对象输出成 JSON，
    # 便于保存、传给 API 或交给后续程序处理。
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
