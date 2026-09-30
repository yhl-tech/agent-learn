# FastAPI 接口层学习笔记

## 1. FastAPI 接口层解决什么问题

接口层负责把 HTTP 请求转换成 Python 业务调用。

用户或前端看到的是：

```text
POST /api/knowledges
GET  /api/knowledges
POST /api/knowledges/{knowledge_id}/documents
POST /api/knowledges/{knowledge_id}/chat
```

后端代码里真正执行的是：

```text
create_knowledge(...)
list_knowledges(...)
upload_document(...)
retrieve_paragraphs(...)
answer_question(...)
```

FastAPI 接口层就是两者之间的适配层。

它主要回答：

```text
这个 URL 对应哪个函数？
参数从哪里来？
请求体按什么结构校验？
返回值按什么结构输出？
业务异常要变成什么 HTTP 错误？
```

## 2. 本项目接口文件

本项目有三个主要 API 文件：

```text
backend/app/api/knowledge_api.py
backend/app/api/document_api.py
backend/app/api/chat_api.py
```

对应能力：

```text
knowledge_api.py   创建知识库、查询知识库列表
document_api.py    上传文档、查询文档、查询段落
chat_api.py        知识库问答
```

启动时在 `main.py` 注册：

```python
app.include_router(knowledge_router)
app.include_router(document_router)
app.include_router(chat_router)
```

这表示：

```text
这几个 router 里的接口都会挂到 FastAPI 应用上。
```

## 3. `APIRouter` 是什么

`APIRouter` 可以理解为一组接口的集合。

例如：

```python
router = APIRouter(prefix="/api/knowledges", tags=["chat"])
```

含义：

```text
prefix  给这个 router 下的接口统一加前缀
tags    在 /docs 里给接口分组
```

如果写：

```python
@router.post("/{knowledge_id}/chat")
```

实际完整路径就是：

```text
/api/knowledges/{knowledge_id}/chat
```

因为：

```text
prefix = /api/knowledges
path   = /{knowledge_id}/chat
```

## 4. 路由装饰器是什么

例子：

```python
@router.post("/{knowledge_id}/chat", response_model=ChatResponse)
```

这行代码做了几件事：

```text
声明 HTTP 方法是 POST
声明路径是 /{knowledge_id}/chat
声明返回结构是 ChatResponse
把下面的函数注册成这个接口的处理函数
```

常见装饰器：

```text
@router.get(...)     查询资源
@router.post(...)    创建资源或执行动作
@router.put(...)     整体更新资源
@router.patch(...)   局部更新资源
@router.delete(...)  删除资源
```

本项目目前主要用了：

```text
GET
POST
```

## 5. 参数从哪里来

以问答接口为例：

```python
async def chat_api(
    knowledge_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    vector_store: ChromaVectorStore = Depends(get_vector_store),
):
```

这些参数来源不同。

`knowledge_id` 来自路径：

```text
POST /api/knowledges/{knowledge_id}/chat
```

`payload` 来自请求体：

```json
{
  "question": "这个项目用什么向量库？",
  "top_k": 4
}
```

`db` 来自依赖注入：

```python
Depends(get_db)
```

`embedding_service` 来自依赖注入：

```python
Depends(get_embedding_service)
```

`vector_store` 来自依赖注入：

```python
Depends(get_vector_store)
```

总结：

```text
路径里有的字段 -> 路径参数
JSON body 对应的模型 -> 请求体
Depends(...) -> FastAPI 自动创建或获取
```

## 6. 请求体如何校验

问答请求体：

```python
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=20)
```

这意味着前端必须传：

```text
question 是字符串
question 长度至少 1
question 长度最多 2000
top_k 是整数
top_k 最小 1
top_k 最大 20
top_k 不传时默认 4
```

如果前端传错：

```json
{
  "question": "",
  "top_k": 100
}
```

FastAPI 会在进入业务代码前自动返回：

```text
422 Unprocessable Entity
```

所以接口函数里不用手写这些基础校验。

## 7. `response_model` 做什么

例子：

```python
@router.post("/{knowledge_id}/chat", response_model=ChatResponse)
```

`response_model` 的作用：

```text
规定接口返回结构
自动把对象转换成 JSON
过滤未声明字段
生成 /docs 文档
```

例如 `ChatResponse`：

```python
class ChatResponse(BaseModel):
    answer: str
    references: List[ReferenceRead]
```

这表示接口最终返回：

```json
{
  "answer": "...",
  "references": [...]
}
```

即使 service 返回了更多内部字段，`response_model` 也可以避免多余字段直接暴露出去。

## 8. `async def` 什么时候需要

本项目里上传文档接口和问答接口是异步函数：

```python
async def upload_document_api(...):
async def chat_api(...):
```

原因：

```text
上传文件读取是异步接口
调用外部大模型 API 使用 httpx.AsyncClient
```

例如：

```python
file_path = await save_upload_file(knowledge_id, upload_file)
return await answer_question(payload.question, retrieved)
```

如果函数内部需要 `await`，外层函数就必须是 `async def`。

如果函数只是普通数据库查询，可以写同步函数：

```python
def list_knowledges_api(db: Session = Depends(get_db)):
```

## 9. HTTP 错误怎么处理

FastAPI 使用 `HTTPException` 返回明确的 HTTP 错误。

例如问答时知识库不存在：

```python
knowledge = get_knowledge(db, knowledge_id)
if knowledge is None:
    raise HTTPException(status_code=404, detail="知识库不存在")
```

含义：

```text
业务上找不到资源
-> 返回 404
```

上传文档时：

```python
try:
    return await upload_document(...)
except ValueError as error:
    raise HTTPException(status_code=400, detail=str(error)) from error
```

含义：

```text
service 抛业务错误
api 层把它转换成 HTTP 400
```

回答生成失败时：

```python
raise HTTPException(status_code=502, detail=f"生成回答失败：{error}") from error
```

含义：

```text
上游模型服务失败
-> 返回 502
```

## 10. 本项目有哪些接口

创建知识库：

```text
POST /api/knowledges
```

请求体：

```text
KnowledgeCreate
```

响应：

```text
KnowledgeRead
```

查询知识库：

```text
GET /api/knowledges
```

响应：

```text
list[KnowledgeRead]
```

上传文档：

```text
POST /api/knowledges/{knowledge_id}/documents
```

请求：

```text
路径参数 knowledge_id
上传文件 file
```

响应：

```text
DocumentRead
```

查询知识库下文档：

```text
GET /api/knowledges/{knowledge_id}/documents
```

响应：

```text
list[DocumentRead]
```

查询文档段落：

```text
GET /api/documents/{document_id}/paragraphs
```

响应：

```text
list[ParagraphRead]
```

知识库问答：

```text
POST /api/knowledges/{knowledge_id}/chat
```

请求体：

```text
ChatRequest
```

响应：

```text
ChatResponse
```

## 11. `UploadFile` 是什么

文档上传接口：

```python
async def upload_document_api(
    knowledge_id: str,
    file: UploadFile,
    ...
):
```

`UploadFile` 是 FastAPI 处理上传文件的类型。

它提供：

```text
filename    原始文件名
content_type 文件类型
read()      读取文件内容
```

本项目里：

```python
content = await upload_file.read()
target_path.write_bytes(content)
```

也就是说：

```text
先从 HTTP 请求里读文件内容
再写入 backend/data/files/{knowledge_id}/
```

## 12. `/docs` 自动文档

FastAPI 会根据：

```text
APIRouter
路由装饰器
参数类型
Pydantic Schema
response_model
```

自动生成接口文档。

启动后通常可以访问：

```text
http://localhost:8000/docs
```

在这里可以看到：

```text
接口路径
请求参数
请求体结构
响应结构
字段校验规则
```

这也是为什么 Schema 写清楚很重要。

## 13. 接口层和 service 层的边界

接口层应该做：

```text
接 HTTP
拆参数
注入依赖
转 HTTP 错误
声明返回结构
```

service 层应该做：

```text
业务流程
数据库读写
调用 storage
调用 embedding
调用 retrieval
调用 chat
```

例如 `chat_api` 不直接调用 Chroma。

它调用：

```python
retrieve_paragraphs(...)
answer_question(...)
```

这样接口层保持清晰，业务逻辑也方便复用。

## 14. 常见知识点

FastAPI 接口层常见概念：

```text
FastAPI          应用对象
APIRouter        一组接口
prefix           路由统一前缀
tags             接口文档分组
path parameter   路径参数
request body     请求体
response_model   响应结构
Depends          依赖注入
HTTPException    HTTP 错误
UploadFile       上传文件
async def        异步接口函数
```

本项目里的对应关系：

```text
FastAPI          app = create_app()
APIRouter        knowledge_router / document_router / chat_router
path parameter   knowledge_id / document_id
request body     KnowledgeCreate / ChatRequest
response_model   KnowledgeRead / DocumentRead / ChatResponse
Depends          get_db / get_embedding_service / get_vector_store
```

## 15. `Depends` 到底做了什么

以问答接口为例：

```python
embedding_service: HashEmbeddingService = Depends(get_embedding_service)
```

这行可以拆成三部分：

```text
embedding_service       参数名，接口函数内部通过这个名字使用对象
HashEmbeddingService    类型提示，说明参数应该是什么类型
Depends(...)            告诉 FastAPI 这个参数不由前端传入
```

`Depends(get_embedding_service)` 的执行过程：

```text
收到 HTTP 请求
-> FastAPI 发现 Depends
-> FastAPI 调用 get_embedding_service()
-> 取得函数返回值
-> 把返回值传给 embedding_service 参数
-> 执行 chat_api
```

可以近似理解为 FastAPI 自动执行了：

```python
embedding_service = get_embedding_service()
await chat_api(..., embedding_service=embedding_service)
```

注意这里传入的是函数：

```python
Depends(get_embedding_service)
```

不是主动调用函数：

```python
Depends(get_embedding_service())
```

FastAPI 需要保存这个函数，在收到请求时决定何时调用、是否复用以及如何清理。

## 16. 依赖函数为什么要返回实例

依赖函数：

```python
@lru_cache
def get_embedding_service() -> HashEmbeddingService:
    return HashEmbeddingService()
```

`HashEmbeddingService` 是类，相当于对象的定义：

```python
class HashEmbeddingService:
    def embed_text(self, text: str) -> list[float]:
        ...
```

`HashEmbeddingService()` 才是根据这个类创建出来的实例。

后续代码需要调用实例方法：

```python
query_embedding = embedding_service.embed_text(question)
```

所以依赖函数必须把实例返回给 FastAPI。

如果没有写 `return`：

```python
def get_embedding_service():
    HashEmbeddingService()
```

Python 会默认返回 `None`。FastAPI 注入的也会是 `None`：

```python
embedding_service = None
embedding_service.embed_text(question)
```

最终会报错：

```text
AttributeError: 'NoneType' object has no attribute 'embed_text'
```

`@lru_cache` 表示第一次调用时创建实例，后续调用复用同一个实例，避免重复初始化。

数据库依赖比较特殊：

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

这里使用 `yield`：

```text
yield db        把 Session 注入接口参数
finally         请求结束后关闭 Session
```

## 17. `db.get()` 的两个参数

例如：

```python
db.get(KnowledgeModel, knowledge_id)
```

两个参数分别表示：

```text
KnowledgeModel  查询哪一种 ORM 模型
knowledge_id    要查询的主键值
```

`KnowledgeModel` 映射到数据库的 `knowledge` 表，并且它的 `id` 字段是主键。

所以上面的代码大致相当于：

```sql
SELECT *
FROM knowledge
WHERE id = knowledge_id;
```

返回结果：

```text
找到记录     返回 KnowledgeModel 实例
没有找到     返回 None
```

因此函数返回类型写成：

```python
def get_knowledge(...) -> KnowledgeModel | None:
```

`db.get()` 适合按主键查询单条记录。复杂条件查询使用 `select(...)`。

## 18. `class DocumentModel(Base)` 是什么写法

这是 Python 的类继承语法：

```python
class DocumentModel(Base):
```

含义：

```text
class           定义一个类
DocumentModel   新类的名称
Base            DocumentModel 继承的父类
:               类体开始
```

对应 TypeScript：

```typescript
class DocumentModel extends Base {
}
```

本项目中的 `Base` 继承自 SQLAlchemy 的 `DeclarativeBase`：

```python
class Base(DeclarativeBase):
    pass
```

因此继承 `Base` 的类会获得 SQLAlchemy ORM 模型能力：

```python
class DocumentModel(Base):
    __tablename__ = "document"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
```

这里：

```text
__tablename__       指定对应的数据库表名
id / name           Python 对象属性
Mapped[str]         属性值的 Python 类型
mapped_column(...)  对应的数据库字段配置
```

最终对应关系：

```text
DocumentModel 类      <-> document 数据库表
DocumentModel 实例    <-> document 表中的一条记录
实例的 id/name 属性   <-> 一条记录中的字段值
```

## 19. 最小记忆模型

```text
FastAPI 接口层 = HTTP 到业务函数的入口适配
APIRouter = 管一组接口
装饰器 = 定义 HTTP 方法和路径
参数类型 = 告诉 FastAPI 参数从哪里来、怎么校验
response_model = 告诉 FastAPI 返回什么结构
HTTPException = 把业务失败翻译成 HTTP 错误
Depends(f) = FastAPI 调用 f，并把返回值注入参数
依赖函数不返回值 = 注入 None
db.get(Model, id) = 按 Model 的主键查询一条记录
class Child(Parent) = Child 继承 Parent
ORM 模型类 = 数据库表，ORM 模型实例 = 表中的一条记录
```
