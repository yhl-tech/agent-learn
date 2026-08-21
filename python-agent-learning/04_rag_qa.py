"""
RAG 与知识库问答技术导读

1. 这个技术是什么
   RAG 是 Retrieval-Augmented Generation，中文通常叫“检索增强生成”。
   它先从知识库检索相关资料，再把资料作为上下文交给模型回答。

2. 它解决什么问题
   模型本身不知道你的团队文档、组件规范、业务接口和最新制度。
   直接问模型容易幻觉；RAG 通过“先检索、再回答”，让模型基于可追溯资料生成答案。

3. 知识库整体方案有哪些
   - 本地文件知识库：Markdown、PDF、代码文件、FAQ 等。
   - 数据库知识库：从业务库、工单、CMS、Wiki 中同步内容。
   - 向量库方案：Chroma、FAISS、Milvus、Qdrant、pgvector 等。
   - 混合检索方案：关键词检索 + 向量检索 + Rerank。
   - 权限知识库：按用户、部门、项目控制可检索内容。

4. 工程中常用方案
   - 文档加载：把文件、网页、Wiki 转成 Document。
   - 文档切块：按标题、段落、函数、字符长度切成 chunk。
   - Metadata：保存来源、标题、路径、权限、更新时间。
   - 检索：用关键词、Embedding 或混合检索找相关 chunk。
   - Rerank：对候选结果重新排序，提高 top-k 质量。
   - 生成：把问题和检索上下文交给模型，并要求列来源。
   - Eval：用固定问题集评估召回率和回答质量。

5. 当前业界实践效果
   RAG 是企业知识库问答、客服、研发助手、代码理解中最常用的方案之一。
   对“资料中能找到答案”的问题效果较好；对跨文档推理、权限复杂、文档质量差的场景，
   仍然需要较多工程治理。

6. 常见问题
   - chunk 切得不好，答案被切断或上下文太碎。
   - 检索召回差，正确文档没有进入 top-k。
   - 命中了相关文档，但模型仍然编造。
   - 文档过期或重复，导致答案冲突。
   - 没有权限控制，可能泄露敏感内容。
   - token 成本、延迟和向量库维护成本上升。

7. 常见解决思路
   - 用 Eval 数据集调 chunk_size、chunk_overlap、k 和检索策略。
   - 按 Markdown 标题、代码函数、业务章节做结构化切分。
   - 使用 Hybrid Search 和 Rerank 提升检索质量。
   - 强制回答带来源；无来源时允许回答“不确定”。
   - 给 Metadata 加权限、版本、更新时间。
   - 定期清理过期文档，建立知识库同步和质量检查流程。

8. 本文件做什么
   本文件实现的是最小 RAG：本地 Markdown 知识库 + 简单关键词检索 + 模型回答。
   它没有使用向量库，是为了先把 RAG 主流程讲清楚，再逐步升级到真实工程方案。
"""

# argparse 用来解析命令行参数，例如 --no-model 和用户输入的问题。
import argparse
# os 用来读取环境变量，这里主要判断是否配置了 OPENAI_API_KEY。
import os
# re 是正则表达式模块，这里用来从问题和文档里提取关键词。
import re
# pathlib.Path 用面向对象的方式处理文件路径，比手写字符串路径更稳。
from pathlib import Path
# Iterable / List / Set 都是类型标注，帮助 IDE、类型检查工具和读代码的人理解数据结构。
from typing import Iterable, List, Set

# truststore 可以让 Python 使用系统证书链，解决 macOS / 公司网络下的 HTTPS 证书校验问题。
try:
    import truststore
except ImportError:
    truststore = None

# load_dotenv 会读取 .env 文件，把 OPENAI_API_KEY / OPENAI_BASE_URL 加载到环境变量里。
from dotenv import load_dotenv
# Document 是 LangChain 表示“文档”的标准结构，包含正文 page_content 和元信息 metadata。
from langchain_core.documents import Document
# ChatOpenAI 是 LangChain 对聊天模型的统一封装。
from langchain_openai import ChatOpenAI
# APIConnectionError 是 OpenAI SDK 的连接错误类型，网络、代理、证书问题通常会走到这里。
from openai import APIConnectionError
# RecursiveCharacterTextSplitter 用来把长文档切成较小的 chunk。
from langchain_text_splitters import RecursiveCharacterTextSplitter


# __file__ 表示当前 Python 文件路径；Path(__file__).parent 表示当前文件所在目录。
PROJECT_ROOT = Path(__file__).parent
# 本地知识库目录。这里放 Markdown 文档，RAG 会从这些文档中检索上下文。
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "data" / "kb"
# 默认模型名。使用 DeepSeek 时，可以在 .env 中配置 OPENAI_MODEL=deepseek-chat 覆盖它。
DEFAULT_MODEL_NAME = "gpt-4o-mini"


def load_knowledge_base(kb_dir: Path = KNOWLEDGE_BASE_DIR) -> List[Document]:
    """读取本地 Markdown 知识库，转成 LangChain Document。"""
    # documents 用来保存所有读取到的 LangChain Document。
    documents: List[Document] = []

    # glob("*.md") 表示只读取知识库目录下的 Markdown 文件。
    # sorted(...) 保证读取顺序稳定，方便调试和测试。
    for file_path in sorted(kb_dir.glob("*.md")):
        # read_text 会读取文件内容；encoding="utf-8" 可以正确处理中文。
        content = file_path.read_text(encoding="utf-8")
        documents.append(
            Document(
                # page_content 是文档正文，后续检索和拼上下文都基于它。
                page_content=content,
                # metadata 用来保存来源信息。回答时带来源，可以降低模型胡编的风险。
                metadata={"source": str(file_path.relative_to(PROJECT_ROOT))},
            )
        )

    # 返回 Document 列表，后续会进入切分、检索、拼上下文流程。
    return documents


def split_documents(documents: List[Document]) -> List[Document]:
    """把长文档切成小块，后续真实 RAG 会对 chunk 做 embedding。"""
    # RAG 通常不会把整篇长文档一次性塞给模型，而是先切成小块。
    splitter = RecursiveCharacterTextSplitter(
        # chunk_size 表示每个片段的大致长度。太大会浪费上下文，太小会丢语义。
        chunk_size=220,
        # chunk_overlap 表示相邻片段保留一部分重叠内容，避免切断关键语义。
        chunk_overlap=40,
    )
    # split_documents 会保留原文档的 metadata，所以每个 chunk 仍然知道来源文件。
    return splitter.split_documents(documents)


def extract_terms(text: str) -> Set[str]:
    """提取粗粒度关键词。

    这里故意不用向量库，先让你看清 RAG 的工程流程。
    中文没有天然空格，所以额外加入 2 字符片段，提升简单检索的命中率。
    """
    # lower() 把英文统一转成小写，避免 Button / button 被当成两个词。
    normalized = text.lower()
    # 提取英文、数字、下划线、路径片段等关键词。
    terms = set(re.findall(r"[a-z0-9_./-]+", normalized))

    # 中文不像英文一样天然用空格分词，所以这里先把连续中文提取出来。
    chinese_text = "".join(re.findall(r"[\u4e00-\u9fff]+", normalized))
    # 用 2 个中文字符作为一个粗粒度词片段，例如“表单提交”会产生“表单”“单提”“提交”。
    for index in range(max(len(chinese_text) - 1, 0)):
        terms.add(chinese_text[index : index + 2])

    # 过滤空字符串，返回 set 可以自动去重。
    return {term for term in terms if term.strip()}


def score_document(question_terms: Set[str], document: Document) -> int:
    # 把文档内容也提取成关键词集合。
    document_terms = extract_terms(document.page_content)
    # question_terms & document_terms 表示两个集合的交集。
    # 交集越大，说明文档和问题共享关键词越多，相关性越高。
    return len(question_terms & document_terms)


def retrieve_context(
    question: str,
    chunks: Iterable[Document],
    k: int = 3,
) -> List[Document]:
    """根据问题检索最相关的文档块。"""
    # 先把用户问题转成关键词集合。
    question_terms = extract_terms(question)
    # sorted(..., reverse=True) 会按相关性分数从高到低排序。
    ranked_chunks = sorted(
        chunks,
        # key 指定排序依据：每个 chunk 和问题的关键词重合数量。
        key=lambda chunk: score_document(question_terms, chunk),
        reverse=True,
    )
    # 只返回前 k 个最相关的文档块，避免把无关内容塞给模型。
    return ranked_chunks[:k]


def build_context(related_docs: Iterable[Document]) -> str:
    # 把检索到的多个 Document 拼成一段文本上下文。
    # 每段都带“来源”，方便模型在回答末尾列引用。
    return "\n\n".join(
        f"来源：{doc.metadata['source']}\n内容：{doc.page_content}"
        for doc in related_docs
    )


def configure_ssl_trust_store() -> None:
    # macOS 或公司网络下，Python 自带证书链可能不信任模型服务证书。
    # truststore.inject_into_ssl() 会让 Python 复用系统证书链，通常比关闭 SSL 校验更安全。
    if truststore is not None:
        truststore.inject_into_ssl()


def create_chat_model() -> ChatOpenAI:
    # 创建模型客户端前先配置证书信任链，避免 DeepSeek 等 HTTPS 服务连接失败。
    configure_ssl_trust_store()

    # OPENAI_MODEL 是自定义环境变量，用来切换模型名。
    # 例如使用 DeepSeek 时，可以配置 OPENAI_MODEL=deepseek-chat。
    model_name = os.getenv("OPENAI_MODEL", DEFAULT_MODEL_NAME)
    # OPENAI_BASE_URL 用来配置兼容 OpenAI 协议的模型服务地址。
    # DeepSeek 的地址可以配置为 https://api.deepseek.com。
    base_url = os.getenv("OPENAI_BASE_URL")

    # 没有配置 base_url 时，走 ChatOpenAI 默认服务地址。
    if not base_url:
        return ChatOpenAI(model=model_name, temperature=0)

    # 配置了 base_url 时，LangChain 会把请求发到对应的兼容服务。
    return ChatOpenAI(model=model_name, temperature=0, base_url=base_url)


def answer_with_model(question: str, context: str) -> str:
    # temperature=0 表示尽量稳定输出，适合问答、RAG、结构化任务。
    model = create_chat_model()
    # 这里才是真正调用模型。模型只能看到 question 和检索出来的 context。
    response = model.invoke(
        [
            # system 消息约束模型：只能根据上下文回答，并且必须列来源。
            ("system", "请只根据给定上下文回答。答案末尾必须列出来源。"),
            # human 消息包含用户问题和 RAG 检索到的上下文。
            ("human", f"问题：{question}\n\n上下文：\n{context}"),
        ]
    )
    # response.content 是模型生成的回答内容；转成 str 方便打印和返回。
    return str(response.content)


def print_model_connection_error(error: APIConnectionError) -> None:
    # 这里专门处理模型服务连接失败，避免一大段 traceback 干扰学习。
    print("模型调用失败：连接模型服务时出现网络或证书问题。")
    print("你当前的 RAG 检索已经成功，失败点只在最后一步调用模型。")
    print("常见原因：")
    print("- OPENAI_BASE_URL 配置错误。DeepSeek 应配置为 https://api.deepseek.com")
    print("- 终端设置了 HTTP/HTTPS 代理，但代理证书没有被当前 .venv 信任")
    print("- macOS / pyenv / 公司网络环境下，Python 没有使用系统证书链")
    print("建议先检查：")
    print("- .env 中是否配置 OPENAI_BASE_URL=https://api.deepseek.com")
    print("- .env 中是否配置 OPENAI_MODEL=deepseek-chat")
    print("- 如使用公司代理，把公司根证书配置到 SSL_CERT_FILE 或 REQUESTS_CA_BUNDLE")
    print(f"底层错误：{error}")


def main() -> None:
    # 读取 .env 中的模型服务配置。
    load_dotenv()

    # ArgumentParser 用来定义这个脚本支持哪些命令行参数。
    parser = argparse.ArgumentParser(description="本地知识库 RAG 问答练习")
    parser.add_argument(
        "question",
        # nargs="?" 表示 question 是可选参数；不传时使用 default。
        nargs="?",
        default="Button 有哪些类型？表单提交前要做什么？",
        help="要提问的问题",
    )
    parser.add_argument(
        "--no-model",
        # action="store_true" 表示只要命令里出现 --no-model，这个值就是 True。
        action="store_true",
        help="只展示检索上下文，不调用模型",
    )
    # parse_args 会把命令行输入解析成 args.question / args.no_model。
    args = parser.parse_args()

    # RAG 第 1 步：加载原始知识库文档。
    documents = load_knowledge_base()
    # RAG 第 2 步：把文档切成 chunk。
    chunks = split_documents(documents)
    # RAG 第 3 步：根据问题检索相关 chunk。
    related_docs = retrieve_context(args.question, chunks)
    # RAG 第 4 步：把检索结果拼成模型可读的上下文。
    context = build_context(related_docs)

    print("检索到的上下文：")
    print(context)

    # 如果传了 --no-model，或者没有配置 OPENAI_API_KEY，就只展示检索结果，不调用模型。
    # 这样即使没有模型 Key，也能先练习 RAG 的前半段流程。
    if args.no_model or not os.getenv("OPENAI_API_KEY"):
        print("\n未调用模型。配置 OPENAI_API_KEY 后去掉 --no-model 可以生成最终回答。")
        return

    # RAG 第 5 步：把问题和上下文交给模型，生成最终回答。
    print("\n模型回答：")
    try:
        print(answer_with_model(args.question, context))
    except APIConnectionError as error:
        print_model_connection_error(error)


# 直接运行 python 04_rag_qa.py 时会执行 main()。
# 如果被其他文件 import，例如 06_agent_api.py 复用这里的函数，则不会自动执行 main()。
if __name__ == "__main__":
    main()
