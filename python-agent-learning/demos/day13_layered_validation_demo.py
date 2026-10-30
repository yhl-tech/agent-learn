"""Day 13 / Day 14 Demo：分层处理模型输出。

完整链路：

    外部数据
      -> Pydantic 结构校验
      -> 业务语义校验
      -> 下游流程

只有通过前两层校验的数据，才允许进入后续工具或状态更新。

运行：

    .venv/bin/python demos/day13_layered_validation_demo.py
"""

from typing import Any, Dict, List

from pydantic import BaseModel, ValidationError


class SimpleAnalysis(BaseModel):
    # 这些字段代表下游程序真正需要的最小结构。
    page_type: str
    components: List[str]


def parse_and_validate(raw_data: Dict[str, Any]) -> SimpleAnalysis:
    """完成结构校验和最小业务校验。"""
    try:
        # 第一层：把外部字典转换成受约束的 Pydantic 对象。
        analysis = SimpleAnalysis.model_validate(raw_data)
    except ValidationError as error:
        # 不合法的数据不能继续交给下游工具，
        # 否则错误会在更晚的地方爆炸，排查成本更高。
        raise ValueError(f"模型输出结构不合法：{error}") from error

    # 第二层：类型正确不代表业务内容可用。
    if not analysis.page_type.strip():
        raise ValueError("模型输出缺少有效 page_type")
    if not analysis.components:
        raise ValueError("模型输出没有任何组件")

    # 通过两层校验后，才把结果交给下游流程。
    return analysis


def main() -> None:
    payloads = [
        {
            "page_type": "列表页",
            "components": ["DataTable"],
        },
        {
            "page_type": "",
            "components": ["DataTable"],
        },
        {
            "page_type": "列表页",
            "components": "DataTable",
        },
    ]

    for index, payload in enumerate(payloads, start=1):
        try:
            result = parse_and_validate(payload)
        except ValueError as error:
            print(f"[样例 {index}] 失败：{error}")
        else:
            print(f"[样例 {index}] 通过：{result.model_dump()}")


if __name__ == "__main__":
    main()
