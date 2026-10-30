"""Day 12 Demo：做跨字段业务校验。

Pydantic 适合验证字段类型和基础约束，
但“组件、状态、风险之间是否匹配”属于业务关系，需要额外代码检查。

运行：

    .venv/bin/python demos/day12_cross_field_validation_demo.py
"""

from typing import List

from pydantic import BaseModel, Field, field_validator


class ValidatedAnalysis(BaseModel):
    # 列表不能为空，列表项也不能是空白字符串。
    core_components: List[str] = Field(min_length=1)
    state_requirements: List[str] = Field(min_length=1)
    risk_points: List[str] = Field(min_length=1)

    @field_validator("core_components", "state_requirements", "risk_points")
    @classmethod
    def items_must_not_be_blank(cls, items: List[str]) -> List[str]:
        """执行所有列表字段共用的基础校验。"""
        if any(not item.strip() for item in items):
            raise ValueError("列表项不能是空字符串")
        return items


def validate_cross_field_rules(analysis: ValidatedAnalysis) -> List[str]:
    """检查多个字段之间的业务关系。"""
    problems: List[str] = []

    # 批量操作必须有“选中了哪些行”的状态，否则前端无法执行操作。
    if "BatchActionBar" in analysis.core_components:
        if "selected_row_ids" not in analysis.state_requirements:
            problems.append("存在批量操作，但缺少 selected_row_ids 状态")

    # 权限组件必须对应权限风险，否则模型可能只分析了按钮展示，
    # 却漏掉了后端数据权限和接口权限。
    if "PermissionGuard" in analysis.core_components:
        if not any("权限" in risk for risk in analysis.risk_points):
            problems.append("存在权限组件，但风险点没有覆盖权限校验")

    return problems


def main() -> None:
    analysis = ValidatedAnalysis(
        core_components=["BatchActionBar", "PermissionGuard"],
        state_requirements=["loading"],
        risk_points=["接口失败需要展示原因"],
    )

    problems = validate_cross_field_rules(analysis)
    print("业务校验结果：")
    if problems:
        for problem in problems:
            print(f"- {problem}")
    else:
        print("- 通过")


if __name__ == "__main__":
    main()
