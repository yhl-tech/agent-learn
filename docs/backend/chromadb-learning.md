# ChromaDB 学习笔记

## 1. ChromaDB 是什么

ChromaDB 是向量数据库，也是本项目在 SQLite 本地模式下使用的向量后端。

当前业务代码不直接依赖 Chroma，而是依赖统一的 `EmbeddingRepository`：

```text
SQLite + Chroma 模式       ChromaEmbeddingRepository
PostgreSQL + pgvector 模式 PostgresEmbeddingRepository
```

普通数据库擅长查：

```text
id 等于什么
name 包含什么
created_at 大于什么时间
```

向量数据库擅长查：

```text
哪个向量和这个查询向量最相似
```

在 RAG 里，ChromaDB 的任务是：

```text
保存段落 embedding
根据问题 embedding 找相似段落
```

## 2. 向量数据库保存什么

一条向量数据通常包含：

```text
id         向量 ID
embedding  向量
document   原始文本
metadata   业务信息
```

本项目中一条 Chroma 数据可以理解成：

```text
id          vector_id
embedding   paragraph.content 生成的向量
document    paragraph.content
metadata    knowledge_id / document_id / paragraph_id / position
```

也就是说：

```text
Chroma 保存“用于相似度检索的数据”
SQLite 保存“业务对象和业务关系”
```

问题增强向量还会在 metadata 中保存：

```text
source_type = problem
problem_id
```

## 3. 本项目中的封装

入口：

```text
backend/app/storage/vector_store.py
```

核心类：

```python
class ChromaEmbeddingRepository:
```

它实现 `EmbeddingRepository` 协议，是 Chroma 的具体适配器。

它不负责：

```text
生成 embedding
处理 HTTP 请求
组装 prompt
```

它负责：

```text
初始化 Chroma client
获取 collection
写入段落向量
查询相似段落
按 document_id 删除向量
同步维护 SQLAlchemy Session 中的 EmbeddingRefModel
```

业务 service 只看到统一仓库接口，因此切换 pgvector 时不需要改检索流程。

## 4. Client 是什么

初始化代码：

```python
self.client = chromadb.PersistentClient(
    path=str(CHROMA_DIR),
    settings=Settings(anonymized_telemetry=False),
)
```

`PersistentClient` 表示：

```text
使用本地持久化 Chroma。
向量数据会保存到磁盘目录，而不是只存在内存里。
```

本项目保存目录：

```text
backend/data/chroma
```

来自配置：

```python
CHROMA_DIR = DATA_DIR / "chroma"
```

## 5. Collection 是什么

代码：

```python
COLLECTION_NAME = "mini_maxkb_paragraphs"
self.collection = self.client.get_or_create_collection(name=COLLECTION_NAME)
```

Collection 可以理解成：

```text
一组向量数据的集合，类似向量世界里的一张表。
```

本项目目前只有一个 collection：

```text
mini_maxkb_paragraphs
```

所有知识库的段落向量都放在这个 collection 里。

不同知识库之间依靠：

```text
metadata.knowledge_id
```

隔离。

## 6. 为什么不是每个知识库一个 collection

也可以设计成：

```text
一个 knowledge 一个 collection
```

但本项目选择：

```text
所有段落放一个 collection
通过 metadata 过滤 knowledge_id
```

这样学习成本更低。

优势：

```text
collection 管理简单
代码结构简单
删除和查询都通过 metadata 过滤
```

需要注意：

```text
每次查询必须带 where={"knowledge_id": knowledge_id}
```

这是数据隔离的关键。

## 7. 写入向量：`collection.add` 与 `collection.upsert`

封装方法：

```python
def add_paragraphs(
    self,
    db: Session,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
```

内部调用：

```python
self.collection.add(
    ids=ids,
    embeddings=embeddings,
    documents=documents,
    metadatas=metadatas,
)
```

当前异步索引主链路使用 `upsert_paragraphs`。因为 Celery 和 Outbox 是至少一次投递，同一任务可能再次执行；稳定 `vector_id` 配合 `upsert` 可以覆盖同一条向量，而不是生成重复数据。

四组数据必须一一对应：

```text
ids[0]
embeddings[0]
documents[0]
metadatas[0]
```

描述的是同一个段落。

例如：

```text
ids[0]         = "vector-1"
embeddings[0]  = [0.12, -0.03, ...]
documents[0]   = "如何上传文档..."
metadatas[0]   = {"knowledge_id": "...", "paragraph_id": "..."}
```

如果顺序错了，会导致：

```text
向量和文本对应不上
metadata 指向错误段落
检索结果回查 SQLite 时错乱
```

## 8. metadata 是什么

metadata 是挂在向量上的业务信息。

本项目写入：

```python
metadatas = [
    {
        "knowledge_id": knowledge_id,
        "document_id": document.id,
        "paragraph_id": paragraph.id,
        "position": paragraph.position,
        "source_type": "paragraph",
    }
    for paragraph in paragraphs
]
```

它的作用有两个。

第一，用来过滤：

```python
where={"knowledge_id": knowledge_id}
```

第二，用来回查业务数据：

```python
paragraph_id = result.metadata.get("paragraph_id")
paragraph = db.get(ParagraphModel, paragraph_id)
```

没有 metadata，Chroma 只能告诉你：

```text
哪个向量相似
```

有了 metadata，系统才能知道：

```text
这个向量属于哪个知识库、哪个文档、哪个段落。
```

## 9. 查询向量：`collection.query`

封装方法：

```python
def search(
    self,
    db: Session,
    knowledge_id: str,
    query_embedding: list[float],
    top_k: int,
) -> list[VectorSearchResult]:
```

内部调用：

```python
result = self.collection.query(
    query_embeddings=[query_embedding],
    n_results=top_k,
    where={"knowledge_id": knowledge_id},
)
```

参数含义：

```text
query_embeddings  查询向量列表
n_results         最多返回多少条
where             metadata 过滤条件
```

本项目里：

```text
query_embedding   用户问题生成的向量
top_k             最多召回段落数
knowledge_id      限制只查当前知识库
```

注意：

```text
query_embeddings 是列表。
即使只查一个问题，也要传 [query_embedding]。
```

## 10. `where` 为什么必须有

本项目所有知识库共用一个 collection。

所以查询时必须加：

```python
where={"knowledge_id": knowledge_id}
```

它表示：

```text
只在当前 knowledge_id 的段落向量里查。
```

如果不加：

```text
A 知识库的问题可能查到 B 知识库的段落
用户看到不属于当前知识库的引用
数据隔离被破坏
```

这是 RAG 系统里非常关键的边界。

记忆：

```text
向量相似度只负责“像不像”
where 负责“能不能查”
```

## 11. Chroma 返回结构为什么要取 `[0]`

代码：

```python
ids = result.get("ids", [[]])[0]
distances = result.get("distances", [[]])[0]
metadatas = result.get("metadatas", [[]])[0]
documents = result.get("documents", [[]])[0]
```

原因：

```text
Chroma 支持一次传多个 query embedding。
所以返回结果是二维结构。
```

例如查询一个问题：

```text
query_embeddings = [query_embedding]
```

返回类似：

```text
ids = [
  ["vector1", "vector2", "vector3"]
]
```

外层列表表示第几个 query。

内层列表表示这个 query 的检索结果。

本项目每次只查一个问题，所以取：

```text
[0]
```

## 12. distance 和 score

Chroma 返回的是：

```text
distance
```

一般理解：

```text
distance 越小，越相似
```

但前端展示通常更习惯：

```text
score 越高，越相似
```

所以本项目转换：

```python
score = 1.0 / (1.0 + float(distance))
```

效果：

```text
distance = 0    -> score = 1
distance = 1    -> score = 0.5
distance = 3    -> score = 0.25
```

这个 score 是简化展示分。

它不是严格概率。

不要理解成：

```text
score = 0.8 就是 80% 正确
```

更准确的理解是：

```text
用于排序和展示的相似度指标。
```

## 13. 为什么还要有 `EmbeddingRefModel`

Chroma 里已经有 `paragraph_id` metadata。

但 SQLite 里仍然有：

```text
EmbeddingRefModel
```

它保存：

```text
knowledge_id
document_id
paragraph_id
problem_id
source_type
vector_id
```

作用：

```text
在业务数据库中保留段落和向量的对应关系
方便后续删除、重建、迁移向量索引
```

例如后续删除文档时，可以：

```text
查 document_id 下所有 embedding_ref
删除 Chroma 对应向量
删除 SQLite 业务数据
```

在 Chroma 模式中，`embedding_ref.embedding` 为空，它主要承担业务引用作用。

在 pgvector 模式中，同一张表的 `embedding` 列保存真实向量：

```text
Chroma 模式      EmbeddingRef 是外部向量引用
pgvector 模式    EmbeddingRef 同时保存引用和真实向量
```

## 14. `delete_by_document`

代码：

```python
def delete_by_document(self, db: Session, document_id: str) -> None:
    self.collection.delete(where={"document_id": document_id})
```

意思是：

```text
删除某个文档对应的全部向量。
```

当前删除和重新索引链路已经使用该能力，同时删除 Chroma 向量和当前 Session 中的 `EmbeddingRefModel`。

关键点：

```text
删除向量也通过 metadata 过滤。
```

## 15. 向量维度要一致

写入同一 Chroma collection 的 embedding 维度必须一致。

本项目默认：

```text
EMBEDDING_DIMENSION = 256
```

如果未来把 HashEmbeddingService 换成真实 embedding 模型，比如 1536 维。

需要注意：

```text
旧 collection 里的 256 维向量不能和 1536 维向量混用
通常要重建对应向量索引
业务数据库里的 embedding_ref 也要同步处理
```

pgvector 模式也要求 ORM `Vector(EMBEDDING_DIMENSION)`、数据库列和生成模型的维度一致。

## 16. 常见知识点

ChromaDB 常见概念：

```text
Client        Chroma 客户端
Collection    一组向量数据
Embedding     向量
Document      向量对应的原始文本
Metadata      向量附带的业务字段
Query         相似度查询
Where         基于 metadata 的过滤条件
Distance      距离，通常越小越相似
Top K         返回最相似的前 K 条
Persistent    数据持久化到本地目录
```

本项目里的对应：

```text
Client        chromadb.PersistentClient
Collection    mini_maxkb_paragraphs
Embedding     HashEmbeddingService 生成的 list[float]
Document      ParagraphModel.content
Metadata      knowledge_id / document_id / paragraph_id / position
Where         {"knowledge_id": knowledge_id}
Top K         ChatRequest.top_k
```

## 17. 排查检索问题时先看什么

如果问答结果不对，先按顺序检查：

```text
1. 文档是否成功上传
2. 段落是否成功切分
3. Chroma 是否写入向量
4. metadata 是否包含正确 knowledge_id
5. 查询时 where 是否带 knowledge_id
6. top_k 是否太小
7. embedding 模型是否能表达语义相似
8. 业务数据库是否能根据 paragraph_id 查回段落
9. source_type=problem 时是否存在有效 problem_id 和 mapping
```

不要一开始就怀疑大模型。

RAG 的很多问题发生在：

```text
切分
向量化
检索
metadata 对齐
```

## 18. 最小记忆模型

```text
ChromaDB = 保存向量并做相似度查询
ChromaEmbeddingRepository = EmbeddingRepository 的本地实现
collection = 一组向量数据
embedding = 用来比较相似度的数字列表
metadata = 让向量能回到业务对象
where = 数据隔离过滤条件
distance 小 = 更相似
score 大 = 更相似
```

Chroma 不是业务层的固定依赖。业务层依赖 `EmbeddingRepository`，生产 PostgreSQL 模式可以替换为 pgvector。
