# RAG 主链路学习笔记

## 1. RAG 解决什么问题

大模型本身不一定知道你的私有文档。

例如你上传了一份项目说明：

```text
Mini MaxKB RAG 的向量库使用 ChromaDB。
```

用户随后提问：

```text
这个项目用什么向量库？
```

如果只把问题直接丢给模型，模型可能不知道这份本地文档。

RAG 的做法是：

```text
先从你的知识库里找相关资料
再把资料和问题一起交给模型回答
```

所以 RAG 的核心不是“让模型记住所有知识”，而是：

```text
让模型在回答前先查资料。
```

## 2. RAG 三个核心动作

RAG 可以拆成三个动作。

第一步：索引。

```text
把文档处理成可以被检索的数据。
```

第二步：检索。

```text
根据用户问题，从索引里找相关段落。
```

第三步：生成。

```text
把问题和相关段落放进 prompt，让模型基于资料回答。
```

对应英文：

```text
Retrieval    检索
Augmented    增强
Generation   生成
```

其中 “Augmented” 的意思是：

```text
模型回答时不是只靠自身参数，而是被外部检索资料增强。
```

## 3. 本项目主链路

这个项目的完整流程是：

```text
创建知识库
-> 上传文档
-> 保存原始文件
-> 读取文本
-> 文本切分
-> 段落入库
-> 生成段落向量
-> 向量写入 Chroma
-> 用户提问
-> 问题向量化
-> Chroma 检索相似段落
-> 回 SQLite 查段落和文档
-> 组装 prompt
-> 调用模型生成回答
-> 返回 answer + references
```

可以拆成两条链路：

```text
文档入库链路：上传 -> 切分 -> 向量化 -> 存储
问答检索链路：提问 -> 向量化 -> 检索 -> 生成
```

一句话：

```text
入库是建索引，问答是查索引。
```

## 4. 本项目中的代码入口

API 入口：

```text
backend/app/api/knowledge_api.py    创建和查询知识库
backend/app/api/document_api.py     上传文档、查询文档、查询段落
backend/app/api/chat_api.py         知识库问答
```

业务服务：

```text
backend/app/services/knowledge_service.py    知识库增查
backend/app/services/document_service.py     文档入库主流程
backend/app/services/chunk_service.py        文本切分
backend/app/services/embedding_service.py    文本转向量
backend/app/services/retrieval_service.py    检索段落
backend/app/services/chat_service.py         生成回答
```

存储封装：

```text
backend/app/storage/file_storage.py    原始文件保存和读取
backend/app/storage/vector_store.py    ChromaDB 向量读写
```

数据结构：

```text
backend/app/models.py     SQLite 表结构
backend/app/schemas.py    API 入参和出参
```

## 5. 创建知识库做了什么

接口：

```text
POST /api/knowledges
```

代码入口：

```text
backend/app/api/knowledge_api.py
backend/app/services/knowledge_service.py
```

核心逻辑：

```python
knowledge = KnowledgeModel(
    name=payload.name,
    description=payload.description,
)
db.add(knowledge)
db.commit()
db.refresh(knowledge)
```

创建知识库只是创建一个顶层容器。

它本身还没有文档，也没有向量。

后续文档、段落、向量引用都会带上：

```text
knowledge_id
```

这个字段用来说明：

```text
这条数据属于哪个知识库。
```

## 6. 上传文档做了什么

接口：

```text
POST /api/knowledges/{knowledge_id}/documents
```

代码入口：

```text
backend/app/api/document_api.py
backend/app/services/document_service.py
```

核心流程在 `upload_document`：

```text
检查知识库是否存在
-> 保存上传文件
-> 读取文本
-> 切分文本
-> 创建 DocumentModel
-> 创建 ParagraphModel
-> 生成 embedding
-> 写入 Chroma
-> 创建 EmbeddingRefModel
-> commit
```

关键点：

```text
DocumentModel      记录文档本身
ParagraphModel     记录切分后的段落
EmbeddingRefModel  记录 paragraph_id 和 vector_id 的对应关系
Chroma             保存真正的向量
```

## 7. 为什么不直接检索整篇文档

因为整篇文档通常太粗。

例如一篇文档有 5000 字，只里面一小段和问题相关。

如果把整篇文档作为一个检索单位，会有几个问题：

```text
相似度不够精确
prompt 很容易过长
引用来源不清楚
模型需要在大量无关文本里找答案
```

所以项目会把文档切成 paragraph。

在 RAG 里：

```text
paragraph 是检索单位
document 是管理单位
knowledge 是隔离单位
```

## 8. 为什么需要 Embedding

用户问题和段落都是文本。

向量数据库不能直接理解中文句子。

所以要先做：

```text
文本 -> embedding 向量
```

入库时：

```text
paragraph.content -> paragraph embedding
```

提问时：

```text
question -> query embedding
```

然后才能比较：

```text
query embedding 和哪些 paragraph embedding 最相似
```

## 9. SQLite 和 Chroma 的分工

这个项目用了两个存储。

SQLite 保存业务数据：

```text
knowledge
document
paragraph
embedding_ref
```

Chroma 保存向量数据：

```text
vector_id
embedding
document text
metadata
```

为什么要分开？

```text
SQLite 适合查业务关系
Chroma 适合查向量相似度
```

例如问答时，Chroma 先返回：

```text
vector_id
metadata.paragraph_id
distance
```

然后项目再用 `paragraph_id` 回 SQLite 查询：

```text
ParagraphModel.content
DocumentModel.name
```

这样返回给前端的引用来源才完整。

## 10. 问答接口做了什么

接口：

```text
POST /api/knowledges/{knowledge_id}/chat
```

代码入口：

```text
backend/app/api/chat_api.py
```

核心逻辑：

```python
retrieved = retrieve_paragraphs(
    db=db,
    knowledge_id=knowledge_id,
    question=payload.question,
    top_k=top_k,
    embedding_service=embedding_service,
    vector_store=vector_store,
)

return await answer_question(payload.question, retrieved)
```

这说明问答接口本身不直接做复杂业务。

它只负责：

```text
校验知识库
读取 top_k
调用检索服务
调用回答服务
把结果返回给前端
```

## 11. 检索服务做了什么

代码入口：

```text
backend/app/services/retrieval_service.py
```

核心逻辑：

```python
query_embedding = embedding_service.embed_text(question)
vector_results = vector_store.search(
    knowledge_id=knowledge_id,
    query_embedding=query_embedding,
    top_k=top_k,
)
```

可以理解为：

```text
把问题变成向量
-> 拿问题向量查 Chroma
-> 得到相似段落的 metadata
-> 根据 paragraph_id 回 SQLite 查真实段落
```

这里最关键的过滤条件是：

```python
where={"knowledge_id": knowledge_id}
```

没有它，不同知识库的数据会互相串。

## 12. 回答服务做了什么

代码入口：

```text
backend/app/services/chat_service.py
```

它先把检索结果转换成引用：

```python
references = build_references(retrieved)
```

然后分两种情况。

配置了 `OPENAI_API_KEY`：

```text
调用 OpenAI-compatible Chat API
```

没有配置 `OPENAI_API_KEY`：

```text
返回 fallback 简化回答
```

fallback 的意义不是回答质量高，而是：

```text
不用配置大模型，也能验证 RAG 工程链路。
```

## 13. references 为什么重要

RAG 不应该只返回一段 answer。

它还应该告诉用户：

```text
答案依据来自哪份文档
来自哪个段落
相似度大概是多少
```

本项目响应结构：

```python
class ChatResponse(BaseModel):
    answer: str
    references: List[ReferenceRead]
```

每条引用包含：

```text
document_id
document_name
paragraph_id
content
score
```

引用来源的价值：

```text
方便用户核验答案
方便调试检索质量
方便后续做高亮、跳转、溯源
```

## 14. top_k 是什么

`top_k` 表示最多召回多少段。

例如：

```text
top_k = 4
```

意思是：

```text
从当前知识库中找出最相似的 4 个段落。
```

太小：

```text
可能漏掉关键上下文
```

太大：

```text
prompt 变长
噪声变多
模型更容易被不相关内容干扰
```

本项目默认值来自：

```text
DEFAULT_TOP_K = 4
```

## 15. RAG 链路里最容易出问题的地方

第一类：文档没有切好。

```text
chunk 太大，检索不准
chunk 太小，上下文断裂
overlap 不合理，关键句被切断
```

第二类：embedding 效果不好。

```text
问题和段落语义相近，但向量距离不近
同义词召回差
中文语义理解弱
```

第三类：向量库过滤不严。

```text
没有按 knowledge_id 过滤
导致 A 知识库检索到 B 知识库内容
```

第四类：prompt 约束不清楚。

```text
没有要求模型只基于引用回答
模型可能补充未被检索到的信息
```

第五类：索引和业务库不一致。

```text
SQLite 里有 paragraph，但 Chroma 没有向量
Chroma 有向量，但 SQLite 查不到 paragraph
```

## 16. 读代码时的顺序

建议按这个顺序读：

```text
1. backend/app/main.py
   看应用如何启动、router 如何注册。

2. backend/app/api/document_api.py
   看上传文档接口怎么进入入库流程。

3. backend/app/services/document_service.py
   看保存文件、切分、向量化、写入数据库和 Chroma。

4. backend/app/api/chat_api.py
   看提问接口怎么进入问答流程。

5. backend/app/services/retrieval_service.py
   看问题向量如何检索段落。

6. backend/app/services/chat_service.py
   看引用如何组成 prompt 和回答。
```

## 17. 常用知识点

RAG 学习时常见概念：

```text
Knowledge      知识库，数据隔离的顶层容器
Document       文档，用户上传的文件
Chunk          文本块，检索单位
Paragraph      本项目里的 chunk
Embedding      文本向量
Vector Store   向量库，保存和检索 embedding
Metadata       向量附带的业务信息
Top K          返回最相似的前 K 条
Prompt         发给模型的上下文和指令
Reference      回答引用来源
```

这些概念在项目中的对应关系：

```text
Knowledge      KnowledgeModel
Document       DocumentModel
Chunk          TextChunk / ParagraphModel
Embedding      HashEmbeddingService 输出的 list[float]
Vector Store   ChromaVectorStore
Metadata       knowledge_id / document_id / paragraph_id / position
Reference      ReferenceRead
```

## 18. 最小记忆模型

```text
RAG = 先检索，再生成
入库 = 把文档变成段落索引
问答 = 把问题变成向量去查段落
SQLite = 存业务数据
Chroma = 存向量数据
references = 告诉用户答案依据
```
