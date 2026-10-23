# SQLAlchemy Session 学习笔记

## 1. SQLAlchemy 解决什么问题

后端代码最终要读写数据库。

如果直接写 SQL，也可以完成：

```sql
select * from knowledge where id = 'xxx';
```

但项目里更常见的是用 ORM。

ORM 的作用是：

```text
把数据库表映射成 Python 类
把数据库记录映射成 Python 对象
```

例如：

```python
knowledge = db.get(KnowledgeModel, knowledge_id)
```

这行代码背后等价于：

```text
去 knowledge 表里按主键查一条记录
然后返回一个 KnowledgeModel 对象
```

## 2. 核心角色

本项目的数据层核心角色：

```text
DATABASE_URL   数据库连接字符串
engine         数据库引擎，知道连哪个数据库
SessionLocal   Session 工厂，用来创建 Session
Session        一次数据库操作上下文
db             当前请求拿到的 Session 实例
Base           所有 ORM Model 的基类
Model          表结构对应的 Python 类
```

最小关系：

```text
DATABASE_URL -> engine -> SessionLocal -> db(Session) -> Model
```

## 3. 本项目里的创建方式

代码位置：

```text
backend/app/database.py
```

核心代码：

```python
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

含义：

```text
create_engine      创建底层数据库入口
DATABASE_URL       决定连接哪个数据库
sessionmaker       创建 Session 工厂
SessionLocal()     创建一个真正的 Session
```

本项目默认使用 SQLite，也可以通过 `DATABASE_URL` 切换到 PostgreSQL：

```text
本地默认      sqlite:///backend/data/app.db
生产模式      postgresql+psycopg://...
```

数据库类型改变后，创建 Session 和操作 ORM 的基本方式不变；数据库迁移和向量存储实现会随配置切换。

## 4. `connect_args` 是什么

代码：

```python
connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
```

这是 SQLite 在 Web 服务里常见的配置。

SQLite 默认限制：

```text
一个连接只能在创建它的线程里使用。
```

FastAPI 处理请求时可能涉及不同线程。

所以本项目对 SQLite 增加：

```text
check_same_thread=False
```

它的目的不是提升性能，而是避免本地开发时线程检查报错。

如果以后换成 PostgreSQL，这个配置就不会传。

## 5. `Base` 是什么

代码：

```python
class Base(DeclarativeBase):
    pass
```

所有模型都继承它：

```python
class KnowledgeModel(Base):
    __tablename__ = "knowledge"
```

`Base` 的作用：

```text
收集所有继承它的表模型元信息
让 SQLAlchemy 知道项目里有哪些表
```

创建表时：

```python
Base.metadata.create_all(bind=engine)
```

意思是：

```text
根据所有 Model 定义，在数据库中创建还不存在的表。
```

## 6. Model 和表的关系

本项目模型在：

```text
backend/app/models.py
```

一张表对应一个类：

```python
class KnowledgeModel(Base):
    __tablename__ = "knowledge"
```

字段用 `mapped_column` 定义：

```python
id: Mapped[str] = mapped_column(String(64), primary_key=True, default=new_id)
name: Mapped[str] = mapped_column(String(150), index=True)
```

含义：

```text
id    knowledge 表的主键字段
name  knowledge 表的名称字段，并建立索引
```

一条数据库记录在代码里就是一个对象：

```python
KnowledgeModel(id="...", name="默认知识库", ...)
```

## 7. 本项目有哪些表

当前 ORM 共 11 张表，可以按职责分成三组：

```text
核心业务：
KnowledgeFolderModel
KnowledgeModel
FileModel
DocumentModel
ParagraphModel

增强检索：
ProblemModel
ProblemParagraphMappingModel
EmbeddingRefModel

任务可靠性：
TaskModel
TaskAttemptModel
OutboxEventModel
```

其中：

```text
FileModel
保存原始文件名称、大小、哈希和路径。

ParagraphModel
保存文档切分后的 chunk，是 RAG 检索的核心业务单位。

ProblemParagraphMappingModel
保存增强问题与原始段落之间的多对多关系。

EmbeddingRefModel
保存向量来源和稳定 vector_id。
SQLite + Chroma 模式下真实向量在 Chroma；
PostgreSQL + pgvector 模式下真实向量在 embedding 列。

TaskModel / TaskAttemptModel / OutboxEventModel
分别保存任务当前状态、每次执行历史和待投递消息。
```

## 8. 外键和关系

字段外键：

```python
knowledge_id: Mapped[str] = mapped_column(String(64), ForeignKey("knowledge.id"), index=True)
document_id: Mapped[str] = mapped_column(String(64), ForeignKey("document.id"), index=True)
```

意思是：

```text
document 属于 knowledge
paragraph 属于 document
embedding_ref 指向 paragraph
```

ORM 关系：

```python
documents: Mapped[list["DocumentModel"]] = relationship(
    back_populates="knowledge",
    cascade="all, delete-orphan",
)
```

`relationship` 的作用是：

```text
让 Python 对象之间可以互相访问。
```

例如理论上可以：

```text
knowledge.documents
document.paragraphs
paragraph.embedding_ref
```

字段外键更偏数据库结构。

`relationship` 更偏 Python 对象访问。

## 9. `db.get` 是什么

代码：

```python
knowledge = db.get(KnowledgeModel, knowledge_id)
```

含义：

```text
按主键查询 KnowledgeModel。
```

等价理解：

```text
select * from knowledge where id = knowledge_id limit 1
```

如果查不到：

```text
返回 None
```

所以项目里会写：

```python
knowledge = get_knowledge(db, knowledge_id)
if knowledge is None:
    raise HTTPException(status_code=404, detail="知识库不存在")
```

## 10. `select` 和 `scalars`

查询多条数据时用：

```python
statement = (
    select(DocumentModel)
    .where(DocumentModel.knowledge_id == knowledge_id)
    .order_by(DocumentModel.created_at.desc())
)
documents = list(db.scalars(statement).all())
```

拆开理解：

```text
select(DocumentModel)                     查询 DocumentModel
where(DocumentModel.knowledge_id == ...)  只查某个知识库
order_by(...desc())                       按创建时间倒序
db.scalars(statement)                     只取 ORM 对象本身
all()                                     拿到全部结果
list(...)                                 转成普通 list
```

如果不用 `scalars`，SQLAlchemy 返回的结构会更接近“行”。

用 `scalars` 后，拿到的是：

```text
list[DocumentModel]
```

## 11. 新增数据的步骤

创建知识库：

```python
knowledge = KnowledgeModel(
    name=payload.name,
    description=payload.description,
)
db.add(knowledge)
db.commit()
db.refresh(knowledge)
```

含义：

```text
创建 Python 对象
-> 加入 Session
-> 提交事务
-> 刷新对象字段
```

`db.add` 只是告诉 Session：

```text
这个对象需要被保存。
```

真正提交要等：

```python
db.commit()
```

## 12. `flush` 和 `commit`

上传接口创建待处理文档时：

```python
db.add(source_file)
db.flush()
db.add(document)
db.flush()
db.add(task)
db.flush()
db.add(outbox_event)
db.commit()
```

为什么这里不用马上 `commit`？

因为后面还要创建：

```text
File
PENDING Document
PENDING Task
PENDING OutboxEvent
```

这些记录必须一起成功或一起失败。只有提交以后，上传接口才返回已经可靠受理的任务。

`flush` 的作用：

```text
把当前变更同步到数据库连接
让 ORM 对象拿到 id
但还不正式提交事务
```

`commit` 的作用：

```text
正式提交事务，让变更持久生效
```

本项目上传事务先使用 `flush()`，因为后面的记录需要引用前面生成的：

```text
source_file.id
document.id
task.id
```

Worker 随后在另一个 Session 中执行索引，创建：

```text
ParagraphModel
EmbeddingRefModel
TaskAttemptModel
```

## 13. `refresh` 是什么

提交后：

```python
db.refresh(document)
```

作用：

```text
从数据库重新读取这条记录，把数据库生成或更新的字段同步回对象。
```

例如：

```text
id
created_at
updated_at
```

这些字段可能由默认值函数生成。

`refresh` 后，返回给接口的对象字段更完整。

## 14. Session 和事务

Session 可以理解成：

```text
一组数据库操作的工作区。
```

上传请求的 Session 在同一个事务里：

```text
新增 file
新增 document
新增 task
新增 outbox_event
最后统一 commit
```

如果中间出错，代码会显式 `rollback()`，并补偿删除已经写到磁盘的实体文件。

Worker 处理索引时使用另一个事务：

```text
认领 Task 后先提交执行权
-> 在新事务中写 Paragraph、EmbeddingRef 和文档结果
-> 同时把 Task 和 TaskAttempt 更新为终态
```

向量一致性取决于存储模式。

PostgreSQL + pgvector：

```text
业务表和 embedding 向量位于同一个数据库事务。
执行失败时 rollback 可以一起撤销。
```

SQLite + Chroma：

```text
SQLite commit 和 Chroma upsert 不是同一个原子事务。
失败或取消时，代码需要按稳定 vector_id 补偿删除 Chroma 向量。
```

任务投递也跨越数据库和 Redis。项目使用 Transactional Outbox 保证 Task 与待投递事件同事务落库，再由 Relay 至少一次发布。完整说明见 `async-task-outbox-learning.md`。

## 15. Session 生命周期

Session 由 `get_db` 创建：

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

接口中使用：

```python
db: Session = Depends(get_db)
```

生命周期：

```text
请求开始
-> 创建 Session
-> 接口和 service 使用 db
-> 请求结束
-> close Session
```

不要把这个 `db` 理解成全局数据库对象。

它是：

```text
当前请求的一次数据库会话。
```

## 16. 常见知识点

SQLAlchemy 常用概念：

```text
Engine        数据库连接入口
Session       ORM 工作上下文
Transaction   事务
Model         表对应的 Python 类
Column        表字段
Primary Key   主键
Foreign Key   外键
Index         索引
Relationship  ORM 对象关系
Query         查询
Flush         同步变更但不提交
Commit        提交事务
Refresh       从数据库刷新对象
```

本项目里的对应：

```text
Engine        engine
Session       db
Model         业务、检索、任务三组共 11 个 ORM Model
Primary Key   id
Foreign Key   knowledge_id / document_id / paragraph_id / task_id
Index         index=True
Flush         在事务内生成 ID，供后续关联记录引用
Commit        原子提交上传数据，或提交一次任务状态转换
```

## 17. 最小记忆模型

```text
Model = 表结构
Session = 一次数据库操作上下文
db.get = 按主键查
select = 构造查询
db.add = 加入待保存对象
flush = 先写入以拿到 id，但不结束事务
commit = 正式提交
refresh = 重新读取数据库生成的字段
```
