# Mini MaxKB RAG 学习文档索引

## 1. 建议阅读顺序

先读主链路，再读分层，再读每个技术点。

```text
1. rag-core-flow.md
   先理解完整 RAG 链路：上传 -> 切分 -> 向量化 -> 检索 -> 回答。

2. project-layering-learning.md
   理解 api / services / storage / models / schemas / config / database 各层职责。

3. fastapi-api-learning.md
   理解接口路径、请求参数、response_model、HTTPException 和 UploadFile。

4. fastapi-dependency-learning.md
   理解 Depends(get_db) 如何给接口函数注入数据库会话。

5. sqlalchemy-session-learning.md
   理解 engine、SessionLocal、Session、Model、select、flush、commit。

6. pydantic-schema-learning.md
   理解 API 入参和出参为什么用 Schema，以及 Field 校验怎么生效。

7. text-chunking-learning.md
   理解为什么要把文档切成 chunk/paragraph，以及 chunk_size、overlap 的影响。

8. embedding-learning.md
   理解文本向量是什么，以及本项目的 HashEmbeddingService。

9. chromadb-learning.md
   理解 ChromaDB、collection、metadata、where、distance 和 score。

10. retrieval-flow-learning.md
    理解 retrieve_paragraphs 如何把向量检索结果转回业务段落。
```

## 2. 每篇文档对应的核心问题

```text
rag-core-flow.md
这个项目的 RAG 完整链路是什么？

project-layering-learning.md
每个目录和文件负责什么？

fastapi-api-learning.md
HTTP 请求如何进入后端业务代码？

fastapi-dependency-learning.md
db、embedding_service、vector_store 这些参数是谁传进来的？

sqlalchemy-session-learning.md
业务代码如何通过 Session 读写 SQLite？

pydantic-schema-learning.md
接口请求和响应为什么需要 Schema？

text-chunking-learning.md
文档为什么要切分，切分参数如何影响检索？

embedding-learning.md
文本为什么能变成向量，向量在入库和问答中怎么用？

chromadb-learning.md
向量如何保存和查询，metadata 如何支撑业务回查？

retrieval-flow-learning.md
问题如何召回段落，召回结果如何进入回答生成？
```

## 3. 按代码链路阅读

如果想从一次“上传文档”开始看：

```text
backend/app/api/document_api.py
-> backend/app/services/document_service.py
-> backend/app/storage/file_storage.py
-> backend/app/services/chunk_service.py
-> backend/app/services/embedding_service.py
-> backend/app/storage/vector_store.py
-> backend/app/models.py
```

对应文档：

```text
fastapi-api-learning.md
project-layering-learning.md
text-chunking-learning.md
embedding-learning.md
chromadb-learning.md
sqlalchemy-session-learning.md
```

如果想从一次“知识库问答”开始看：

```text
backend/app/api/chat_api.py
-> backend/app/services/retrieval_service.py
-> backend/app/services/embedding_service.py
-> backend/app/storage/vector_store.py
-> backend/app/services/chat_service.py
-> backend/app/schemas.py
```

对应文档：

```text
fastapi-api-learning.md
fastapi-dependency-learning.md
retrieval-flow-learning.md
embedding-learning.md
chromadb-learning.md
pydantic-schema-learning.md
```

## 4. 最小学习路线

如果只想先跑通主干，按这个顺序：

```text
rag-core-flow.md
text-chunking-learning.md
embedding-learning.md
chromadb-learning.md
retrieval-flow-learning.md
```

如果想理解后端工程结构，按这个顺序：

```text
project-layering-learning.md
fastapi-api-learning.md
fastapi-dependency-learning.md
sqlalchemy-session-learning.md
pydantic-schema-learning.md
config-and-runtime-learning.md
```

如果想排查问答效果，优先看：

```text
text-chunking-learning.md
embedding-learning.md
chromadb-learning.md
retrieval-flow-learning.md
```
