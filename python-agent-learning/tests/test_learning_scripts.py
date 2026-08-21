# importlib 用来动态导入文件名以数字开头的练习脚本。
import importlib

# pytest 是 Python 常用测试框架，这里用来验证确定性逻辑。
import pytest


# 04_rag_qa.py 文件名以数字开头，不能直接写 import 04_rag_qa。
rag_module = importlib.import_module("04_rag_qa")
# 08_human_approval_file_writer.py 也是同理，用 importlib 动态导入。
approval_module = importlib.import_module("08_human_approval_file_writer")


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
