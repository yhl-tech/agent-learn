# 检索链路学习笔记

## 1. Retrieval 是什么

RAG 里的 Retrieval 指检索。

目标：

```text
根据用户问题，从知识库中找出最相关的段落。
```

用户问：

```text
如何上传文档？
```

系统需要找到类似内容：

```text
上传文档接口会保存文件、读取文本、切分段落、生成向量并写入 Chroma。
```

这个“找相关段落”的过程就是 Retrieval。

一句话：

```text
Retrieval 决定模型回答时能看到哪些资料。
```

## 2. 本项目的检索入口

代码位置：

```text
backend/app/services/retrieval_service.py
```

核心函数：

```python
def retrieve_paragraphs(
    db: Session,
    knowledge_id: str,
    question: str,
    top_k: int,
    embedding_service: HashEmbeddingService,
    vector_store: ChromaVectorStore,
) -> list[RetrievedParagraph]:
```

这个函数的输入：

```text
db                 当前请求的数据库会话
knowledge_id       查哪个知识库
question           用户问题
top_k              最多返回几条
embedding_service  负责把问题转成向量
vector_store       负责查询 Chroma
```

输出：

```text
list[RetrievedParagraph]
```

也就是：

```text
一组业务可用的召回段落。
```

## 3. 检索链路总览

核心流程：

```text
用户问题
-> 生成问题向量
-> 去 Chroma 查相似段落向量
-> 读取 Chroma 返回的 metadata
-> 根据 paragraph_id 回 SQLite 查段落
-> 根据 document_id 回 SQLite 查文档
-> 封装成 RetrievedParagraph
-> 交给 chat_service 生成回答
```

对应代码：

```python
query_embedding = embedding_service.embed_text(question)
vector_results = vector_store.search(
    knowledge_id=knowledge_id,
    query_embedding=query_embedding,
    top_k=top_k,
)
```

## 4. 为什么先把问题转成向量

ChromaDB 做的是向量相似度检索。

它不能直接用一句中文问题去查段落。

所以必须先做：

```text
question -> query_embedding
```

本项目：

```python
query_embedding = embedding_service.embed_text(question)
```

这表示：

```text
用户问题经过和段落相同的 embedding 逻辑
变成同一维度的向量
```

只有问题向量和段落向量在同一个向量空间里，才能比较相似度。

## 5. 为什么参数是这几个

检索最少要回答三个问题：

```text
查哪里？
用什么查？
查几条？
```

对应参数：

```text
knowledge_id      查哪里
query_embedding   用什么查
top_k             查几条
```

本项目调用：

```python
vector_store.search(
    knowledge_id=knowledge_id,
    query_embedding=query_embedding,
    top_k=top_k,
)
```

含义：

```text
只在当前 knowledge_id 的范围里
用 question 生成的 query_embedding
查最相似的 top_k 个段落
```

## 6. `knowledge_id` 为什么关键

这个项目所有知识库共用同一个 Chroma collection。

所以必须用：

```python
where={"knowledge_id": knowledge_id}
```

限定检索范围。

如果没有这个条件：

```text
用户在 A 知识库提问
系统可能召回 B 知识库的段落
```

这不是单纯的排序问题。

这是数据隔离问题。

在 RAG 系统中：

```text
相似度负责找“像”的内容
过滤条件负责保证“允许查”的范围
```

## 7. Chroma 返回什么

`vector_store.search` 返回：

```text
list[VectorSearchResult]
```

结构：

```python
@dataclass
class VectorSearchResult:
    vector_id: str
    score: float
    metadata: dict
    document: str
```

字段含义：

```text
vector_id  Chroma 中的向量 ID
score      转换后的相似度分数
metadata   写入向量时带上的业务信息
document   Chroma 中保存的段落文本
```

metadata 里最重要的是：

```text
paragraph_id
document_id
knowledge_id
position
```

## 8. 为什么还要回 SQLite 查

Chroma 返回的主要是向量检索结果。

它能返回 document 文本和 metadata。

但本项目真正的业务数据在 SQLite：

```text
ParagraphModel.content
ParagraphModel.position
DocumentModel.name
DocumentModel.id
```

所以检索后还要：

```python
paragraph = db.get(ParagraphModel, paragraph_id)
document = db.get(DocumentModel, paragraph.document_id)
```

这样做的好处：

```text
以 SQLite 中的业务数据为准
可以拿到完整的文档信息
后续扩展权限、状态、删除逻辑更清晰
```

一句话：

```text
Chroma 负责找相似，SQLite 负责确认业务对象。
```

## 9. 为什么要跳过缺失数据

代码：

```python
paragraph_id = result.metadata.get("paragraph_id")
if not paragraph_id:
    continue

paragraph = db.get(ParagraphModel, paragraph_id)
if paragraph is None:
    continue

document = db.get(DocumentModel, paragraph.document_id)
if document is None:
    continue
```

这里用了多个 `continue`。

原因：

```text
向量库和业务库可能短暂不一致
metadata 可能缺字段
paragraph 可能已被删除
document 可能已被删除
```

学习项目里不做复杂报错。

它选择：

```text
跳过不可用的召回结果
继续返回剩下可用的段落
```

这样问答接口更稳。

## 10. `RetrievedParagraph` 是什么

代码：

```python
@dataclass
class RetrievedParagraph:
    paragraph: ParagraphModel
    document: DocumentModel
    score: float
```

它是检索服务输出给回答服务的对象。

它把三类信息放在一起：

```text
paragraph  被召回的段落
document   段落所属文档
score      相似度分数
```

为什么不直接把 Chroma 原始结果交给 `chat_service`？

因为 Chroma 原始结果偏底层：

```text
ids
distances
metadatas
documents
```

`chat_service` 需要的是业务语义：

```text
这段内容来自哪份文档
段落内容是什么
分数是多少
```

所以 `retrieval_service` 的职责是：

```text
把向量检索结果翻译成业务可用的段落引用。
```

## 11. score 怎么来的

Chroma 原始返回是 `distance`。

在 `vector_store.py` 中转换：

```python
score = 1.0 / (1.0 + float(distance))
```

含义：

```text
distance 越小，score 越大
distance 越大，score 越小
```

这个 score 主要用于：

```text
前端展示
调试检索结果
判断召回段落大致相关程度
```

它不是：

```text
答案正确率
模型置信度
严格概率
```

## 12. 检索结果如何进入回答

`chat_api.py` 中：

```python
retrieved = retrieve_paragraphs(...)
return await answer_question(payload.question, retrieved)
```

`chat_service.py` 中：

```python
references = build_references(retrieved)
```

然后构造 prompt：

```text
问题：
{question}

引用内容：
[引用 1]
文档：xxx
段落：xxx
```

最终模型基于这些引用回答。

所以检索结果质量直接影响：

```text
回答是否准确
引用是否可信
模型是否容易产生幻觉
```

## 13. top_k 对效果的影响

`top_k` 表示召回数量。

小 `top_k`：

```text
上下文少
速度快
噪声少
但可能漏召回
```

大 `top_k`：

```text
上下文多
更可能覆盖答案
但 prompt 更长
噪声更多
```

本项目默认：

```text
DEFAULT_TOP_K = 4
```

并通过 Schema 限制：

```text
1 <= top_k <= 20
```

## 14. 检索链路中的数据流

入库时：

```text
ParagraphModel.id
-> metadata.paragraph_id
-> Chroma.add(...)
```

检索时：

```text
Chroma.query(...)
-> result.metadata.paragraph_id
-> db.get(ParagraphModel, paragraph_id)
-> db.get(DocumentModel, paragraph.document_id)
-> RetrievedParagraph
```

这个闭环很重要。

如果 metadata 写错，后面就无法正确回到业务数据。

## 15. 常见问题排查

问题：没有召回结果。

先检查：

```text
文档是否上传成功
paragraph 是否生成
embedding 是否写入 Chroma
query 时 knowledge_id 是否正确
top_k 是否大于 0
```

问题：召回了别的知识库内容。

重点检查：

```text
vector_store.search 是否有 where={"knowledge_id": knowledge_id}
写入 metadata 时 knowledge_id 是否正确
```

问题：召回内容相关性差。

可能原因：

```text
HashEmbeddingService 语义能力有限
chunk 切分不合理
top_k 设置不合适
文档内容和问题词汇差异太大
```

问题：Chroma 有结果但 references 为空。

可能原因：

```text
metadata 缺 paragraph_id
SQLite 里查不到 paragraph
SQLite 里查不到 document
```

## 16. 常用知识点

检索链路常见概念：

```text
Query Embedding   问题向量
Candidate         候选召回结果
Top K             返回前 K 条
Metadata Filter   元数据过滤
Distance          向量距离
Score             展示用相似度分数
Reference         给模型和前端看的引用来源
Recall            召回能力
Ranking           排序能力
Rerank            对召回结果二次排序
```

本项目暂时实现了：

```text
Query Embedding
Top K
Metadata Filter
Distance -> Score
Reference
```

暂时没有实现：

```text
重排 rerank
关键词混合检索
多路召回
相邻段落扩展
引用压缩
```

## 17. 最小记忆模型

```text
检索 = 用问题向量找段落向量
knowledge_id = 限定检索范围
top_k = 返回几条
metadata.paragraph_id = 从 Chroma 回到 SQLite 的桥
RetrievedParagraph = 检索结果的业务封装
```
