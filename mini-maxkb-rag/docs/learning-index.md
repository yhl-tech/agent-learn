# Mini MaxKB RAG 学习文档索引

## 1. 建议阅读顺序

按“工程基础 -> RAG 主链路 -> 增强检索 -> 存储演进 -> 异步可靠性”阅读。

```text
1. rag-core-flow.md
   建立全局地图：异步入库 -> 检索 -> 回答。

2. project-layering-learning.md
   理解 api / services / repositories / storage / tasks / models 等层的职责。

3. fastapi-api-learning.md
   理解接口路径、请求参数、response_model、HTTPException 和 UploadFile。

4. fastapi-dependency-learning.md
   理解 FastAPI 如何注入 Session、EmbeddingService 和 EmbeddingRepository。

5. pydantic-schema-learning.md
   理解 API 入参、出参和 Field 校验。

6. database-orm-basics-learning.md
   理解表、行、字段如何映射为 ORM 模型类、属性和实例。

7. sqlalchemy-session-learning.md
   理解 engine、SessionLocal、Session、Model、select、flush、commit。

8. config-and-runtime-learning.md
   理解环境变量、运行时目录和配置边界。

9. text-chunking-learning.md
   理解为什么要把文档切成 chunk/paragraph，以及 chunk_size、overlap 的影响。

10. embedding-learning.md
   理解文本向量是什么，以及本项目的 HashEmbeddingService。

11. chromadb-learning.md
   理解本地 Chroma 实现、collection、metadata、distance 和 score。

12. retrieval-flow-learning.md
    理解三种检索模式如何形成统一候选并回到业务段落。

13. problem-enhancement-learning.md
    理解问题向量如何通过 Mapping 回到原始段落。

14. hybrid-retrieval-learning.md
    理解向量检索、关键词检索和 weighted RRF。

15. database-migration-pgvector-learning.md
    理解 Alembic、PostgreSQL、pgvector、tsvector 和 Repository。

16. async-task-outbox-learning.md
    理解 Celery、Redis、Transactional Outbox、幂等、租约和重试。
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
db、embedding_service、vector_store 这些依赖是谁创建和传入的？

pydantic-schema-learning.md
接口请求和响应为什么需要 Schema？

database-orm-basics-learning.md
当前 11 张表如何对应 ORM 模型、字段和关系？

sqlalchemy-session-learning.md
业务代码如何通过 Session 管理 SQLite/PostgreSQL 事务？

config-and-runtime-learning.md
配置值和运行时文件从哪里来？

text-chunking-learning.md
文档为什么要切分，切分参数如何影响检索？

embedding-learning.md
文本为什么能变成向量，向量在入库和问答中怎么用？

chromadb-learning.md
本地 Chroma 如何保存向量，metadata 如何支撑业务回查？

retrieval-flow-learning.md
向量、关键词和问题增强候选如何变成最终引用？

problem-enhancement-learning.md
为什么给段落生成问题，命中问题后怎样回到原文？

hybrid-retrieval-learning.md
不同量纲的向量分数和关键词分数如何通过 RRF 融合？

database-migration-pgvector-learning.md
数据库结构如何演进，Chroma 如何抽象并切换到 pgvector？

async-task-outbox-learning.md
上传任务如何可靠投递、避免重复执行并从故障中恢复？
```

## 3. 按代码链路阅读

### 3.1 文档上传与异步索引

```text
backend/app/api/document_api.py
-> backend/app/services/document_service.py
-> backend/app/storage/file_storage.py
-> backend/app/services/outbox_service.py
-> backend/app/tasks/document_tasks.py
-> backend/app/services/task_service.py
-> backend/app/services/chunk_service.py
-> backend/app/services/embedding_service.py
-> backend/app/repositories/embedding_repository.py
-> backend/app/models.py
```

对应文档：

```text
fastapi-api-learning.md
project-layering-learning.md
database-orm-basics-learning.md
sqlalchemy-session-learning.md
text-chunking-learning.md
embedding-learning.md
async-task-outbox-learning.md
```

### 3.2 知识库问答与混合检索

```text
backend/app/api/chat_api.py
-> backend/app/services/retrieval_service.py
-> backend/app/services/embedding_service.py
-> backend/app/repositories/embedding_repository.py
-> backend/app/repositories/paragraph_repository.py
-> backend/app/services/rerank_service.py
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
problem-enhancement-learning.md
hybrid-retrieval-learning.md
pydantic-schema-learning.md
```

### 3.3 按 v0.4 至 v0.7 版本阅读

```text
v0.4 增强检索
backend/app/services/retrieval_service.py
-> backend/app/repositories/paragraph_repository.py
-> backend/app/services/rerank_service.py
-> hybrid-retrieval-learning.md
-> problem-enhancement-learning.md

v0.5 PostgreSQL 与 pgvector
backend/app/config.py
-> backend/app/repositories/embedding_repository.py
-> backend/alembic/versions/0001_v05_postgresql_storage.py
-> database-migration-pgvector-learning.md

v0.6 持久化任务
backend/app/api/document_api.py
-> backend/app/services/task_service.py
-> backend/alembic/versions/0002_v06_background_tasks.py

v0.7 可靠任务投递
backend/app/services/outbox_service.py
-> backend/app/repositories/outbox_repository.py
-> backend/app/celery_app.py
-> backend/alembic/versions/0003_v07_celery_outbox.py
-> async-task-outbox-learning.md
```

## 4. 按目标选择最小路线

只理解 RAG 主干：

```text
rag-core-flow.md
text-chunking-learning.md
embedding-learning.md
retrieval-flow-learning.md
```

理解后端工程基础：

```text
project-layering-learning.md
fastapi-api-learning.md
fastapi-dependency-learning.md
pydantic-schema-learning.md
database-orm-basics-learning.md
sqlalchemy-session-learning.md
config-and-runtime-learning.md
```

排查检索效果：

```text
text-chunking-learning.md
embedding-learning.md
retrieval-flow-learning.md
problem-enhancement-learning.md
hybrid-retrieval-learning.md
```

理解生产化基础：

```text
database-migration-pgvector-learning.md
async-task-outbox-learning.md
```
