"""Day 1 Demo：区分 Chatbot、Workflow 和 Agent。

这个 Demo 不调用模型，故意使用确定性规则。
Day 1 的重点不是让模型做分类，而是建立一个工程判断：

- 只是问答或解释时，Chatbot 通常够用。
- 步骤固定时，Workflow 通常更稳定。
- 需要根据中间结果动态选择下一步时，才考虑 Agent。

运行：

    .venv/bin/python demos/day01_task_boundary_demo.py
"""

from typing import Literal


# Literal 限制返回值只能是这三个固定字符串。
# 在 Agent 状态和路由代码中，固定取值可以减少拼写错误和非法分支。
TaskType = Literal["chatbot", "workflow", "agent"]


def classify_task(task: str) -> TaskType:
    """根据任务描述做一个粗粒度判断。

    这不是生产级意图分类器，只用于帮助学习者练习边界判断。
    """
    normalized_task = task.strip()

    # 解释、总结、翻译通常是一次输入对应一次文本输出，
    # 不需要模型选择工具或维护多步状态，所以归为 Chatbot。
    # 依次检查三个关键词是否出现在已经清理过的任务描述中。
    # any 只要发现一个关键词命中，就返回 True，进入 Chatbot 分类。
    if any(keyword in normalized_task for keyword in ("解释", "总结", "翻译")):
        return "chatbot"

    # 如果需求已经明确了固定步骤，程序可以直接按顺序执行。
    # 这种场景优先使用 Workflow，而不是为了“智能”引入 Agent。
    if any(keyword in normalized_task for keyword in ("固定步骤", "依次执行")):
        return "workflow"

    # 下面两个信号表示下一步需要根据当前信息动态决定：
    # 例如先检索，看到检索结果后再决定是否继续搜索。
    if any(
        keyword in normalized_task
        for keyword in ("选择工具", "根据结果", "根据检索结果", "动态追问")
    ):
        return "agent"

    # 信息不足时返回 workflow 只是教学兜底。
    # 实际项目中也可以返回“需要澄清”，而不是直接归类。
    return "workflow"


def main() -> None:
    examples = [
        "解释 React useMemo 的适用场景",
        "依次执行读取需求、生成 JSON、保存结果三个固定步骤",
        "根据检索结果决定继续搜索还是直接回答",
        "做一个页面分析工具",
    ]

    for example in examples:
        task_type = classify_task(example)
        print(f"[{task_type}] {example}")


if __name__ == "__main__":
    main()
