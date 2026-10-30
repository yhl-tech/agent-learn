"""Day 7 Demo：把结构化输出检查结果整理成复盘摘要。

Day 7 的重点是复盘，不是继续堆功能。
这个 Demo 将样例覆盖情况整理成一份可读报告，帮助发现：

- 哪些关键字段经常漏。
- 哪些需求边界还没有覆盖。
- 下一周应该优先补什么。

运行：

    .venv/bin/python demos/day07_week_review_demo.py
"""

from dataclasses import dataclass
from typing import List


@dataclass
class CaseReview:
    # name 是样例名称。
    name: str
    # missing_terms 保存结果中缺少的关键语义。
    missing_terms: List[str]


def build_review_report(reviews: List[CaseReview]) -> str:
    """根据样例复盘结果生成 Markdown 文本。"""
    lines = ["# 第 1 周结构化输出复盘", ""]

    # 逐条列出样例结果，避免只保留一个总通过率而丢失失败细节。
    for review in reviews:
        if review.missing_terms:
            missing = "、".join(review.missing_terms)
            lines.append(f"- {review.name}：缺少 {missing}")
        else:
            lines.append(f"- {review.name}：通过")

    # 统计所有缺失字段，帮助确定下一周的学习重点。
    missing_count: dict[str, int] = {}
    for review in reviews:
        for term in review.missing_terms:
            missing_count[term] = missing_count.get(term, 0) + 1

    lines.append("")
    lines.append("## 高频缺口")
    if missing_count:
        for term, count in sorted(
            missing_count.items(),
            key=lambda item: (-item[1], item[0]),
        ):
            lines.append(f"- {term}：{count} 条样例缺失")
    else:
        lines.append("- 暂未发现缺口")

    return "\n".join(lines)


def main() -> None:
    reviews = [
        CaseReview("审批列表", []),
        CaseReview("权限边界", ["普通用户权限"]),
        CaseReview("模糊需求", ["信息不足"]),
        CaseReview("上传异常", ["失败重试"]),
    ]
    print(build_review_report(reviews))


if __name__ == "__main__":
    main()
