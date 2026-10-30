"""Day 6 / Day 10 Demo：准备可重复运行的需求样例。

样例不应该只有“成功案例”，还要覆盖模糊、权限和异常边界。
本 Demo 使用关键词检查器模拟最简单的评估辅助逻辑。
它不是完整语义评估，但能先把成功标准写清楚。

运行：

    .venv/bin/python demos/day06_requirement_cases_demo.py
"""

from dataclasses import dataclass
from typing import List


@dataclass
class RequirementCase:
    # name 便于在失败报告里定位是哪条样例。
    name: str
    # requirement 是交给需求分析 Agent 的原始输入。
    requirement: str
    # required_terms 是结果中必须覆盖的关键语义。
    required_terms: List[str]
    # forbidden_terms 是不能出现的明显错误判断。
    forbidden_terms: List[str]


CASES = [
    RequirementCase(
        name="审批列表正常样例",
        requirement="做一个审批列表页，支持搜索、筛选、分页和查看详情。",
        required_terms=["列表", "搜索", "分页", "详情"],
        forbidden_terms=["不需要错误提示"],
    ),
    RequirementCase(
        name="权限边界样例",
        requirement="管理员可以批量通过，普通用户只能查看自己有权限的记录。",
        required_terms=["管理员", "普通用户", "权限"],
        forbidden_terms=["所有用户都可以批量通过"],
    ),
    RequirementCase(
        name="模糊需求样例",
        requirement="做一个管理页面。",
        required_terms=["信息不足"],
        forbidden_terms=["接口已经明确"],
    ),
    RequirementCase(
        name="上传异常样例",
        requirement="文件上传支持进度、取消和失败重试。",
        required_terms=["进度", "取消", "重试"],
        forbidden_terms=["失败时静默处理"],
    ),
]


def check_text_result(text: str, case: RequirementCase) -> List[str]:
    """返回一条样例的检查问题。"""
    problems: List[str] = []

    # 缺少 required_terms，说明结果可能没有覆盖需求重点。
    for term in case.required_terms:
        if term not in text:
            problems.append(f"缺少关键信息：{term}")

    # 命中 forbidden_terms，说明结果出现了明确错误判断。
    for term in case.forbidden_terms:
        if term in text:
            problems.append(f"出现禁止判断：{term}")

    return problems


def main() -> None:
    # 这里用一个模拟结果演示检查器。
    # 学习时可以把 simulated_output 替换成模型返回的 JSON 文本。
    simulated_outputs = {
        "审批列表正常样例": "输出覆盖列表、搜索、分页和详情。",
        "权限边界样例": "管理员可以批量通过，普通用户需要根据权限查看。",
        "模糊需求样例": "信息不足，需要补充页面角色、接口和异常状态。",
        "上传异常样例": "输出覆盖进度、取消和失败重试。",
    }

    for case in CASES:
        output = simulated_outputs[case.name]
        problems = check_text_result(output, case)
        status = "通过" if not problems else "失败"

        print(f"[{status}] {case.name}")
        for problem in problems:
            print(f"  - {problem}")


if __name__ == "__main__":
    main()
