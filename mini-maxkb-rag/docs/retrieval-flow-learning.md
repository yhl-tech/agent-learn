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
上传任务会保存文件、切分段落、生成向量，并通过当前配置的向量仓库建立索引。
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
    vector_store: EmbeddingRepository,
    score_threshold: float = 0.0,
    search_mode: str = "embedding",
    blend_weight: float = 0.5,
) -> list[RetrievedParagraph]:
```

这个函数的输入：

```text
db                 当前请求的数据库会话
knowledge_id       查哪个知识库
question           用户问题
top_k              最多返回几条
embedding_service  负责把问题转成向量
vector_store       统一向量仓库，可以是 Chroma 或 pgvector
score_threshold    最低召回分数
search_mode        embedding / keywords / blend
blend_weight       混合检索中向量通道的权重
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

当前支持三种检索模式：

```text
embedding
问题 -> 问题向量 -> 向量仓库 -> 段落候选和问题候选

keywords
问题 -> 全文检索 -> 段落候选

blend
向量候选 + 关键词候选 -> weighted RRF -> 统一候选
```

三种模式最终汇合到同一条业务回源链路：

```text
候选 paragraph_id
-> 批量读取 Paragraph
-> 批量读取 Document
-> 再次校验 knowledge_id
-> 封装 RetrievedParagraph
-> 交给 chat_service 生成回答
```

## 4. 为什么先把问题转成向量

向量后端做的是向量相似度检索。

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

只有 `embedding` 和 `blend` 模式需要生成问题向量。纯 `keywords` 模式直接使用原始问题执行全文检索。

## 5. 检索配置为什么需要这些参数

检索需要回答：

```text
查哪里？
走哪种召回通道？
查几条？
最低接受什么分数？
混合模式如何分配权重？
```

对应参数：

```text
knowledge_id      查哪里
search_mode       embedding / keywords / blend
top_k             查几条
score_threshold   最低分数
blend_weight      向量通道权重，关键词权重为 1 - blend_weight
```

有效配置按三层合并：

```text
系统默认值
-> Knowledge.retrieval_config
-> 单次请求覆盖值
```

单次请求覆盖只影响本次调用，不会写回知识库。

## 6. `knowledge_id` 为什么关键

无论使用 Chroma、pgvector、SQLite FTS5 还是 PostgreSQL `tsvector`，查询都必须限定 `knowledge_id`。

如果没有这个条件：
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

向量仓库先按 `knowledge_id` 查询，业务回源时 `_load_retrieved_paragraphs` 又检查一次 `paragraph.knowledge_id`，形成两层隔离。

## 7. 向量仓库返回什么

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
vector_id  向量索引中的稳定 ID
score      后端归一后的向量相关分数
metadata   写入向量时带上的业务信息
document   外部向量后端可携带的文本；业务回源不依赖它
```

metadata 里最重要的是：

```text
paragraph_id
document_id
knowledge_id
position
source_type
problem_id（问题向量才有）
```

`EmbeddingRepository` 屏蔽具体后端：

```text
SQLite 默认      ChromaEmbeddingRepository
PostgreSQL       PostgresEmbeddingRepository
```

## 8. 为什么还要回业务表查

向量仓库返回的是检索候选，不是最终业务对象。

最终引用所需的数据在 SQLAlchemy 业务表：

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
以业务数据库中的当前数据为准
可以拿到完整的文档信息
后续扩展权限、状态、删除逻辑更清晰
```

一句话：

```text
检索后端负责找候选，业务数据库负责确认可用对象。
```

问题向量还需要先回源：

```text
problem_id
-> ProblemParagraphMapping
-> 一个或多个 paragraph_id
-> Paragraph + Document
```

因此命中“用户可能怎样提问”后，最终提供给模型的证据仍是原始段落。

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
检索索引和业务表可能短暂不一致
metadata 可能缺字段
paragraph 可能已被删除
document 可能已被删除
问题可能没有有效段落映射
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
    match_type: str
    score_meta: dict
```

它是检索服务输出给回答服务的对象。

它把三类信息放在一起：

```text
paragraph  被召回的段落
document   段落所属文档
score      相似度分数
match_type 命中类型：embedding / keywords / problem / blend
score_meta 各通道原始分数、排名和向量来源
```

为什么不直接把底层检索结果交给 `chat_service`？

因为底层结果偏存储实现：

```text
Chroma distance
pgvector cosine distance
全文检索 rank
问题向量 metadata
```

`chat_service` 需要的是业务语义：

```text
这段内容来自哪份文档
段落内容是什么
分数是多少
```

所以 `retrieval_service` 的职责是：

```text
把多路检索结果翻译成统一、业务可用的段落引用。
```

## 11. score 怎么来的

不同通道的原始分数不可直接比较：

```text
Chroma       distance 转成越大越相关的 score
pgvector     cosine distance 转成 1 - distance
关键词检索   FTS5 rank 或 PostgreSQL ts_rank
```

单通道模式会归一并按阈值过滤。`blend` 模式使用 weighted RRF，根据两路排名融合：

```text
向量贡献      blend_weight / (RRF_K + vector_rank)
关键词贡献    (1 - blend_weight) / (RRF_K + keyword_rank)
最终分数      两路贡献之和再归一化
```

RRF 关注各通道中的相对排名，不要求向量分数和全文分数处于同一量纲。

最终 score 主要用于：

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

详细推导见 `hybrid-retrieval-learning.md`。

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

段落向量入库时：

```text
ParagraphModel.id
-> 稳定 vector_id
-> EmbeddingRepository.upsert_paragraphs(...)
```

问题向量入库时：

```text
ProblemModel.id
-> metadata.problem_id
-> EmbeddingRepository
```

检索时：

```text
EmbeddingRepository.search(...)
-> paragraph_id 直接形成候选
-> 或 problem_id 经 Mapping 转成 paragraph_id
-> 与关键词候选按模式重排
-> 批量读取 Paragraph 和 Document
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
embedding 是否写入当前向量后端
query 时 knowledge_id 是否正确
search_mode 是否正确
top_k 是否大于 0
```

问题：召回了别的知识库内容。

重点检查：

```text
向量或关键词 Repository 是否过滤 knowledge_id
写入 metadata 时 knowledge_id 是否正确
业务回源时 paragraph.knowledge_id 是否正确
```

问题：召回内容相关性差。

可能原因：

```text
HashEmbeddingService 语义能力有限
chunk 切分不合理
top_k 设置不合适
文档内容和问题词汇差异太大
blend_weight 不适合当前语料
缺少问题增强数据
```

问题：底层检索有结果但 references 为空。

可能原因：

```text
metadata 缺 paragraph_id 或 problem_id
问题没有有效 mapping
业务数据库里查不到 paragraph
业务数据库里查不到 document
候选不属于当前 knowledge_id
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
embedding / keywords / blend
SQLite FTS5 / PostgreSQL tsvector
weighted RRF
score threshold
问题向量回源
Reference
检索测试接口
```

暂时没有实现：

```text
Cross-Encoder 或 LLM rerank
相邻段落扩展
引用压缩
查询改写
```

## 17. 最小记忆模型

```text
search_mode = 选择向量、关键词或混合召回
EmbeddingRepository = 屏蔽 Chroma 与 pgvector 差异
weighted RRF = 用排名融合不同量纲的候选
problem_id -> mapping -> paragraph_id = 问题增强回源
knowledge_id = 存储查询和业务回源的双重边界
RetrievedParagraph = 多路检索统一后的业务结果
```

继续阅读：

```text
hybrid-retrieval-learning.md
problem-enhancement-learning.md
database-migration-pgvector-learning.md
```
