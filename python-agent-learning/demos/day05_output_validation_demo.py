"""Day 5 Demo：区分结构校验和业务校验。

模型输出可能有三种问题：

1. 解析或类型错误：例如 core_components 不是列表。
2. 结构错误：列表存在，但为空或包含空字符串。
3. 业务语义错误：字段都存在，但组件、状态和风险之间互相矛盾。

运行：

    .venv/bin/python demos/day05_output_validation_demo.py
"""

from typing import List

from pydantic import BaseModel, Field, ValidationError


class CheckedAnalysis(BaseModel):
    # Pydantic 负责检查类型和基础结构。
    page_type: str
    core_components: List[str] = Field(min_length=1)
    test_points: List[str] = Field(min_length=1)


def validate_business_result(result: CheckedAnalysis) -> List[str]:
    """执行 Pydantic 之外的业务校验。"""
    problems: List[str] = []

    # 类型是 str 不代表内容可用，空字符串仍然需要拦截。
    if not result.page_type.strip():
        problems.append("page_type 不能为空")

    # 列表本身可能非空，但其中某一项仍然可能是空字符串。
    if any(not component.strip() for component in result.core_components):
        problems.append("core_components 不能包含空名称")

    # 测试点太短时通常无法直接用于验收。
    if any(len(test_point.strip()) < 4 for test_point in result.test_points):
        problems.append("test_points 中存在过于简略的描述")

    return problems


def validate_payload(payload: object) -> None:
    print("输入：", payload)

    try:
        # model_validate 负责把外部字典转换成受约束的模型实例。
        # 如果字段类型错误，程序会在这里停止，不把脏数据继续传下去。
        result = CheckedAnalysis.model_validate(payload)
    except ValidationError as error:
        print("结构校验失败：")
        print(error)
        print()
        return

    # 能通过 Pydantic，只能说明结构合法；
    # 还需要继续检查业务语义是否可以被下游使用。
    problems = validate_business_result(result)
    if problems:
        print("业务校验失败：")
        for problem in problems:
            print(f"- {problem}")
    else:
        print("校验通过：", result.model_dump())
    print()


def main() -> None:
    # 结构错误：core_components 的类型不是列表。
    validate_payload(
        {
            "page_type": "列表页",
            "core_components": "DataTable",
            "test_points": ["接口成功后展示列表"],
        }
    )

    # 业务错误：结构合法，但测试点为空字符串。
    validate_payload(
        {
            "page_type": "列表页",
            "core_components": ["DataTable"],
            "test_points": [""],
        }
    )

    # 完整正确的输入。
    validate_payload(
        {
            "page_type": "列表页",
            "core_components": ["DataTable"],
            "test_points": ["接口成功后展示列表"],
        }
    )


if __name__ == "__main__":
    main()
