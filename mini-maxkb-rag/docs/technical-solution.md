# Mini MaxKB RAG 问答系统技术方案

## 1. 项目目标

本项目用于通过动手实现一个简化版知识库问答系统，理解 MaxKB 中知识库模块的核心链路。

第一阶段目标是跑通最小 RAG 流程：

```text
创建知识库 -> 上传文档 -> 文本切分 -> 生成向量 -> 用户提问 -> 检索段落 -> 生成回答
```

对应 MaxKB 源码中的核心模型：

```text
Knowledge  -> 知识库
Document   -> 文档
Paragraph  -> 段落
Embedding  -> 向量索引
File       -> 原始文件
```

第一版先不追求完整复刻 MaxKB，而是优先把主链路做清楚、跑起来、能调试。

## 2. 总体架构

推荐采用前后端分离架构：

```text
React 前端
  -> 调用 FastAPI 接口

FastAPI 后端
  -> 管理知识库、文档、段落
  -> 调用 embedding 模型生成向量
  -> 调用向量库执行相似度检索
  -> 调用 LLM 生成回答

存储层
  -> SQLite 保存业务数据
  -> Chroma 保存向量数据
  -> 本地磁盘保存原始文件
```

## 3. 后端技术方案

### 3.1 技术栈

后端推荐：

```text
Python
FastAPI
SQLAlchemy
SQLite
Chroma
OpenAI-compatible API 或本地 embedding 模型
```

选择 FastAPI 的原因：

- 启动成本低，适合先理解 RAG 主链路。
- API 定义清晰，方便前端联调。
- 不需要一开始处理 Django 项目里的权限、迁移、任务队列等复杂上下文。

SQLite 用于保存业务表，Chroma 用于保存向量索引。后续如果要更贴近 MaxKB，可以再迁移到 Django ORM 和 PostgreSQL。

### 3.2 后端目录结构

建议目录：

```text
backend/
  app/
    main.py
    database.py
    models.py
    schemas.py
    api/
      knowledge_api.py
      document_api.py
      chat_api.py
    services/
      knowledge_service.py
      document_service.py
      chunk_service.py
      embedding_service.py
      retrieval_service.py
      chat_service.py
    storage/
      file_storage.py
      vector_store.py
  data/
    files/
    chroma/
    app.db
```

模块职责：

```text
knowledge_service.py
  管理知识库创建、查询。

document_service.py
  管理文档上传、读取、入库。

chunk_service.py
  将文档文本切分成段落。

embedding_service.py
  将段落文本转成向量。

retrieval_service.py
  根据用户问题检索相关段落。

chat_service.py
  组装 prompt，调用大模型生成回答。

file_storage.py
  保存原始上传文件。

vector_store.py
  封装 Chroma 的写入和查询。
```

## 4. 前端技术方案

### 4.1 技术栈

前端推荐：

```text
React
Vite
TypeScript
Ant Design
fetch 或 axios
```

选择 Ant Design 的原因：

- 管理后台类界面组件完整。
- 表格、上传、列表、输入框、消息提示都可以快速落地。
- 和知识库工作台类产品的交互形态比较匹配。

### 4.2 页面结构

第一版只做一个工作台页面：

```text
左侧：知识库列表
中间：文档列表和上传区
右侧：问答区
```

核心交互：

- 创建知识库。
- 选择知识库。
- 上传 `.txt` / `.md` 文档。
- 查看文档列表。
- 输入问题。
- 查看回答。
- 查看引用段落。

### 4.3 前端目录结构

建议目录：

```text
frontend/
  src/
    main.tsx
    App.tsx
    api/
      client.ts
      knowledge.ts
      document.ts
      chat.ts
    components/
      KnowledgeSidebar.tsx
      DocumentPanel.tsx
      ChatPanel.tsx
      ReferenceList.tsx
    types/
      knowledge.ts
      document.ts
      chat.ts
```

## 5. 数据模型设计

第一版简化为 4 张业务表：

### 5.1 knowledge

表示一个知识库。

```text
id
name
description
created_at
updated_at
```

对应 MaxKB：

```text
Knowledge
```

### 5.2 document

表示知识库下的一份文档。

```text
id
knowledge_id
name
file_path
char_length
created_at
updated_at
```

对应 MaxKB：

```text
Document
File
```

第一版不单独建 `file` 表，先把原始文件路径保存在 `document.file_path`。

### 5.3 paragraph

表示文档切分后的段落。

```text
id
knowledge_id
document_id
content
position
created_at
updated_at
```

对应 MaxKB：

```text
Paragraph
```

### 5.4 embedding_ref

记录段落与向量库中的向量 ID 的对应关系。

```text
id
knowledge_id
document_id
paragraph_id
vector_id
created_at
updated_at
```

对应 MaxKB：

```text
Embedding
```

向量本身存放在 Chroma 中，不直接存在 SQLite。

## 6. API 设计

第一版 API 控制在 5 个核心接口。

### 6.1 创建知识库

```http
POST /api/knowledges
```

请求：

```json
{
  "name": "我的知识库",
  "description": "用于测试 RAG"
}
```

返回：

```json
{
  "id": "knowledge_id",
  "name": "我的知识库",
  "description": "用于测试 RAG"
}
```

### 6.2 查询知识库列表

```http
GET /api/knowledges
```

### 6.3 上传文档

```http
POST /api/knowledges/{knowledge_id}/documents
```

支持格式：

```text
.txt
.md
```

处理流程：

```text
保存原始文件
-> 读取文本
-> 切分段落
-> 写入 paragraph 表
-> 生成 embedding
-> 写入 Chroma
-> 写入 embedding_ref 表
```

### 6.4 查询文档列表

```http
GET /api/knowledges/{knowledge_id}/documents
```

### 6.5 知识库问答

```http
POST /api/knowledges/{knowledge_id}/chat
```

请求：

```json
{
  "question": "这份文档讲了什么？"
}
```

返回：

```json
{
  "answer": "回答内容",
  "references": [
    {
      "document_id": "document_id",
      "document_name": "example.md",
      "paragraph_id": "paragraph_id",
      "content": "命中的段落内容",
      "score": 0.82
    }
  ]
}
```

## 7. RAG 主链路

### 7.1 文档入库链路

```text
用户上传文档
-> 后端保存文件
-> 读取纯文本
-> 按长度和换行切分段落
-> 保存段落到 SQLite
-> 调用 embedding 模型生成向量
-> 写入 Chroma
-> 保存向量引用关系
```

### 7.2 问答链路

```text
用户输入问题
-> 对问题生成 embedding
-> 在 Chroma 中按 knowledge_id 检索相似段落
-> 读取段落和文档信息
-> 组装 prompt
-> 调用 LLM
-> 返回回答和引用来源
```

## 8. 第一版暂不实现

为了避免范围过大，第一版先不做：

```text
用户登录
工作空间权限
知识库文件夹树
异步任务队列
PDF / Word 解析
问题增强召回
全文检索
混合检索
模型管理页面
知识库导入导出
文档删除后的向量清理
```

这些能力可以在主链路跑通后逐步补齐。

## 9. 迭代路线

### 9.1 v0.1 跑通主链路

目标：

```text
先完成一个可以使用的最小知识库问答系统。
```

功能范围：

```text
创建知识库
上传 txt/md
文本切分
向量入库
提问检索
回答带引用
```

技术方案：

```text
FastAPI 提供接口
SQLite 保存 knowledge/document/paragraph/embedding_ref
Chroma 保存向量
本地磁盘保存原始文件
React 工作台完成基础交互
```

验收标准：

```text
可以创建知识库
可以上传一个 Markdown 文档
后端能切出段落并写入向量库
用户提问后能返回回答
回答中能展示引用段落
```

### 9.2 v0.2 二期：补齐基础管理能力

目标：

```text
把 v0.1 从“能跑通”补成“可日常调试和管理”的状态。
```

功能范围：

```text
删除文档
重新索引文档
查看文档段落
上传进度和处理状态展示
接口异常提示
空知识库、空文档、无检索结果等空状态
```

后端调整：

```text
document 增加 status 字段，记录文档处理状态
paragraph 增加 chunk_length 或 token_count，便于观察切分效果
增加文档删除接口，删除 SQLite 数据和 Chroma 向量
增加文档重新索引接口，重新执行切分和向量写入
```

建议状态设计：

```text
PENDING    等待处理
PROCESSING 处理中
SUCCESS    处理成功
FAILED     处理失败
```

新增 API：

```http
GET    /api/documents/{document_id}/paragraphs
DELETE /api/documents/{document_id}
POST   /api/documents/{document_id}/reindex
```

前端调整：

```text
文档列表展示状态、字符数、段落数
文档详情支持查看切分后的段落
上传后展示处理结果
删除和重新索引使用确认弹窗
chat 区域展示“无引用结果”的明确状态
```

验收标准：

```text
可以删除文档，并确认向量库中对应数据也被删除
可以重新索引文档
可以查看每个文档切出来的段落
上传失败时前端能看到明确错误原因
```

### 9.3 v0.3 三期：对齐 MaxKB 核心数据模型

目标：

```text
开始把项目从简化 RAG Demo 往 MaxKB 的真实模型靠近。
```

功能范围：

```text
KnowledgeFolder 文件夹树
File 原始文件表
Problem 问题增强召回
Embedding 元数据
知识库基础配置
```

后端调整：

```text
新增 knowledge_folder 表，支持多级目录
新增 file 表，保存原始文件元数据
document.file_path 迁移为 document.source_file_id
新增 problem 表，保存从段落生成的问题
新增 problem_paragraph_mapping 表，关联问题和段落
embedding_ref 增加 source_type，用于区分段落向量和问题向量
```

建议新增表：

```text
knowledge_folder
  id
  name
  description
  parent_id
  created_at
  updated_at

file
  id
  file_name
  file_size
  sha256_hash
  file_path
  created_at
  updated_at

problem
  id
  knowledge_id
  content
  created_at
  updated_at

problem_paragraph_mapping
  id
  knowledge_id
  document_id
  problem_id
  paragraph_id
  created_at
  updated_at
```

前端调整：

```text
左侧知识库区域增加文件夹树
知识库支持移动到不同文件夹
文档详情展示原始文件信息
段落详情展示关联问题
```

验收标准：

```text
可以创建文件夹和子文件夹
可以把知识库放入文件夹
上传文档后能看到原始文件记录
可以为段落生成问题
提问时可以先命中问题，再回到段落
```

### 9.4 v0.4 四期：增强检索能力

目标：

```text
从单一向量检索升级为更接近真实 RAG 系统的混合检索。
```

功能范围：

```text
向量检索
关键词检索
混合检索
召回结果重排
检索参数配置
```

技术方案：

```text
保留 Chroma 做向量检索
增加 SQLite FTS5 或迁移 PostgreSQL 全文检索
实现 SearchMode：embedding / keywords / blend
增加 rerank_service.py，对召回结果二次排序
```

后端调整：

```text
paragraph 增加 title 字段
embedding_ref 增加 score_meta 字段，记录检索调试信息
knowledge 增加 retrieval_config，保存 top_k、score_threshold、search_mode
```

新增 API：

```http
PATCH /api/knowledges/{knowledge_id}/retrieval-config
POST  /api/knowledges/{knowledge_id}/retrieval-test
```

前端调整：

```text
知识库设置页支持配置 top_k、相似度阈值、检索模式
增加检索测试面板，只展示召回段落，不调用 LLM
回答引用区展示分数和命中类型
```

验收标准：

```text
同一个问题可以分别使用向量检索、关键词检索、混合检索
可以看到每种模式召回了哪些段落
可以通过参数调整召回数量和阈值
```

### 9.5 v0.5 五期：迁移到真实项目常用存储

目标：

```text
把学习版存储升级为更接近生产项目的方案。
```

推荐技术路线：

```text
SQLite -> PostgreSQL
Chroma -> PostgreSQL + pgvector
本地文件 -> 本地文件表 + 可替换对象存储接口
```

迁移原因：

```text
PostgreSQL 可以同时保存业务数据、向量数据和全文检索索引
pgvector 更贴近 MaxKB 里 VectorField 的设计
PostgreSQL 的事务能力更适合处理文档、段落、向量的一致性
```

后端调整：

```text
引入 Alembic 管理数据库迁移
用 pgvector 存储 embedding
用 PostgreSQL tsvector 做全文检索
移除或抽象 Chroma 依赖
增加 repository 层，隔离数据库实现
```

建议新增目录：

```text
backend/
  app/
    repositories/
      knowledge_repository.py
      document_repository.py
      paragraph_repository.py
      embedding_repository.py
```

验收标准：

```text
系统可以使用 PostgreSQL 启动
向量检索从 pgvector 查询
关键词检索从 PostgreSQL 全文检索查询
业务数据和检索索引可以通过事务保持一致
```

### 9.6 v0.6 六期：任务队列和异步处理

目标：

```text
解决大文件上传、批量文档入库时接口阻塞的问题。
```

功能范围：

```text
上传后异步解析文档
异步切分和向量化
任务状态查询
失败重试
任务取消
```

技术方案：

```text
Celery + Redis
或 FastAPI BackgroundTasks 作为过渡方案
```

推荐路线：

```text
学习阶段先用 FastAPI BackgroundTasks
需要更贴近真实项目时再切到 Celery + Redis
```

后端调整：

```text
新增 task 表，记录任务类型、状态、错误信息、开始时间、结束时间
document.status 不再只靠接口同步更新，而是由任务更新
文档上传接口只负责保存文件和创建任务
```

验收标准：

```text
上传大文档时接口能快速返回
前端可以轮询任务状态
任务失败后可以看到错误信息
失败任务可以重新执行
```

### 9.7 v0.7 七期：模型管理和多模型支持

目标：

```text
把 embedding 模型和 chat 模型从硬编码改成可配置。
```

功能范围：

```text
模型供应商配置
embedding 模型配置
chat 模型配置
知识库绑定 embedding 模型
问答时选择 chat 模型
```

后端调整：

```text
新增 model_provider 表
新增 model 表
knowledge 增加 embedding_model_id
chat 请求支持 model_id
embedding_service 和 chat_service 改成按模型配置动态调用
```

前端调整：

```text
增加模型管理页面
知识库创建时选择 embedding 模型
问答区可选择 chat 模型
模型配置支持测试连接
```

验收标准：

```text
可以配置至少一个 OpenAI-compatible 供应商
不同知识库可以使用不同 embedding 模型
问答时可以切换 chat 模型
模型连接失败时有明确错误提示
```

### 9.8 v1.0 目标版本：形成完整学习版 MaxKB

目标：

```text
形成一个结构清晰、功能闭环、可对照 MaxKB 源码继续学习的知识库系统。
```

能力范围：

```text
知识库管理
文件夹管理
文档管理
原始文件管理
段落管理
向量检索
全文检索
混合检索
问题增强召回
模型管理
异步任务
问答引用
检索测试
```

不作为 v1.0 目标：

```text
多租户权限系统
复杂工作空间协作
企业级审计
高可用部署
海量数据分片
复杂可视化运营面板
```

v1.0 的核心价值不是功能数量，而是能把 MaxKB 的核心源码概念对应到自己写过的代码中。

## 10. 长期技术演进

### 10.1 存储演进

```text
v0.1-v0.4:
  SQLite + Chroma

v0.5:
  PostgreSQL + pgvector + tsvector

生产化方向:
  PostgreSQL 保存业务数据
  Milvus / Qdrant / Elasticsearch 作为独立检索服务
  S3 / OSS / TOS 保存原始文件
```

### 10.2 检索演进

```text
第一阶段:
  纯向量检索

第二阶段:
  向量检索 + 关键词检索

第三阶段:
  混合检索 + rerank

第四阶段:
  查询改写、多路召回、上下文压缩
```

### 10.3 工程演进

```text
第一阶段:
  单体 FastAPI 应用

第二阶段:
  service/repository 分层

第三阶段:
  异步任务队列

第四阶段:
  可观测性、日志、指标、错误追踪
```

### 10.4 和 MaxKB 源码的对照阅读顺序

完成每个阶段后，建议回头看对应源码：

```text
v0.1 后:
  Knowledge
  Document
  Paragraph
  Embedding

v0.2 后:
  文档状态字段
  文档删除和重建索引相关逻辑

v0.3 后:
  KnowledgeFolder
  File
  Problem
  ProblemParagraphMapping

v0.4 后:
  SearchMode
  SearchVectorField
  向量检索和全文检索实现

v0.5 后:
  VectorField
  PostgreSQL pgvector 相关 SQL
```

## 11. 企业级生产化差距与升级路线

当前方案的定位是：

```text
学习版 / 原型版 / 单机可运行版
```

它适合用来理解 MaxKB 的核心 RAG 链路，但不能直接作为企业级生产项目上线。企业级版本需要在存储、权限、安全、任务、可观测性和部署等方面继续补齐。

### 11.1 当前方案和生产方案的差距

| 维度 | 当前方案 | 企业级生产常见方案 |
|---|---|---|
| 业务数据库 | SQLite | PostgreSQL / MySQL，配合备份、迁移、主从或高可用 |
| 向量索引 | Chroma | pgvector / Milvus / Qdrant / Elasticsearch |
| 文件存储 | 本地磁盘 | S3 / OSS / TOS / MinIO |
| 任务处理 | 同步处理或轻量后台任务 | Celery / RQ / MQ / Kafka，支持重试和补偿 |
| 权限体系 | 单用户 | 用户、组织、工作空间、角色、资源权限 |
| 模型管理 | 简化配置 | 多供应商、多模型、密钥托管、调用限流 |
| 检索能力 | 纯向量检索为主 | 向量检索、全文检索、混合检索、rerank、召回评估 |
| 数据一致性 | 简化处理 | 事务、幂等、失败回滚、补偿任务 |
| 可观测性 | 基础日志 | 结构化日志、trace、metrics、告警 |
| 部署方式 | 本地启动 | Docker、CI/CD、Kubernetes、环境隔离 |
| 安全能力 | 基础校验 | 鉴权、审计、文件安全扫描、敏感信息保护 |

### 11.2 生产化升级顺序

建议按下面顺序推进，不要一开始就把所有企业级能力堆进去。

```text
第一步：数据存储生产化
  SQLite -> PostgreSQL
  Chroma -> pgvector 或独立向量数据库
  本地文件 -> 对象存储接口

第二步：任务处理生产化
  上传接口只创建任务
  文档解析、切分、向量化异步执行
  支持失败重试、任务取消、任务状态查询

第三步：权限和资源隔离
  增加用户、组织、工作空间
  知识库、文档、文件按工作空间隔离
  API 层做鉴权和权限校验

第四步：检索质量提升
  增加全文检索
  增加混合检索
  增加 rerank
  增加检索测试和效果评估

第五步：可观测性和运维
  结构化日志
  请求链路追踪
  模型调用耗时和错误率统计
  文档处理任务监控
  告警和错误追踪

第六步：部署和安全
  Docker 化
  区分开发、测试、生产环境
  密钥不落库明文
  文件类型和大小限制
  上传文件安全扫描
```

### 11.3 企业级目标架构

生产化后的推荐架构：

```text
React 前端
  -> API Gateway / 后端服务

FastAPI 后端
  -> 权限校验
  -> 知识库、文档、检索、问答 API
  -> 模型配置和调用

PostgreSQL
  -> 业务数据
  -> pgvector 向量索引
  -> tsvector 全文检索索引

Redis / MQ
  -> 异步任务队列
  -> 任务状态缓存

Worker
  -> 文档解析
  -> 文本切分
  -> embedding 生成
  -> 索引写入

对象存储
  -> 原始文件
  -> 导入导出文件

可观测性系统
  -> 日志
  -> 指标
  -> 链路追踪
  -> 告警
```

### 11.4 本项目的合理边界

这个项目的核心价值不是一次性做成完整企业系统，而是分阶段理解和复刻 MaxKB 的关键设计：

```text
v0.1-v0.4:
  用低成本技术跑通 RAG 和检索链路

v0.5-v0.7:
  引入真实项目常见的存储、任务和模型管理

v1.0:
  形成结构完整、能对照 MaxKB 源码学习的工程化版本

生产级:
  在 v1.0 之后继续补权限、安全、监控、部署和高可用
```

如果目标是学习源码，第一阶段不要被生产化复杂度拖慢。先把主链路做出来，再逐步把每个简化点替换成真实项目做法。

## 12. 推荐下一步

下一步先创建项目骨架：

```text
mini-maxkb-rag/
  backend/
  frontend/
  docs/
```

然后优先实现后端：

```text
SQLite 表结构
文档上传接口
文本切分服务
Chroma 写入和查询
chat 接口
```

后端主链路跑通后，再接前端页面。
