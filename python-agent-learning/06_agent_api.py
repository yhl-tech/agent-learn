"""
Agent API 服务化技术导读

1. 这个技术是什么
   Agent API 服务化是把本地脚本里的 Agent 能力封装成 HTTP 接口，
   让前端页面、其他后端服务、自动化任务都可以调用它。

2. 它解决什么问题
   学习阶段直接运行 Python 脚本即可；真实业务中，Agent 通常要接入产品页面、
   内部平台、工作流系统或定时任务。API 是这些系统调用 Agent 的稳定边界。

3. 工程中常见方案
   - FastAPI / Flask / Django：Python 服务端封装。
   - Next.js API Route / Node 服务：前端团队常用的 BFF 方案。
   - SSE / WebSocket：长任务流式返回过程和中间状态。
   - 队列 + Worker：耗时 Agent 任务异步执行。
   - OpenAPI Schema：让前后端共享接口结构。

4. 当前业界实践效果
   Agent API 很适合做企业内部助手、知识库问答、工单分析、PR Review、数据查询等。
   但 Agent 调用通常比普通接口慢、成本高、失败形态复杂，所以服务化时必须重视状态展示、
   超时、重试、取消、权限和日志。

5. 常见问题
   - 接口只返回最终结果，用户看不到 Agent 正在做什么。
   - 请求耗时长，前端一直 loading。
   - 错误信息不结构化，前端无法友好展示。
   - 没有鉴权和限流，容易产生安全和成本问题。
   - 模型配置、Prompt、工具版本不可追踪。

6. 常见解决思路
   - 请求和响应都用 Pydantic schema 明确定义。
   - 长任务使用 SSE / WebSocket 返回阶段事件。
   - 统一错误结构，例如 error_code、message、detail。
   - 加鉴权、限流、超时、审计日志和 trace_id。
   - 危险操作进入 waiting_approval 状态，由用户确认。

7. 本文件做什么
   本文件用 FastAPI 暴露两个接口：
   /health 用于健康检查；/rag/ask 复用 04_rag_qa.py 的 RAG 能力返回答案和来源。
"""

# importlib 用来动态导入模块。
# 因为 04_rag_qa.py 文件名以数字开头，不能直接写 import 04_rag_qa。
import importlib
# os 用来读取环境变量，这里判断是否配置了 OPENAI_API_KEY。
import os
# List 是类型标注，表示 sources 是字符串列表。
from typing import List

# load_dotenv 会读取 .env 文件，把模型服务配置加载到环境变量。
from dotenv import load_dotenv
# FastAPI 用来把本地 Agent 能力封装成 HTTP API。
from fastapi import FastAPI
# BaseModel / Field 用来定义请求和响应的数据结构。
from pydantic import BaseModel, Field


# 模块加载时先读取 .env，保证接口处理时能拿到 OPENAI_API_KEY / OPENAI_BASE_URL。
load_dotenv()

# app 是 FastAPI 应用对象。后续通过装饰器把函数注册成接口。
app = FastAPI(title="Agent Learning API", version="0.1.0")

# 文件名以数字开头，不能写成普通 import 语法，所以这里用 importlib。
# 导入后可以通过 rag_module.load_knowledge_base() 复用 04_rag_qa.py 里的函数。
rag_module = importlib.import_module("04_rag_qa")


class HealthResponse(BaseModel):
    # status 表示服务是否正常。
    status: str
    # has_model_key 表示当前环境是否配置了模型 Key。
    has_model_key: bool


class RagRequest(BaseModel):
    # 用户要问的问题。
    question: str = Field(description="用户问题")
    # 是否调用模型生成最终回答。
    # 默认 False 是为了无 Key 时也可以练习 API 和 RAG 检索流程。
    use_model: bool = Field(
        default=False,
        description="是否调用模型生成答案；False 时只返回检索上下文，适合无 Key 练习",
    )


class RagResponse(BaseModel):
    # answer 是接口返回给调用方的答案。
    answer: str
    # sources 是本次检索命中的来源文件列表，方便前端展示引用。
    sources: List[str]
    # used_model 表示这次请求是否真的调用了模型。
    used_model: bool


# @app.get 表示注册一个 GET 接口。
# response_model 会约束接口响应结构，也会生成 OpenAPI 文档。
@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    # 健康检查接口通常用于确认服务能否访问、关键配置是否存在。
    return HealthResponse(
        status="ok",
        has_model_key=bool(os.getenv("OPENAI_API_KEY")),
    )


# @app.post 表示注册一个 POST 接口。
# request 参数会由 FastAPI 自动从请求 JSON 中解析成 RagRequest。
@app.post("/rag/ask", response_model=RagResponse)
def ask_rag(request: RagRequest) -> RagResponse:
    # 复用 04_rag_qa.py 的 RAG 第 1 步：加载知识库。
    documents = rag_module.load_knowledge_base()
    # RAG 第 2 步：切分文档。
    chunks = rag_module.split_documents(documents)
    # RAG 第 3 步：根据用户问题检索相关 chunk。
    related_docs = rag_module.retrieve_context(request.question, chunks)
    # RAG 第 4 步：把检索结果拼成上下文。
    context = rag_module.build_context(related_docs)
    # 从命中的 Document metadata 中提取来源，并去重排序。
    sources = sorted({doc.metadata["source"] for doc in related_docs})

    # 只有用户明确 use_model=true，并且环境里配置了 OPENAI_API_KEY，才真正调用模型。
    should_use_model = request.use_model and bool(os.getenv("OPENAI_API_KEY"))
    if should_use_model:
        # RAG 第 5 步：调用模型基于上下文生成回答。
        answer = rag_module.answer_with_model(request.question, context)
    else:
        # 不调用模型时，直接返回检索上下文。
        # 这样可以先验证 API、检索和来源展示，不被模型 Key 阻塞。
        answer = (
            "当前未调用模型，仅返回检索上下文。"
            "把 use_model 设为 true 并配置 OPENAI_API_KEY 后，可以生成最终回答。\n\n"
            f"{context}"
        )

    # 返回结构化响应，FastAPI 会自动转成 JSON。
    return RagResponse(
        answer=answer,
        sources=sources,
        used_model=should_use_model,
    )


# 直接运行 python 06_agent_api.py 时，会启动本地 API 服务。
if __name__ == "__main__":
    # uvicorn 是运行 FastAPI 的 ASGI 服务器。
    import uvicorn

    # reload=True 表示开发模式下文件变化会自动重启服务。
    uvicorn.run("06_agent_api:app", host="127.0.0.1", port=8000, reload=True)
