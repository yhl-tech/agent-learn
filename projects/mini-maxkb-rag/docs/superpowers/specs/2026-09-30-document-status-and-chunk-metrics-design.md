# 文档状态与切分指标设计

## 1. 目标

为同步文档入库流程补充可观察状态，并记录每个段落的字符长度。

本阶段只实现：

- `document.status`
- `document.error_message`
- `paragraph.chunk_length`
- 上传过程中的状态流转
- 兼容现有 SQLite 数据的轻量迁移
- 对应自动化测试

文档删除、重新索引、异步任务和前端展示不在本阶段实现。

## 2. 状态设计

文档支持以下状态：

```text
PENDING     已创建，等待处理
PROCESSING  正在读取、切分和写入向量
SUCCESS     段落与向量均写入成功
FAILED      处理失败
```

上传仍是同步接口，但保留 `PENDING`，便于后续切换到异步任务时复用同一套状态。

失败原因写入 `error_message`。成功后该字段必须为空。

知识库不存在、文件扩展名不支持等前置校验失败时，不创建文档记录。文件已经保存且文档记录已经创建后发生的读取、切分或索引异常，才进入 `FAILED` 状态。

## 3. 数据模型

`DocumentModel` 新增：

```text
status         String(20)，默认 PENDING
error_message  Text，可空
```

`ParagraphModel` 新增：

```text
chunk_length   Integer，保存 content 的字符数
```

状态使用字符串常量，不引入数据库枚举，避免 SQLite 枚举迁移增加当前学习阶段的复杂度。

## 4. 上传流程

```text
校验文件
-> 保存原始文件
-> 创建 PENDING 文档
-> 更新为 PROCESSING
-> 读取和切分文本
-> 写入段落、向量和向量引用
-> 更新为 SUCCESS
```

出现处理异常时：

```text
回滚当前数据库事务
-> 按 document_id 清理可能已写入的 Chroma 向量
-> 将文档更新为 FAILED
-> 保存精简后的错误原因
-> 向 API 层抛出业务异常
```

原始文件保留，为后续重新索引功能提供输入。

`PENDING` 文档先单独提交，再更新并提交为 `PROCESSING`。这样后续处理事务回滚时，文档本身仍然存在，可以继续记录 `FAILED` 和失败原因。

## 5. SQLite 兼容迁移

当前项目使用 `Base.metadata.create_all()`，它只能创建新表，不能给已有表增加字段。

本阶段增加独立的轻量迁移函数：

1. 先由 ORM 的 `create_all()` 创建尚不存在的新表。
2. 再通过 SQLAlchemy Inspector 检查字段是否存在。
3. 仅对 SQLite 执行幂等的 `ALTER TABLE ADD COLUMN`。
4. 将已有文档状态回填为 `SUCCESS`。
5. 将已有段落的 `chunk_length` 回填为 `length(content)`。

该迁移只解决当前新增字段，不替代后续 v0.5 的 Alembic。

## 6. 接口变化

现有接口路径不变。

`DocumentRead` 增加：

```text
status
error_message
```

`ParagraphRead` 增加：

```text
chunk_length
```

这样后续前端无需新增接口即可展示处理状态和段落长度。

## 7. 注释要求

新增注释重点解释：

- 为什么 `create_all()` 不能修改已有表。
- 四种文档状态的生命周期。
- 为什么失败时需要分别处理 SQLite、Chroma 和原始文件。
- 为什么当前使用轻量迁移，以及它与 Alembic 的边界。

不添加逐行复述代码含义的注释。

## 8. 测试

使用临时数据目录，避免污染 `backend/data`。

覆盖：

- 新数据库创建后包含新增字段。
- 旧表可以幂等迁移并正确回填。
- 上传成功后文档状态为 `SUCCESS`。
- 段落 `chunk_length` 等于内容字符数。
- 空文档或处理异常后文档状态为 `FAILED`。
- 失败后没有残留段落、向量引用和 Chroma 向量。
