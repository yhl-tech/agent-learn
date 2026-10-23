# 文本切分学习笔记

## 1. 为什么要切分

RAG 不会把整篇文档直接丢给模型。

原因有三个。

第一，文档可能太长。

```text
大模型上下文长度有限
整篇文档可能超过模型能处理的范围
```

第二，整篇文档作为检索单位太粗。

```text
用户问一个具体问题
真正相关的可能只有其中几句话
```

第三，引用来源需要更精确。

```text
返回“来自哪篇文档”不够
最好能返回“来自哪个段落”
```

所以要把文档切成多个 chunk。

在本项目里，chunk 对应：

```text
ParagraphModel
```

## 2. chunk 在 RAG 里的位置

入库阶段：

```text
读取文档文本
-> 切成 chunks
-> 每个 chunk 创建一个 ParagraphModel
-> 每个 ParagraphModel 生成 embedding
-> 通过 EmbeddingRepository 写入 Chroma 或 pgvector
```

问答阶段：

```text
用户问题
-> 问题 embedding
-> 检索最相似的 chunk
-> 把 chunk 内容作为引用交给模型
```

所以：

```text
chunk 是 RAG 的最小检索单位。
```

不是文档被直接检索。

真正被检索的是：

```text
文档切出来的段落。
```

## 3. 本项目的代码位置

入口：

```text
backend/app/services/chunk_service.py
```

核心函数：

```python
def split_text(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[TextChunk]:
```

返回值：

```python
@dataclass
class TextChunk:
    position: int
    content: str
```

字段含义：

```text
position  chunk 在原文中的顺序
content   chunk 的文本内容
```

## 4. 本项目切分流程

整体流程：

```text
1. 检查 chunk_overlap 必须小于 chunk_size
2. 统一换行符
3. 去掉整篇文本首尾空白
4. 按空行切成自然段
5. 短自然段直接作为 chunk
6. 长自然段按固定长度滑动切分
7. 长段切分时保留 overlap
8. 重新生成连续 position
```

对应代码：

```python
normalized_text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
raw_blocks = [block.strip() for block in normalized_text.split("\n\n") if block.strip()]
```

含义：

```text
先把不同系统的换行符统一成 \n
再用空行把文档拆成自然段
```

## 5. 为什么先按空行切

Markdown 或普通文本里，空行通常表示段落边界。

例如：

```text
第一段内容...

第二段内容...

第三段内容...
```

按空行切，可以尽量保留作者原本的结构。

这样比每 800 个字符硬切更自然：

```text
标题和正文不容易被随便拆开
一个完整说明不容易被拆到不同块
列表内容更可能保持在一起
```

所以本项目策略是：

```text
先尊重自然段
自然段太长才硬切
```

## 6. `chunk_size` 是什么

默认值：

```python
chunk_size: int = 800
```

含义：

```text
每个 chunk 最多约 800 个字符。
```

太大时：

```text
检索粒度粗
一个 chunk 里可能混入很多无关内容
prompt 变长
模型更容易被噪声干扰
引用不够精准
```

太小时：

```text
上下文容易断
一个完整概念可能被拆散
检索结果数量增加
需要更多 top_k 才能拼回上下文
```

所以 chunk_size 是一个平衡：

```text
既要足够短，方便精准检索
又要足够长，保留完整语义
```

## 7. `chunk_overlap` 是什么

默认值：

```python
chunk_overlap: int = 120
```

含义：

```text
长文本切成多个 chunk 时，相邻 chunk 重叠 120 个字符。
```

例如：

```text
chunk_size = 800
chunk_overlap = 120
```

第一个 chunk：

```text
0 到 800
```

第二个 chunk：

```text
680 到 1480
```

中间重叠：

```text
680 到 800
```

为什么要重叠？

因为固定长度切分可能刚好切断一句话或一个概念。

overlap 可以让边界附近的内容在两个 chunk 中都出现。

这样检索时不容易丢上下文。

## 8. 为什么 `chunk_overlap` 必须小于 `chunk_size`

代码：

```python
if chunk_overlap >= chunk_size:
    raise ValueError("chunk_overlap 必须小于 chunk_size")
```

原因：

```text
下一段的起点 = 当前 end - chunk_overlap
```

如果 `chunk_overlap >= chunk_size`，下一段起点不会向前推进。

结果可能是：

```text
无限循环
重复切同一段内容
```

所以必须保证：

```text
chunk_overlap < chunk_size
```

## 9. `_split_block` 做了什么

如果自然段不长：

```python
if len(block) <= chunk_size:
    return [TextChunk(position=0, content=block)]
```

直接返回。

如果自然段太长：

```python
while start < len(block):
    end = min(start + chunk_size, len(block))
    content = block[start:end].strip()
    ...
    start = end - chunk_overlap
```

这就是滑动窗口。

每次切：

```text
从 start 开始
最多切到 start + chunk_size
下一次从 end - chunk_overlap 开始
```

## 10. 为什么最后要重新编号

`_split_block` 内部返回的 `position` 是当前自然段内部的位置。

但一篇文档可能有多个自然段。

所以 `split_text` 最后会重新编号：

```python
return [TextChunk(position=index, content=chunk.content) for index, chunk in enumerate(chunks)]
```

目的：

```text
确保整篇文档的 chunk position 是连续的 0, 1, 2...
```

这个 position 后续会写入：

```text
ParagraphModel.position
向量索引 metadata.position
```

作用：

```text
保留段落在原文中的顺序
方便展示和调试
方便后续扩展上下文拼接
```

## 11. 切分结果如何入库

在 `document_service.py` 中：

```python
chunks = split_text(text)
```

然后：

```python
for chunk in chunks:
    paragraph = ParagraphModel(
        knowledge_id=knowledge_id,
        document_id=document.id,
        content=chunk.content,
        position=chunk.position,
    )
    db.add(paragraph)
```

也就是说：

```text
TextChunk 是切分阶段的临时对象
ParagraphModel 是数据库中的持久化对象
```

随后每个 `paragraph.content` 会生成向量：

```python
embeddings = embedding_service.embed_texts([paragraph.content for paragraph in paragraphs])
```

所以切分质量会直接影响向量检索质量。

## 12. 字符切分和 token 切分

本项目按字符数切分：

```text
len(block)
block[start:end]
```

优点：

```text
容易理解
不需要额外 tokenizer
本地调试稳定
```

缺点：

```text
大模型上下文限制通常按 token 计算
中文、英文、符号的 token 数不等于字符数
固定字符切分可能切断句子
```

真实项目更常见：

```text
按 token 切分
按标题层级切分
按 Markdown 结构切分
按句子边界切分
递归切分
```

学习版先用字符切分，是为了让主链路更直观。

## 13. 切分参数怎么调

如果回答经常缺上下文：

```text
适当增大 chunk_size
适当增大 chunk_overlap
适当增大 top_k
```

如果检索结果噪声很多：

```text
适当减小 chunk_size
减少过大的 top_k
优化文档结构
```

如果 prompt 太长：

```text
减小 chunk_size
减小 top_k
在生成前做引用压缩或重排
```

本项目默认：

```text
chunk_size = 800
chunk_overlap = 120
```

是为了学习时先保持简单。

## 14. 常见知识点

文本切分常见概念：

```text
Chunk          文本块
Paragraph      本项目中的 chunk 持久化结果
Chunk Size     单个 chunk 的最大长度
Overlap        相邻 chunk 的重叠内容
Position       chunk 在原文中的顺序
Tokenizer      把文本拆成 token 的工具
Token          模型处理文本的基本单位
Context Window 模型一次能处理的上下文长度
```

这些概念在本项目里的对应：

```text
Chunk          TextChunk
Paragraph      ParagraphModel
Chunk Size     split_text 的 chunk_size
Overlap        split_text 的 chunk_overlap
Position       TextChunk.position / ParagraphModel.position
```

## 15. 常见误区

误区一：chunk 越大越好。

```text
太大时检索不精准，还会占用 prompt 空间。
```

误区二：chunk 越小越好。

```text
太小时上下文断裂，一个完整答案可能散落在多个 chunk。
```

误区三：只看 embedding，不看切分。

```text
检索效果差不一定是 embedding 模型差。
很多时候是 chunk 切得不合理。
```

误区四：忽略 position。

```text
position 可以帮助还原原文顺序。
后续做相邻段落扩展时很重要。
```

## 16. 最小记忆模型

```text
切分 = 把长文档变成可检索的小段
chunk_size = 每段最大长度
chunk_overlap = 相邻段保留重复上下文
position = 段落顺序
ParagraphModel = chunk 入库后的业务对象
```
