"""Day 11 Demo：对结构化输出做人工质量评分。

结构化字段全部存在，不代表结果一定好。
这里从完整性、相关性、可执行性、风险意识四个维度打分，
把“感觉不错”变成可讨论、可记录的结果。

运行：

    .venv/bin/python demos/day11_quality_score_demo.py
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class QualityScore:
    # 每个维度使用 0-2 分：
    # 0 = 没覆盖，1 = 部分覆盖，2 = 覆盖且具体。
    completeness: int
    relevance: int
    executability: int
    risk_awareness: int

    def total(self) -> int:
        # 总分用于快速比较多个 Prompt 或模型版本的结果。
        return (
            self.completeness
            + self.relevance
            + self.executability
            + self.risk_awareness
        )


def grade_output(score: QualityScore) -> Dict[str, object]:
    """把人工评分整理成可保存的字典。"""
    total = score.total()

    # 阈值只是学习阶段约定。
    # 真实项目需要用更多标注样例校准阈值，不能直接照搬。
    if total >= 7:
        level = "可继续使用"
    elif total >= 4:
        level = "需要人工修改"
    else:
        level = "不合格"

    return {
        "total": total,
        "level": level,
        "dimensions": {
            "completeness": score.completeness,
            "relevance": score.relevance,
            "executability": score.executability,
            "risk_awareness": score.risk_awareness,
        },
    }


def main() -> None:
    result = grade_output(
        QualityScore(
            completeness=2,
            relevance=2,
            executability=1,
            risk_awareness=1,
        )
    )
    print(result)


if __name__ == "__main__":
    main()
