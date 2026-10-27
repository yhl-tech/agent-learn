"""
问答服务。

Chat 是 RAG 里的 G：
检索服务先拿到相关段落，Chat 服务再把问题和段落组织成 prompt，交给大模型生成回答。

为了让项目不依赖 API Key，第一版提供两种模式：
1. 配置 OPENAI_API_KEY：调用 OpenAI-compatible Chat API。
2. 未配置 OPENAI_API_KEY：返回一个基于引用段落拼出来的简化回答。
"""

from textwrap import shorten

import httpx

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_CHAT_MODEL
from app.schemas import ChatResponse, ReferenceRead
from app.services.retrieval_service import RetrievedParagraph


def build_references(retrieved: list[RetrievedParagraph]) -> list[ReferenceRead]:
    """
    将检索结果转换成 API 响应里的 references。
    """

    return [
        ReferenceRead(
            document_id=item.document.id,
            document_name=item.document.name,
            paragraph_id=item.paragraph.id,
            content=item.paragraph.content,
            score=item.score,
            match_type=item.match_type,
            score_meta=item.score_meta,
        )
        for item in retrieved
    ]


async def answer_question(question: str, retrieved: list[RetrievedParagraph]) -> ChatResponse:
    """
    根据问题和召回段落生成回答。

    如果没有召回段落，直接返回空结果。
    如果有 API Key，则调用真实模型。
    如果没有 API Key，则使用 fallback 回答，保证学习链路可以跑通。
    """

    references = build_references(retrieved)
    if not references:
        return ChatResponse(
            answer="没有在当前知识库中检索到相关段落。",
            references=[],
        )

    if OPENAI_API_KEY:
        answer = await _call_openai_compatible_chat(question, references)
    else:
        answer = _build_fallback_answer(question, references)

    return ChatResponse(answer=answer, references=references)


def _build_prompt(question: str, references: list[ReferenceRead]) -> str:
    """
    构造给大模型的 prompt。

    prompt 里明确要求“只基于引用内容回答”，这是 RAG 系统减少幻觉的常见做法。
    """

    context_lines = []
    for index, reference in enumerate(references, start=1):
        context_lines.append(
            "\n".join(
                [
                    f"[引用 {index}]",
                    f"文档：{reference.document_name}",
                    f"段落：{reference.content}",
                ]
            )
        )

    context = "\n\n".join(context_lines)
    return f"""你是一个知识库问答助手。
请只根据下面的引用内容回答问题。
如果引用内容不足以回答，请明确说“当前知识库中没有足够信息”。

问题：
{question}

引用内容：
{context}
"""


async def _call_openai_compatible_chat(question: str, references: list[ReferenceRead]) -> str:
    """
    调用 OpenAI-compatible Chat API。

    只要服务兼容 /chat/completions 协议，就可以通过环境变量切换：
    - OPENAI_BASE_URL
    - OPENAI_API_KEY
    - OPENAI_CHAT_MODEL
    """

    prompt = _build_prompt(question, references)
    url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            url,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": OPENAI_CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": "你是一个严谨的知识库问答助手。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def _build_fallback_answer(question: str, references: list[ReferenceRead]) -> str:
    """
    没有配置大模型时的简化回答。

    它不会真正理解问题，只是把最相关的几段内容整理出来。
    这个模式的价值是让你先验证：
    上传、切分、向量写入、检索、引用返回这些工程链路是否正常。
    """

    lines = [
        f"问题：{question}",
        "",
        "当前未配置 OPENAI_API_KEY，下面是根据检索段落生成的简化回答：",
        "",
    ]

    for index, reference in enumerate(references, start=1):
        snippet = shorten(reference.content.replace("\n", " "), width=220, placeholder="...")
        lines.append(f"{index}. 来自《{reference.document_name}》：{snippet}")

    return "\n".join(lines)
