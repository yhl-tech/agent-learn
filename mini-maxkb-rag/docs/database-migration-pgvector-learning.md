# 数据库迁移、PostgreSQL 与 pgvector 学习笔记

## 1. 一句话定义

```text
数据库迁移是用有版本的脚本，把旧数据库结构安全地升级到新代码需要的结构。
```

本项目同时保留两条路径：

```text
本地学习模式     SQLite + 轻量幂等迁移 + Chroma
生产演进模式     PostgreSQL + Alembic + pgvector
```

核心代码：

```text
backend/app/database.py
backend/app/migrations.py
backend/alembic/
backend/app/repositories/
backend/app/models.py
```

## 2. 它解决什么问题

假设 v0.1 的 `document` 表只有：

```text
id
knowledge_id
name
file_path
```

v0.2 增加：

```text
status
error_message
```

只修改 Python Model 不会自动修改旧数据库。

如果旧表没有新字段，运行时可能报错：

```text
no such column: document.status
```

迁移要解决：

```text
新增或修改表结构
给旧数据回填默认值
创建索引和约束
记录数据库已经升级到哪个版本
必要时提供回滚路径
```

## 3. 和前端数据结构升级的类比

可以把数据库迁移类比成前端持久化数据升级。

旧版 `localStorage`：

```json
{
  "name": "知识库"
}
```

新版代码需要：

```json
{
  "name": "知识库",
  "searchMode": "blend"
}
```

如果直接读取旧数据，`searchMode` 不存在。

前端可能写：

```typescript
const value = {
  searchMode: "embedding",
  ...storedValue
}
```

数据库迁移做的是更正式的同类工作：

```text
识别旧结构
-> 新增字段或表
-> 回填旧记录
-> 建立新约束
```

## 4. `create_all` 为什么不够

本项目启动时会调用：

```python
Base.metadata.create_all(bind=engine)
```

它擅长：

```text
数据库还没有某张表时，创建这张表
```

它不会自动：

```text
给已有表增加字段
删除旧字段
修改字段类型
回填历史数据
创建 PostgreSQL 扩展
管理迁移版本
```

因此：

```text
create_all   适合创建新库的缺失表
migration    适合演进已有数据库
```

## 5. 本项目为什么有两套迁移机制

### 5.1 SQLite 轻量迁移

文件：

```text
backend/app/migrations.py
```

目标：

```text
保持本地学习环境零配置
保留已有 SQLite 学习数据
每次启动都能安全重复执行
```

核心规则：

```text
执行前检查表或字段是否存在
只补当前版本明确需要的结构
旧数据需要时回填默认值
重复执行不产生重复记录
```

### 5.2 PostgreSQL Alembic

目录：

```text
backend/alembic/
```

目标：

```text
显式记录结构版本
支持可审查的 upgrade / downgrade
创建 PostgreSQL 专属能力
让不同环境按相同顺序升级
```

## 6. SQLite 轻量迁移如何工作

入口：

```python
run_lightweight_migrations(engine)
```

只对 SQLite 执行：

```python
if database_engine.dialect.name != "sqlite":
    return
```

整体使用：

```python
with database_engine.begin() as connection:
    ...
```

含义：

```text
迁移全部成功   自动提交
中间抛出异常   自动回滚
```

常见步骤：

```text
读取已有表名
-> 创建缺失表
-> 读取已有字段
-> ALTER TABLE 增加缺失字段
-> UPDATE 回填旧数据
-> CREATE INDEX IF NOT EXISTS
-> 重建 FTS5 索引
```

## 7. 什么是幂等迁移

幂等表示：

```text
执行一次和执行多次，最终结果相同。
```

错误写法：

```sql
ALTER TABLE document ADD COLUMN status VARCHAR(20);
```

每次启动都执行，第二次会因为字段已存在而失败。

本项目先检查：

```python
document_columns = {
    column["name"]
    for column in inspector.get_columns("document")
}

if "status" not in document_columns:
    ...
```

索引使用：

```sql
CREATE INDEX IF NOT EXISTS ...
```

幂等很重要，因为应用可能：

```text
反复重启
迁移中途失败后重新启动
测试中重复调用迁移函数
```

## 8. 为什么迁移不仅是增加字段

新增字段后，旧行可能没有有效值。

例如新增：

```text
task.attempt_no
```

旧任务需要回填：

```text
attempt_no = 1
```

新增：

```text
task.idempotency_key
```

旧任务需要生成稳定值：

```text
legacy:{task_id}
```

新增 Outbox 后，旧的活动任务还需要补事件：

```text
PENDING / QUEUED / RETRYING / RUNNING Task
-> 检查当前 attempt 是否已有 OutboxEvent
-> 没有则创建 PENDING 事件
```

因此数据库迁移包含两部分：

```text
Schema Migration   修改结构
Data Migration     转换和回填旧数据
```

## 9. Alembic 是什么

一句话：

```text
Alembic 是 SQLAlchemy 生态中用于管理数据库结构版本的迁移工具。
```

核心概念：

```text
revision       当前迁移版本
down_revision  上一个版本
upgrade        升级动作
downgrade      回滚动作
```

本项目迁移链：

```text
0001_v05
-> 0002_v06
-> 0003_v07
```

对应内容：

| 版本 | 主要内容 |
| --- | --- |
| `0001_v05` | PostgreSQL 基线、pgvector、全文检索索引 |
| `0002_v06` | 持久化 `task` 表 |
| `0003_v07` | attempt、租约、`task_attempt`、`outbox_event` |

## 10. `upgrade` 和 `downgrade`

升级：

```python
def upgrade() -> None:
    op.add_column(...)
    op.create_table(...)
    op.create_index(...)
```

回滚：

```python
def downgrade() -> None:
    op.drop_table(...)
    op.drop_column(...)
```

不要把 `downgrade` 理解成完全无损撤销。

例如删除表：

```text
表结构可以重新创建
表中的历史数据无法自动恢复
```

本项目 `0003_v07` 回滚时：

```text
会删除 TaskAttempt 和 OutboxEvent 历史
不会恢复升级前 Task 的 RUNNING 状态
```

所以生产回滚前必须评估数据损失。

## 11. 离线和在线迁移

Alembic 环境提供两种模式。

在线迁移：

```text
连接数据库
-> 直接执行迁移
```

离线迁移：

```text
不连接数据库
-> 生成 SQL 文件
-> 先审查 SQL
-> 再由其他流程执行
```

本项目 `run_migrations_offline` 使用：

```python
literal_binds=True
```

让参数尽量直接渲染进 SQL，便于审查。

## 12. PostgreSQL 为什么适合生产演进

相比本地 SQLite，PostgreSQL 更适合：

```text
多进程并发写入
行级锁
FOR UPDATE SKIP LOCKED
复杂索引
全文检索
扩展机制
生产备份和运维
```

本项目在 PostgreSQL 中可以统一保存：

```text
业务数据
任务状态
Outbox 事件
全文检索索引
Embedding 向量
```

这让很多跨存储补偿可以收敛为数据库事务。

## 13. pgvector 是什么

一句话：

```text
pgvector 是 PostgreSQL 的向量类型和相似度检索扩展。
```

启用扩展：

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

模型字段：

```python
embedding: Mapped[list[float] | None] = mapped_column(
    Vector(EMBEDDING_DIMENSION),
    nullable=True,
)
```

本项目维度默认：

```text
256
```

向量查询：

```python
distance = EmbeddingRefModel.embedding.cosine_distance(query_embedding)
```

排序：

```text
余弦距离越小，越相似。
```

业务层需要越大越相关的分数，因此转换：

```python
score = 1.0 - distance
```

并限制到：

```text
0 到 1
```

## 14. HNSW 索引是什么

没有向量索引时，数据库可能需要逐行比较全部向量。

HNSW 是常见的近似最近邻索引：

```text
通过图结构快速找到相近向量
牺牲少量精确性换取查询速度
```

本项目 Alembic 中创建：

```text
HNSW
+ vector_cosine_ops
+ embedding IS NOT NULL
```

其中：

```text
vector_cosine_ops   表示按余弦距离组织索引
WHERE embedding IS NOT NULL   只索引真实向量行
```

## 15. PostgreSQL 全文检索

Paragraph 中定义计算列：

```text
search_vector
```

它由标题和正文生成：

```text
title   权重 A
content 权重 B
```

再建立：

```text
GIN 索引
```

查询使用：

```text
plainto_tsquery
ts_rank_cd
```

职责对照：

```text
pgvector + HNSW       语义相似度检索
tsvector + GIN        关键词全文检索
```

## 16. Repository 为什么重要

如果 Service 直接调用 Chroma：

```python
chroma_collection.query(...)
```

迁移到 pgvector 时，业务代码会大量改变。

本项目定义统一边界：

```python
class EmbeddingRepository(Protocol):
    def add_paragraphs(...): ...
    def upsert_paragraphs(...): ...
    def search(...): ...
    def delete_by_document(...): ...
    def delete_by_ids(...): ...
```

实现：

```text
ChromaEmbeddingRepository     SQLite + Chroma
PostgresEmbeddingRepository   PostgreSQL + pgvector
```

Service 只依赖接口：

```text
EmbeddingRepository
```

这和前端常见的 API Client 抽象类似：

```text
组件依赖统一 request 接口
底层可以是 fetch、Axios 或 Mock
```

## 17. `transactional` 表示什么

Chroma 实现：

```python
transactional = False
```

pgvector 实现：

```python
transactional = True
```

它表示：

```text
向量写入能否和当前 SQLAlchemy Session 共享同一个事务。
```

本地模式：

```text
SQLite rollback 不能撤销 Chroma 写入
-> 需要补偿删除或恢复
```

PostgreSQL 模式：

```text
业务表和 embedding 同库同事务
-> db.rollback() 一起撤销
```

## 18. 不使用和使用迁移工具的区别

不使用迁移：

```text
修改 Model
-> 删除旧数据库
-> 重新建库
-> 历史数据丢失
```

使用迁移：

```text
修改 Model
-> 编写版本迁移
-> 检查旧结构
-> 修改 Schema
-> 回填数据
-> 保留历史记录
```

学习项目可以偶尔删库重建，但正式系统不能把它当成升级方案。

## 19. 常见方案和生态

| 语言或 ORM | 常见迁移工具 |
| --- | --- |
| SQLAlchemy | Alembic |
| Django ORM | Django Migrations |
| Prisma | Prisma Migrate |
| TypeORM | TypeORM Migrations |
| Rails | Active Record Migrations |

向量存储常见选择：

```text
PostgreSQL + pgvector
Chroma
Milvus
Qdrant
Weaviate
Elasticsearch / OpenSearch
```

选择依据包括：

```text
数据规模
事务要求
检索性能
运维成本
过滤能力
团队已有基础设施
```

## 20. 优点

```text
数据库结构演进可追踪
旧数据可以有序回填
不同环境按相同版本升级
SQL 可以提前审查
pgvector 让业务数据和向量共享事务
Repository 限制底层存储差异扩散
```

## 21. 缺点与坑

### 21.1 Model 和迁移必须同步

只改 Model 不写迁移，旧数据库仍然无法运行。

### 21.2 Alembic 不会自动搬迁 SQLite 数据

当前 PostgreSQL 的 `0001_v05` 是新环境基线，不是 SQLite 到 PostgreSQL 的数据导入工具。

### 21.3 pgvector 扩展必须先可用

数据库服务器没有安装 `vector` 扩展时，迁移会失败。

### 21.4 向量维度必须一致

模型输出维度、`Vector(256)` 和已有索引必须匹配。

### 21.5 索引不是免费性能

HNSW 和 GIN 会增加：

```text
存储空间
写入成本
迁移时间
维护成本
```

### 21.6 `downgrade` 可能破坏数据

删除字段或表后，数据通常无法自动恢复。

### 21.7 SQLite 轻量迁移有边界

它适合学习项目，不适合长期承载大量复杂版本和多人协作迁移。

## 22. 推荐阅读代码顺序

```text
backend/app/database.py
-> backend/app/migrations.py
-> backend/alembic/env.py
-> backend/alembic/versions/0001_v05_postgresql_storage.py
-> backend/app/repositories/embedding_repository.py
-> backend/app/dependencies.py
```

重点观察：

```text
SQLite 和 PostgreSQL 在哪里分流
create_all 和轻量迁移如何配合
Alembic revision 如何连接
pgvector 字段和 HNSW 索引如何定义
Repository 如何隐藏后端差异
transactional 如何影响异常处理
```

## 23. 最小记忆模型

```text
create_all          创建缺失表，不升级已有表
轻量迁移            本地 SQLite 的幂等兼容方案
Alembic             PostgreSQL 的版本化迁移工具
upgrade             升级数据库结构和数据
downgrade           回滚结构，但不保证数据无损
Schema Migration    修改表、字段、索引和约束
Data Migration      转换和回填旧数据
PostgreSQL          生产数据库
pgvector            PostgreSQL 向量扩展
HNSW                向量近似检索索引
GIN                 全文检索索引
Repository          隔离底层存储实现
transactional       向量能否共享数据库事务
```

一句话总结：

```text
迁移负责让旧数据库跟上新代码，pgvector 则让向量和业务数据进入同一套 PostgreSQL 事务。
```
