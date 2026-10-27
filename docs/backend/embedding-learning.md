# Embedding 学习笔记

## 1. Embedding 解决什么问题

计算机不能直接理解一段文字的语义。

例如：

```text
如何上传文档？
怎么导入文件？
文档上传失败怎么办？
```

这几句话字面不完全一样，但语义上都和“上传文档”有关。

Embedding 的作用是：

```text
把文本转换成一组数字，让计算机可以用数学方式比较文本相似度。
```

例子：

```text
文本：如何上传文档？
向量：[0.12, -0.03, 0.44, ...]
```

一旦文本变成向量，就可以计算：

```text
两个文本是否相似
一个问题最接近哪些段落
哪些知识内容应该被召回
```

一句话：

```text
Embedding 是 RAG 中“检索”的基础。
```

## 2. Embedding 在 RAG 中的位置

RAG 可以拆成两个阶段。

入库阶段：

```text
上传文档
-> 文本切分成 paragraph
-> 每个 paragraph 生成 embedding
-> embedding 写入向量库
```

问答阶段：

```text
用户提问
-> 问题生成 embedding
-> 用问题 embedding 去向量库查相似 paragraph
-> 把查到的 paragraph 交给模型回答
```

所以同一个 embedding 服务会在两个地方用到：

```text
文档入库时：段落文本 -> 段落向量
用户提问时：问题文本 -> 问题向量
```

## 3. 本项目中的代码位置

Embedding 服务定义在：

```text
backend/app/services/embedding_service.py
```

核心类：

```python
class HashEmbeddingService:
```

它提供两个主要方法：

```python
embed_text(text: str) -> list[float]
embed_texts(texts: list[str]) -> list[list[float]]
```

含义：

```text
embed_text   单条文本转向量
embed_texts  多条文本批量转向量
```

## 4. 入库时怎么用 Embedding

在 `document_service.py` 中，文档会先被切成多个 paragraph。

然后执行：

```python
embeddings = embedding_service.embed_texts(
    [paragraph.content for paragraph in paragraphs]
)
```

这行代码的含义：

```text
取出每个 paragraph 的 content
-> 批量生成 embeddings
-> 得到 list[list[float]]
```

为什么要批量？

```text
本地 HashEmbeddingService 里批量只是循环
但以后换成真实 embedding API 时，批量请求通常更高效
```

随后这些向量会通过统一仓库写入当前向量后端：

```python
vector_store.upsert_paragraphs(
    db=db,
    ids=vector_ids,
    embeddings=embeddings,
    documents=[paragraph.content for paragraph in paragraphs],
    metadatas=metadatas,
)
```

本地默认模式：

```text
SQLite 保存 paragraph 业务数据
Chroma 保存 paragraph 对应的 embedding
```

PostgreSQL 模式：

```text
ParagraphModel 保存段落
EmbeddingRefModel.embedding 保存 pgvector 向量
两者共享同一个数据库事务
```

业务代码只依赖 `EmbeddingRepository`，不直接决定使用哪一种后端。

## 5. 问答时怎么用 Embedding

在 `retrieval_service.py` 中：

```python
query_embedding = embedding_service.embed_text(question)
```

这行代码的含义：

```text
把用户问题转换成一个查询向量
```

然后：

```python
vector_results = vector_store.search(
    db=db,
    knowledge_id=knowledge_id,
    query_embedding=query_embedding,
    top_k=top_k,
)
```

含义：

```text
用问题向量 query_embedding
去当前向量后端查最相似的段落或问题向量
只查当前 knowledge_id 下的数据
最多返回 top_k 条
```

这就是 RAG 的“R”：Retrieval。

## 6. 本项目为什么不用真实 Embedding 模型

真实项目一般会用：

```text
OpenAI Embedding
火山 Embedding
Ollama 本地模型
sentence-transformers
bge / e5 等开源 embedding 模型
```

但这个学习项目第一版用了：

```python
HashEmbeddingService
```

原因：

```text
不需要 API Key
不需要网络
不需要额外模型下载
每次运行结果稳定
方便先理解工程链路
```

它的定位不是“效果最好”，而是“让 RAG 主链路先跑通”。

## 7. HashEmbeddingService 的算法思路

代码大致做了五步。

第一步：分词。

```python
tokens = self._tokenize(text)
```

把文本拆成 token。

例如：

```text
输入：如何上传文档
tokens：["如何上传文档"]
```

英文会按单词拆：

```text
输入：upload document error
tokens：["upload", "document", "error"]
```

第二步：创建固定长度向量。

```python
vector = [0.0] * self.dimension
```

默认维度来自：

```python
EMBEDDING_DIMENSION = 256
```

所以一段文本会变成：

```text
长度为 256 的数字列表
```

第三步：对每个 token 做 hash。

```python
digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
value = int.from_bytes(digest, byteorder="big", signed=False)
```

作用：

```text
把 token 稳定地转换成一个整数
```

稳定的意思是：

```text
同一个 token 每次都会得到同一个 value
```

第四步：把 token 映射到某个向量维度。

```python
index = value % self.dimension
```

如果 `dimension = 256`，那么 `index` 一定在：

```text
0 到 255
```

也就是说：

```text
每个 token 会落到向量中的某一格
```

第五步：累加权重。

```python
sign = 1.0 if value % 2 == 0 else -1.0
vector[index] += sign
```

这里不是简单加 1，而是有时加正数，有时加负数。

目的：

```text
减少所有 token 都往正方向堆叠带来的碰撞偏差
```

最后做归一化：

```python
return self._normalize(vector)
```

## 8. 为什么要 normalize

归一化代码：

```python
norm = math.sqrt(sum(value * value for value in vector))
return [value / norm for value in vector]
```

它的作用是把向量长度缩放到同一尺度。

为什么需要？

如果不归一化，长文本因为 token 更多，向量数值可能天然更大。

这样检索时可能出现：

```text
长段落更容易被认为相关
短段落更容易被压下去
```

归一化后，比较更关注“方向是否接近”，而不是“文本是不是更长”。

一句话：

```text
normalize 让不同长度文本更公平地比较相似度。
```

## 9. HashEmbedding 和真实 Embedding 的区别

HashEmbeddingService 更像一个工程演示版。

它能做到：

```text
相同词出现时，向量更可能相似
文本可被转换成固定维度向量
可以接入 Chroma 或 pgvector 完成检索链路
```

它做不到：

```text
理解深层语义
理解同义词
理解复杂上下文
跨语言语义匹配
高质量召回
```

例如：

```text
“上传文档”
“导入资料”
```

真实 embedding 模型可能知道它们语义接近。

HashEmbeddingService 只看 token hash，本身不真正理解语义。

## 10. 替换成真实 Embedding 时要注意什么

如果以后替换真实模型，优先保持接口不变：

```python
embed_text(text: str) -> list[float]
embed_texts(texts: list[str]) -> list[list[float]]
```

这样其他业务代码不用改。

需要注意：

```text
向量维度必须和当前向量后端的既有索引或列定义一致
旧向量通常需要重建
批量接口要处理限流和失败重试
模型变更会影响检索效果
中文场景要选中文效果好的 embedding 模型
```

例如从 256 维 HashEmbedding 换成 1536 维真实模型后，旧数据不能直接混用。

通常要：

```text
清空旧向量
重新读取 paragraph
重新生成 embedding
重新写入当前向量后端
```

## 11. 和向量仓库的关系

Embedding 服务只负责：

```text
文本 -> 向量
```

`EmbeddingRepository` 负责：

```text
保存向量
根据查询向量查相似向量
返回统一的 vector_id、score、metadata、document
```

职责边界：

```text
embedding_service 不知道向量存在哪里
vector_store 不负责生成向量
retrieval_service 负责把两者串起来
```

对应关系：

```text
HashEmbeddingService.embed_text     生成问题向量
HashEmbeddingService.embed_texts    生成段落向量
EmbeddingRepository.upsert_paragraphs 保存段落或问题向量
EmbeddingRepository.search            查询相似向量
```

具体实现：

```text
ChromaEmbeddingRepository     本地 SQLite 模式
PostgresEmbeddingRepository   PostgreSQL + pgvector 模式
```

## 12. 读代码时的重点问题

看 embedding 相关代码时，重点问这几个问题：

```text
这段文本什么时候被转成向量？
生成的是单条向量还是批量向量？
向量维度是多少？
向量写到了哪里？
查询时用的是哪个向量？
检索结果怎么回到业务数据？
```

在本项目里的答案：

```text
文档上传时，paragraph.content 被批量转成向量
用户提问时，question 被转成查询向量
向量默认 256 维
向量写入 Chroma 或 embedding_ref.embedding
查询时用 question 的向量
段落向量通过 paragraph_id 回源
问题向量通过 problem_id -> mapping -> paragraph_id 回源
```

## 13. 最小记忆模型

```text
Embedding = 文本的数字表示
段落 embedding = 用来建立索引
问题 embedding = 用来检索索引
向量库 = 保存和查询 embedding
RAG = 用问题向量找段落向量，再把段落交给模型回答
```
