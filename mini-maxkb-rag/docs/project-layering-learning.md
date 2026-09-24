# 项目分层学习笔记

## 1. 为什么要分层

一个后端项目如果所有代码都写在接口函数里，很快会变得难读。

例如上传文档接口要做很多事：

```text
接收 HTTP 文件
校验知识库
保存文件
读取文本
切分文本
写 Document 表
写 Paragraph 表
生成向量
写入 Chroma
提交事务
返回响应
```

如果这些逻辑全部堆在 `document_api.py` 里，接口层会非常重。

分层的目的就是：

```text
每一层只负责一种问题。
```

这样读代码时可以快速判断：

```text
我现在看的是入口适配？
还是业务流程？
还是数据库表？
还是外部存储？
```

## 2. 本项目的分层

项目主要分成这些层：

```text
api       接收 HTTP 请求，处理参数和 HTTP 错误
services 组织业务流程
storage  封装文件系统、Chroma 等外部存储
models   定义数据库表结构
schemas  定义 API 入参和出参
config   集中读取配置和路径
database 管理数据库 engine、Session、建表
```

目录对应关系：

```text
backend/app/api/
backend/app/services/
backend/app/storage/
backend/app/models.py
backend/app/schemas.py
backend/app/config.py
backend/app/database.py
```

## 3. `api` 层负责什么

例子：

```text
backend/app/api/knowledge_api.py
backend/app/api/document_api.py
backend/app/api/chat_api.py
```

`api` 层直接面对 HTTP。

它负责：

```text
声明 URL
声明 HTTP 方法
接收路径参数
接收请求体
声明 response_model
注入 db、embedding_service、vector_store
把业务异常转换成 HTTPException
```

例如问答接口：

```python
@router.post("/{knowledge_id}/chat", response_model=ChatResponse)
async def chat_api(
    knowledge_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    vector_store: ChromaVectorStore = Depends(get_vector_store),
):
```

这段代码说明 `api` 层知道：

```text
路径里有 knowledge_id
请求体是 ChatRequest
响应体是 ChatResponse
这个接口需要 db、embedding_service、vector_store
```

但它不应该直接关心：

```text
怎么切分文本
怎么计算 embedding
怎么调用 Chroma
怎么组装 prompt
```

这些是 service 或 storage 的职责。

## 4. `services` 层负责什么

例子：

```text
backend/app/services/knowledge_service.py
backend/app/services/document_service.py
backend/app/services/chunk_service.py
backend/app/services/embedding_service.py
backend/app/services/retrieval_service.py
backend/app/services/chat_service.py
```

`services` 层负责业务流程。

也就是回答：

```text
一个业务动作要按什么步骤执行？
中间需要调用哪些能力？
失败时业务上应该怎么处理？
```

例如 `upload_document`：

```text
查知识库
-> 保存文件
-> 读取文本
-> 切分
-> 创建 Document
-> 创建 Paragraph
-> 生成向量
-> 写 Chroma
-> 创建 EmbeddingRef
-> commit
```

这就是业务编排。

`document_service.py` 本身不应该知道 HTTP 状态码。

所以它遇到业务错误时抛：

```python
raise ValueError("知识库不存在")
```

然后 `document_api.py` 再把它翻译成：

```python
raise HTTPException(status_code=400, detail=str(error))
```

## 5. `storage` 层负责什么

例子：

```text
backend/app/storage/file_storage.py
backend/app/storage/vector_store.py
```

`storage` 层负责外部存储的具体操作。

本项目有两类外部存储：

```text
本地文件系统
ChromaDB 向量库
```

文件存储封装：

```python
save_upload_file(knowledge_id, upload_file)
read_text_file(file_path)
```

向量库封装：

```python
ChromaVectorStore.add_paragraphs(...)
ChromaVectorStore.search(...)
ChromaVectorStore.delete_by_document(...)
```

这样 service 层不用直接写：

```text
Path 拼接
文件名处理
Chroma PersistentClient 初始化
collection.add
collection.query
```

它只调用更稳定的业务接口。

## 6. `models` 负责什么

文件：

```text
backend/app/models.py
```

SQLAlchemy Model 描述数据库怎么存。

本项目的表：

```text
KnowledgeModel      知识库
DocumentModel       文档
ParagraphModel      段落
EmbeddingRefModel   向量引用
```

关系：

```text
KnowledgeModel 1 -> N DocumentModel
DocumentModel  1 -> N ParagraphModel
ParagraphModel 1 -> 1 EmbeddingRefModel
```

核心字段：

```text
knowledge_id    数据属于哪个知识库
document_id     段落属于哪个文档
paragraph_id    向量引用对应哪个段落
vector_id       Chroma 中的向量 ID
```

Model 层回答的是：

```text
数据存在数据库里长什么样？
字段类型是什么？
表之间怎么关联？
```

## 7. `schemas` 负责什么

文件：

```text
backend/app/schemas.py
```

Pydantic Schema 描述 API 怎么收、怎么返回。

例如创建知识库请求：

```python
class KnowledgeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str = ""
```

例如问答响应：

```python
class ChatResponse(BaseModel):
    answer: str
    references: List[ReferenceRead]
```

Schema 层回答的是：

```text
前端应该传什么字段？
后端会返回什么字段？
哪些字段需要校验？
哪些数据库字段不应该暴露给前端？
```

所以：

```text
models.py 是存储结构
schemas.py 是接口合同
```

这两个文件不要混为一谈。

## 8. `config` 负责什么

文件：

```text
backend/app/config.py
```

`config.py` 负责统一管理：

```text
路径
环境变量
默认值
运行时目录
```

例如：

```python
DATA_DIR = Path(os.getenv("MINI_MAXKB_DATA_DIR", BACKEND_DIR / "data"))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")
```

其他模块不需要自己读环境变量。

它们直接导入：

```python
from app.config import DATABASE_URL
from app.config import CHROMA_DIR
```

这样配置来源集中，后续要换数据库、换数据目录、换模型配置时更容易。

## 9. `database` 负责什么

文件：

```text
backend/app/database.py
```

它负责：

```text
创建 engine
创建 SessionLocal
定义 Base
提供 get_db
提供 create_tables
```

核心关系：

```text
DATABASE_URL -> engine -> SessionLocal -> Session
```

接口里用：

```python
db: Session = Depends(get_db)
```

就是从 `database.py` 拿到当前请求的数据库会话。

## 10. `dependencies` 负责什么

文件：

```text
backend/app/dependencies.py
```

这个文件提供可注入的对象：

```python
get_embedding_service()
get_vector_store()
```

它们用了：

```python
@lru_cache
```

作用：

```text
第一次调用时创建对象
后续请求复用同一个对象
避免每个请求都重新初始化 Chroma
```

这类对象不属于单个 HTTP 请求。

它们更像应用级服务。

而 `db: Session = Depends(get_db)` 是请求级资源：

```text
每个请求创建
请求结束关闭
```

## 11. 分层之间怎么调用

以文档上传为例：

```text
document_api.py
-> document_service.upload_document
-> file_storage.save_upload_file
-> file_storage.read_text_file
-> chunk_service.split_text
-> embedding_service.embed_texts
-> vector_store.add_paragraphs
-> models.DocumentModel / ParagraphModel / EmbeddingRefModel
```

以问答为例：

```text
chat_api.py
-> knowledge_service.get_knowledge
-> retrieval_service.retrieve_paragraphs
-> embedding_service.embed_text
-> vector_store.search
-> models.ParagraphModel / DocumentModel
-> chat_service.answer_question
-> schemas.ChatResponse
```

## 12. 判断代码应该放哪一层

可以用这些问题判断：

```text
和 HTTP 路径、状态码、请求参数有关吗？
放 api。

和业务步骤编排有关吗？
放 services。

和文件系统、Chroma、外部 API 的具体调用有关吗？
放 storage 或专门 client。

和数据库表字段有关吗？
放 models。

和接口入参出参有关吗？
放 schemas。

和环境变量、路径、默认值有关吗？
放 config。
```

例如：

```text
“上传失败返回 400”          api
“上传后要先切分再向量化”     services
“文件保存到哪个目录”         storage/config
“paragraph 表有哪些字段”     models
“top_k 最大不能超过 20”      schemas
```

## 13. 常见误区

误区一：在 API 层写太多业务。

```text
接口函数应该薄一点。
它负责入口适配，不负责全部业务细节。
```

误区二：把 Model 直接当接口合同。

```text
数据库字段不一定都要给前端。
前端字段变化也不应该强迫数据库跟着改。
```

误区三：service 直接散落外部库细节。

```text
如果到处都直接调用 Chroma API，
以后切换 pgvector 会很难改。
```

误区四：配置分散在各个文件。

```text
路径和环境变量分散后，启动问题会变难排查。
```

## 14. 和 MaxKB 的对应关系

这个项目是学习版，复杂度比 MaxKB 小很多。

但核心分层思想一致：

```text
接口层处理请求
业务层编排知识库、文档、段落、向量
存储层屏蔽底层存储差异
模型层描述核心数据结构
```

MaxKB 真实项目里还会有：

```text
权限
工作空间
异步任务
多模型配置
文件解析
向量索引维护
问题增强
```

学习这个项目时先抓住主干：

```text
不要先被框架细节淹没。
先看数据从哪来，经过哪几层，最后到哪去。
```

## 15. 最小记忆模型

```text
api = HTTP 入口
services = 业务流程
storage = 外部存储封装
models = 数据库存储结构
schemas = API 数据合同
config = 配置和路径
database = Session 和建表
dependencies = 可注入服务对象
```
