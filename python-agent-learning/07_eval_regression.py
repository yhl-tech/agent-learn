"""
Eval 回归评估技术导读

1. 这个技术是什么
   Eval 是对 Agent / RAG 能力的固定评测。它用一批固定问题、预期来源、预期关键词
   或标准答案来检查系统是否仍然表现正常。

2. 它解决什么问题
   Agent 输出不像传统函数那样完全确定，Prompt、模型、chunk 参数、检索策略、知识库内容
   都可能改变结果。只靠人工随手试几个问题，很难发现能力退化。

3. 工程中常见方案
   - 检索 Eval：检查正确文档是否进入 top-k。
   - 回答 Eval：检查答案是否包含关键事实、是否引用来源。
   - 工具调用 Eval：检查模型是否选择正确工具、参数是否正确。
   - 端到端 Eval：从用户问题到最终结果全链路评估。
   - 人工标注 + 自动评测结合：关键场景人工复核，常规场景自动回归。

4. 当前业界实践效果
   Eval 是生产级 Agent 的核心工程能力。没有 Eval，就很难判断一次 Prompt 修改、
   模型升级、知识库更新到底是变好了还是变坏了。
   但 Eval 本身也需要持续维护，尤其要沉淀历史失败案例。

5. 常见问题
   - 评测集太少，只覆盖了 Demo 场景。
   - 只看模型回答是否“像对的”，没有检查来源。
   - 测试样例和真实用户问题差距太大。
   - 评测指标单一，只看命中率，不看成本和延迟。
   - 模型评模型时可能误判，需要抽样人工复核。

6. 常见解决思路
   - 从真实用户问题、线上失败案例、核心业务问题中沉淀 EvalCase。
   - RAG 先评估检索召回，再评估最终回答。
   - 每次改 chunk_size、chunk_overlap、k、Prompt 或模型后都跑 Eval。
   - 同时记录准确率、召回率、平均耗时、token 成本。
   - 把 Eval 接入 CI，失败时阻断高风险改动。

7. 本文件做什么
   本文件实现一个最小 RAG Eval：
   对固定问题检查是否命中预期来源文件，以及上下文中是否包含预期关键词。
"""

# importlib 用来动态导入模块。
# 因为 04_rag_qa.py 文件名以数字开头，不能直接写 import 04_rag_qa。
import importlib
# sys 用来控制程序退出码。Eval 失败时用 sys.exit(1) 表示命令失败。
import sys
# dataclass 可以快速定义只保存数据的类，适合写评测样例。
from dataclasses import dataclass
# List 是类型标注，表示字段是字符串列表。
from typing import List


# 导入 04_rag_qa.py，复用里面的加载文档、切分、检索和拼上下文函数。
rag_module = importlib.import_module("04_rag_qa")


@dataclass
class EvalCase:
    # question 是评测问题。
    question: str
    # expected_sources 是这个问题应该命中的来源文件。
    expected_sources: List[str]
    # expected_terms 是检索上下文里应该出现的关键词。
    expected_terms: List[str]


# EVAL_CASES 是固定评测集。
# Agent / RAG 代码每次改完后，都应该跑一遍，避免能力退化。
EVAL_CASES = [
    EvalCase(
        question="Button 有哪些类型？",
        expected_sources=["data/kb/button.md"],
        expected_terms=["primary", "secondary", "danger"],
    ),
    EvalCase(
        question="表单提交前要做什么校验？",
        expected_sources=["data/kb/form_validation.md"],
        expected_terms=["schema", "字段级错误"],
    ),
    EvalCase(
        question="tool_calls 是不是已经执行了工具？",
        expected_sources=["data/kb/tool_calling.md"],
        expected_terms=["调用计划", "invoke"],
    ),
    EvalCase(
        question="Agent UI 为什么需要 waiting_approval？",
        expected_sources=["data/kb/agent_ui.md"],
        expected_terms=["危险操作", "确认"],
    ),
]


def run_eval_case(case: EvalCase) -> bool:
    # 复用 RAG 流程：加载知识库。
    documents = rag_module.load_knowledge_base()
    # 复用 RAG 流程：切分文档。
    chunks = rag_module.split_documents(documents)
    # 复用 RAG 流程：根据问题检索相关 chunk。
    related_docs = rag_module.retrieve_context(case.question, chunks)
    # 把检索结果拼成上下文，用于检查关键词是否出现。
    context = rag_module.build_context(related_docs)
    # 提取本次命中的来源文件。
    sources = {doc.metadata["source"] for doc in related_docs}

    # 检查预期来源是否全部命中。
    has_expected_source = all(source in sources for source in case.expected_sources)
    # 检查预期关键词是否都出现在检索上下文里。
    has_expected_terms = all(term in context for term in case.expected_terms)
    # 来源和关键词都满足，才算这个样例通过。
    passed = has_expected_source and has_expected_terms

    # 打印每条样例的结果，方便定位是哪条问题失败。
    status = "通过" if passed else "失败"
    print(f"[{status}] {case.question}")
    print(f"  命中来源：{', '.join(sorted(sources))}")
    if not has_expected_source:
        # 来源没命中，通常说明检索召回有问题。
        print(f"  缺少来源：{', '.join(case.expected_sources)}")
    if not has_expected_terms:
        # 关键词没出现，通常说明检索内容不够相关，或者 chunk 切分/排序需要调整。
        print(f"  缺少关键词：{', '.join(case.expected_terms)}")

    return passed


def main() -> None:
    # 逐条运行固定评测样例。
    results = [run_eval_case(case) for case in EVAL_CASES]
    # True 在 sum 里会被当成 1，False 会被当成 0。
    passed_count = sum(results)
    total_count = len(results)

    print(f"\nEval 结果：{passed_count}/{total_count} 通过")
    # 只要有任意样例失败，就用退出码 1 让命令失败。
    # 这样后续接入 CI 时，Eval 失败可以直接阻断提交或部署。
    if passed_count != total_count:
        sys.exit(1)


# 直接运行 python 07_eval_regression.py 时会执行 main()。
# 如果被其他测试文件 import，则不会自动执行。
if __name__ == "__main__":
    main()
