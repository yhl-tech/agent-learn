"""Day 9 Demo：使用嵌套 Pydantic 模型和 model_validate。

嵌套模型用于表达“一个需求计划包含多个组件，每个组件又有名称和职责”。
这样比 List[str] 更明确，也方便后续给组件增加 owner、依赖或测试点。

运行：

    .venv/bin/python demos/day09_nested_model_demo.py
"""

from typing import List

from pydantic import BaseModel, Field, ValidationError


class ComponentPlan(BaseModel):
    # name 是组件名称，例如 DataTable。
    name: str = Field(description="组件名称")
    # responsibility 说明组件负责什么，避免只得到一个无法执行的名称。
    responsibility: str = Field(description="组件职责")


class RequirementPlan(BaseModel):
    # page_type 描述整体页面类别。
    page_type: str
    # 至少需要一个组件，否则这个计划没有可执行内容。
    components: List[ComponentPlan] = Field(min_length=1)


def main() -> None:
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
        # model_validate 会校验外部字典，并递归校验 components。
        plan = RequirementPlan.model_validate(raw_payload)
    except ValidationError as error:
        print("输入不符合 RequirementPlan：")
        print(error)
        return

    # 通过校验后可以使用属性访问，
    # 不需要在业务代码里到处判断字典键是否存在。
    print(f"页面类型：{plan.page_type}")
    for component in plan.components:
        print(f"- {component.name}：{component.responsibility}")

    # 演示一个缺少嵌套字段的错误输入。
    invalid_payload = {
        "page_type": "审批列表页",
        "components": [{"name": "DataTable"}],
    }

    try:
        RequirementPlan.model_validate(invalid_payload)
    except ValidationError as error:
        print("\n错误输入被拦截：")
        print(error)


if __name__ == "__main__":
    main()
