"""
文本切分服务。

RAG 不会把整篇文档直接塞给模型。
常见做法是先把文档切成多个 chunk/paragraph，再对每个段落建索引。

这个文件实现一个容易理解的切分策略：
1. 先按空行切成自然段。
2. 如果自然段太长，再按固定长度切开。
3. 相邻长段保留少量 overlap，减少上下文被硬切断的问题。
"""

from dataclasses import dataclass


@dataclass
class TextChunk:
    """
    切分后的文本块。

    position 表示它在原文中的顺序。
    content 是实际会写入 paragraph 表并生成向量的文本。
    """

    position: int
    content: str


def split_text(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[TextChunk]:
    """
    将一篇文档切分成多个 TextChunk。

    参数说明：
    - chunk_size：每个 chunk 的最大字符数。
    - chunk_overlap：长文本切开时，相邻 chunk 重叠的字符数。

    注意：
    真实项目更常用 token 维度切分，因为大模型上下文限制按 token 计算。
    这里先按字符切分，方便学习和调试。
    """

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")

    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized_text:
        return []

    # 先按空行切分，这样可以尽量保留 Markdown 文档的自然结构。
    raw_blocks = [block.strip() for block in normalized_text.split("\n\n") if block.strip()]

    chunks: list[TextChunk] = []
    for block in raw_blocks:
        chunks.extend(_split_block(block, chunk_size, chunk_overlap))

    # 重新编号，确保 position 是连续的 0, 1, 2...
    return [TextChunk(position=index, content=chunk.content) for index, chunk in enumerate(chunks)]


def _split_block(block: str, chunk_size: int, chunk_overlap: int) -> list[TextChunk]:
    """
    切分单个自然段。

    如果自然段没有超过 chunk_size，就原样返回。
    如果超过了，就按滑动窗口切开。
    """

    if len(block) <= chunk_size:
        return [TextChunk(position=0, content=block)]

    result: list[TextChunk] = []
    start = 0

    while start < len(block):
        end = min(start + chunk_size, len(block))
        content = block[start:end].strip()
        if content:
            result.append(TextChunk(position=len(result), content=content))

        if end >= len(block):
            break

        # 下一段往前回退 chunk_overlap 个字符。
        # 这样上一段末尾和下一段开头有重复内容，检索时不容易丢上下文。
        start = end - chunk_overlap

    return result
