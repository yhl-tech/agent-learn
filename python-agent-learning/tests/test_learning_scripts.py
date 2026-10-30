# importlib 用来动态导入文件名以数字开头的练习脚本。
import importlib

# pytest 是 Python 常用测试框架，这里用来验证确定性逻辑。
import pytest


# 04_rag_qa.py 文件名以数字开头，不能直接写 import 04_rag_qa。
rag_module = importlib.import_module("04_rag_qa")
# 08_human_approval_file_writer.py 也是同理，用 importlib 动态导入。
approval_module = importlib.import_module("08_human_approval_file_writer")
# 09_requirement_agent_loop.py 也是同理，用 importlib 动态导入。
agent_loop_module = importlib.import_module("09_requirement_agent_loop")
# 10_requirement_tool_agent.py 是 Day 3 的本地工具 Agent 示例。
tool_agent_module = importlib.import_module("10_requirement_tool_agent")


def test_rag_retrieves_button_source() -> None:
    # 加载本地知识库。
    documents = rag_module.load_knowledge_base()
    # 把文档切成 chunk。
    chunks = rag_module.split_documents(documents)
    # 用固定问题检索相关文档。
    related_docs = rag_module.retrieve_context("Button 有哪些类型？", chunks)
    # 提取命中的来源文件。
    sources = {doc.metadata["source"] for doc in related_docs}

    # 断言必须命中 button.md，否则说明 RAG 检索逻辑有退化。
    assert "data/kb/button.md" in sources


def test_file_writer_blocks_path_escape() -> None:
    # pytest.raises 用来断言某段代码应该抛出指定异常。
    # ../danger.txt 试图逃出 generated 目录，必须被安全检查拦截。
    with pytest.raises(ValueError, match="写入路径越界"):
        approval_module.resolve_safe_output_path("../danger.txt")


def test_requirement_agent_loop_completes_five_steps() -> None:
    result = agent_loop_module.run_agent_loop(
        "做一个审批列表页，支持搜索、筛选、分页、批量通过、查看审批详情。"
    )

    assert result.status == "completed"
    assert result.steps_used == 5
    assert "DataTable" in result.state.core_components
    assert "pagination" in result.state.state_requirements
    assert result.state.test_points


def test_requirement_agent_loop_returns_readable_error() -> None:
    result = agent_loop_module.run_agent_loop("")

    assert result.status == "failed"
    assert "需求为空" in result.reason
    assert result.state.errors


def test_requirement_agent_loop_respects_max_steps() -> None:
    result = agent_loop_module.run_agent_loop("做一个订单列表页，支持搜索和分页。", max_steps=2)

    assert result.status == "stopped"
    assert result.steps_used == 2
    assert len(result.state.trace) == 2


def test_requirement_tool_agent_completes_three_tools() -> None:
    result = tool_agent_module.run_requirement_tool_agent(
        "做一个订单列表页，支持按订单号搜索、状态筛选、排序、分页和导出。"
    )

    assert result.status == "completed"
    assert result.steps_used == 3
    assert "SearchBar" in result.state.core_components
    assert "pagination" in result.state.state_requirements
    assert "exporting" in result.state.state_requirements
    assert "sort_order" in result.state.state_requirements
    assert result.state.test_points


def test_requirement_tool_agent_has_three_registered_tools() -> None:
    tool_names = {tool.name for tool in tool_agent_module.TOOL_REGISTRY}

    assert tool_names == {"extract_components", "infer_state", "generate_test_points"}


def test_requirement_tool_agent_failure_samples_are_readable() -> None:
    results = [
        tool_agent_module.run_tool_call(tool_call)
        for tool_call in tool_agent_module.FAILURE_TOOL_CALLS
    ]

    assert len(results) == 3
    assert all(not result.success for result in results)
    assert {result.error_code or result.result.error_code for result in results} == {
        "EMPTY_REQUIREMENT",
        "INVALID_ARGS",
        "UNKNOWN_TOOL",
    }
