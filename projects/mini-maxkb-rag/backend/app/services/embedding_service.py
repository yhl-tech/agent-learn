"""
Embedding 服务。

Embedding 的作用是把文本转换成向量。
向量可以理解成一串数字，语义相近的文本，向量距离通常也更近。

第一版使用本地哈希向量，不依赖外部模型服务。
它不是高质量语义向量，但有三个优点：
1. 不需要 API Key。
2. 每次运行结果稳定，方便调试。
3. 足够演示“文本 -> 向量 -> 相似度检索”的工程流程。

后续可以把 HashEmbeddingService 替换成 OpenAI、火山、Ollama 或 sentence-transformers。
"""

import hashlib
import math
import re

from app.config import EMBEDDING_DIMENSION


TOKEN_PATTERN = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


class HashEmbeddingService:
    """
    本地哈希向量实现。

    它的基本思路：
    1. 把文本切成词或字符片段。
    2. 每个 token 通过 hash 映射到固定维度的某一格。
    3. 对命中的维度累加权重。
    4. 最后做 L2 normalize，让不同长度文本更可比。

    这类似一个很简化的 hashing vectorizer。
    """

    def __init__(self, dimension: int = EMBEDDING_DIMENSION):
        self.dimension = dimension

    def embed_text(self, text: str) -> list[float]:
        """
        将单条文本转换成一个向量。
        """

        tokens = self._tokenize(text)
        vector = [0.0] * self.dimension

        for token in tokens:
            # blake2b 速度快且稳定。
            # digest_size=8 足够得到一个可转成整数的短 hash。
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            value = int.from_bytes(digest, byteorder="big", signed=False)
            index = value % self.dimension

            # 偶数加正权重，奇数加负权重。
            # 这样可以减少所有 token 都只往正方向堆叠导致的碰撞偏差。
            sign = 1.0 if value % 2 == 0 else -1.0
            vector[index] += sign

        return self._normalize(vector)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        批量向量化。

        Chroma 的 add/query 接口都支持 list 形式。
        service 层统一批量处理，后续替换成真实 embedding API 时也更自然。
        """

        return [self.embed_text(text) for text in texts]

    def _tokenize(self, text: str) -> list[str]:
        """
        简单分词。

        英文会按单词切分。
        中文在正则里会被连续识别成一段，所以这里额外加入中文单字 bigram 的效果有限。
        学习项目先保持简单，后续可以接 jieba 或更好的 tokenizer。
        """

        tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
        if tokens:
            return tokens
        return list(text)

    def _normalize(self, vector: list[float]) -> list[float]:
        """
        对向量做 L2 归一化。

        归一化后，长文档不会因为 token 更多就天然获得更大分数。
        """

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]
