# `Depends(get_db)` 学习笔记

## 1. 核心理解

```python
db: Session = Depends(get_db)
```

这句话的意思是：

```text
这个接口需要一个数据库会话 db。
db 不由调用方传入，而是由 FastAPI 调用 get_db() 后自动注入。
```

也就是说，前端请求接口时不会传 `db`。

前端只传：

```text
URL 参数
Query 参数
JSON 请求体
上传文件
```

`db` 是后端运行时需要的对象。

FastAPI 看到 `Depends(get_db)` 后，会自己准备这个对象。

## 2. 抽象模型

```text
Depends(get_db)
= 告诉 FastAPI：请执行 get_db()，并把结果交给这个参数。
```

对应关系：

```text
get_db   负责创建和关闭数据库会话
Depends  声明这个参数需要依赖 get_db
FastAPI  负责在请求前调用 get_db，请求后执行清理
db       接口函数里拿到的 Session 对象
```

可以把它理解成：

```text
接口函数声明需求
FastAPI 负责满足需求
```

接口函数说：

```text
我需要一个 db。
```

FastAPI 做：

```text
调用 get_db()
拿到 db
传给接口函数
请求结束后清理 db
```

## 3. 本项目里哪里用了

知识库接口：

```python
def create_knowledge_api(payload: KnowledgeCreate, db: Session = Depends(get_db)):
```

文档接口：

```python
async def upload_document_api(
    knowledge_id: str,
    file: UploadFile,
    db: Session = Depends(get_db),
    ...
):
```

问答接口：

```python
async def chat_api(
    knowledge_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    ...
):
```

这些接口都需要访问当前配置的业务数据库，可以是 SQLite 或 PostgreSQL。

所以它们都声明：

```python
db: Session = Depends(get_db)
```

## 4. 请求生命周期

```text
请求开始
-> FastAPI 看到 Depends(get_db)
-> 调用 get_db()
-> get_db 创建 Session
-> yield db，把 db 交给接口使用
-> 接口用 db 查询或写入数据库
-> 请求结束
-> get_db 继续执行 finally
-> db.close()
```

这个流程里最关键的是：

```text
yield 前是准备资源
yield 时把资源交出去
yield 后是回收资源
```

## 5. `get_db` 的典型写法

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

对应代码在：

```text
backend/app/database.py
```

它做了三件事：

```text
SessionLocal()  创建一个 Session
yield db        把 Session 提供给接口函数
db.close()      请求结束后关闭 Session
```

## 6. 为什么这里用 `yield`

普通函数可以直接 `return db`。

但如果这样写：

```python
def get_db():
    db = SessionLocal()
    return db
```

它只能创建并返回 `db`。

它没有机会在请求结束后自动执行：

```python
db.close()
```

使用 `yield` 后，FastAPI 会把它当作带清理逻辑的依赖。

生命周期变成：

```text
yield 前代码：请求开始前执行
yield 的值：传给接口参数
yield 后代码：请求结束后执行
```

所以：

```python
try:
    yield db
finally:
    db.close()
```

可以保证：

```text
即使接口中间报错，请求结束后也会关闭 db。
```

## 7. `db: Session` 是什么

```text
数据库文件：真正存数据的地方
Session：操作数据库的一次工作上下文
db：当前请求拿到的那个 Session
```

所以：

```python
knowledge = get_knowledge(db, knowledge_id)
```

可以理解成：

```text
用当前请求的 db 会话，去数据库里查 knowledge_id 对应的知识库。
```

更完整地看：

```python
def get_knowledge(db: Session, knowledge_id: str) -> KnowledgeModel | None:
    return db.get(KnowledgeModel, knowledge_id)
```

这里的 `db` 不是数据库文件本身。

它是：

```text
当前请求里用于操作数据库的会话对象。
```

## 8. 为什么每个请求都要一个 Session

Web 服务同时会处理很多请求。

例如：

```text
用户 A 在上传文档
用户 B 在查询知识库
用户 C 在提问
```

每个请求都应该有自己的数据库操作上下文。

这样可以避免：

```text
不同请求互相污染
事务边界不清楚
连接用完不释放
```

所以本项目用：

```text
一个请求 -> 一个 Session -> 请求结束 close
```

## 9. `Depends` 不只用于数据库

本项目还用了：

```python
embedding_service: HashEmbeddingService = Depends(get_embedding_service)
vector_store: EmbeddingRepository = Depends(get_embedding_repository)
```

它们来自：

```text
backend/app/dependencies.py
```

核心代码：

```python
@lru_cache
def get_embedding_service() -> HashEmbeddingService:
    return HashEmbeddingService()

@lru_cache
def get_embedding_repository() -> EmbeddingRepository:
    if VECTOR_BACKEND == "pgvector":
        return PostgresEmbeddingRepository()
    return ChromaEmbeddingRepository()
```

这说明 `Depends` 的本质是：

```text
声明当前接口依赖某个对象或能力。
```

数据库依赖：

```text
每个请求创建，用完关闭。
```

embedding/repository 依赖：

```text
用 lru_cache 缓存，多个请求复用。
```

## 10. `Depends(get_db)` 和 `Depends(get_embedding_repository)` 的区别

`get_db`：

```text
请求级依赖
每次请求创建一个 Session
请求结束后关闭
```

`get_embedding_repository`：

```text
应用级依赖
第一次调用时按 VECTOR_BACKEND 创建仓库实现
后续请求复用同一个实例
```

为什么不把数据库 Session 也用 `lru_cache`？

因为 Session 有事务和连接状态。

它不应该被所有请求长期共享。

为什么 embedding repository 可以缓存？

因为它是无请求状态的仓库或客户端封装。

重复初始化 Chroma 客户端没有必要，pgvector 实现也只使用调用方传入的请求级 Session。

## 11. Depends 的执行顺序

以 `chat_api` 为例：

```python
async def chat_api(
    knowledge_id: str,
    payload: ChatRequest,
    db: Session = Depends(get_db),
    embedding_service: HashEmbeddingService = Depends(get_embedding_service),
    vector_store: EmbeddingRepository = Depends(get_embedding_repository),
):
```

FastAPI 大致会做：

```text
解析 URL，得到 knowledge_id
解析 JSON，得到 payload
调用 get_db，得到 db
调用 get_embedding_service，得到 embedding_service
调用 get_embedding_repository，得到 vector_store
执行 chat_api(...)
请求结束后清理 get_db 的 yield 资源
```

接口函数里只看到最终对象：

```text
db
embedding_service
vector_store
```

不需要关心它们怎么创建。

## 12. 为什么这叫依赖注入

依赖就是：

```text
一个函数运行时需要的外部对象。
```

例如 `chat_api` 需要：

```text
数据库会话
embedding 服务
向量库客户端
```

注入就是：

```text
这些对象不是函数内部自己 new 出来
而是由框架在调用函数时传进来
```

所以：

```text
Depends = 声明依赖
FastAPI = 负责注入
```

这样做的好处：

```text
接口函数更清晰
资源生命周期统一管理
测试时更容易替换依赖
避免到处手动创建重复对象
```

## 13. 常见误区

误区一：以为 `db` 是前端传的。

```text
不是。
db 是后端依赖注入生成的。
```

误区二：以为 `Depends(get_db)` 会立刻执行。

```text
模块加载时不会执行。
真正收到请求时，FastAPI 才会执行依赖函数。
```

误区三：以为 `yield db` 后面的代码不会执行。

```text
会执行。
请求结束后 FastAPI 会继续执行 finally。
```

误区四：把所有对象都做成全局变量。

```text
有些无请求状态的对象可以复用，例如 embedding repository。
有些资源应该请求隔离，例如 db Session。
```

## 14. 最小记忆模型

```text
Depends(get_db) = 让 FastAPI 给接口函数准备 db
get_db = 创建 Session，并在请求结束后关闭
yield = 先交出资源，后续再清理资源
db = 当前请求的数据库操作上下文
```
