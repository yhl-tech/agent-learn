# 异步任务、Transactional Outbox 与幂等执行学习笔记

## 1. 一句话定义

```text
异步任务把耗时工作移出 HTTP 请求；
Transactional Outbox 保证业务数据提交后，任务消息最终能够被投递；
数据库状态机和幂等写入保证重复消息不会产生重复业务结果。
```

本项目当前的完整链路不是简单的：

```text
API -> Celery
```

而是：

```text
API
-> 同一数据库事务写入 Document、Task、OutboxEvent
-> Outbox Relay 读取并发布事件
-> Redis/Celery 传递 task_id + attempt_no
-> Worker 从数据库条件认领任务
-> 执行文档解析、切分和向量化
-> 数据库记录最终状态
```

其中各组件的职责不同：

```text
Task / TaskAttempt   保存任务事实和执行历史
OutboxEvent          保存“待投递消息”
Outbox Relay         把数据库事件发布到执行器
Redis                Celery 的消息 Broker
Celery               将消息交给 Worker
Worker               真正执行文档索引
```

最重要的边界是：

```text
数据库是任务状态的唯一事实来源。
Redis 和 Celery 只负责消息传递，不负责决定任务最终状态。
```

## 2. 它解决什么问题

### 2.1 同步处理会阻塞上传接口

如果上传接口直接完成全部工作：

```text
保存文件
-> 读取文件
-> 文本切分
-> 生成 embedding
-> 写入向量索引
-> 返回 HTTP 响应
```

那么接口响应时间等于整条处理链路的时间。

小文件可能只需要几百毫秒，大文件或远程 embedding 模型可能需要几十秒。此时会出现：

```text
请求长时间占用 Web Worker
反向代理或客户端超时
用户不知道任务执行到哪一步
进程退出后任务没有恢复入口
同一时间上传多个文件时吞吐量下降
```

异步化后，上传接口只负责持久化最小事实：

```text
保存原始文件
创建 PENDING Document
创建 PENDING Task
创建 PENDING OutboxEvent
提交事务
返回 document 和 task
```

耗时索引由后台 Worker 执行。

### 2.2 直接发送 Celery 消息存在数据丢失窗口

最直观的写法是：

```python
db.add(document)
db.commit()
celery_app.send_task("index_document", args=[document.id])
```

如果数据库提交成功后，进程在 `send_task` 前退出：

```text
Document 已存在
Task 可能已存在
Celery 消息不存在
```

数据库里会留下一个永远没有 Worker 处理的任务。

反过来，如果先发消息再提交数据库：

```python
celery_app.send_task("index_document", args=[document.id])
db.commit()
```

Worker 可能先收到消息，但数据库事务随后失败：

```text
Celery 消息已存在
Document 或 Task 不存在
```

这说明：

```text
数据库事务和 Redis 消息发布不是同一个原子事务。
调整调用顺序不能消除故障窗口。
```

Transactional Outbox 的作用，就是把“业务数据”和“准备发送的事件”放入同一个数据库事务。

### 2.3 消息系统通常只能保证至少一次投递

Celery 发布成功后，Relay 还需要把 Outbox 状态改成 `PUBLISHED`。

下面这个时间点仍可能崩溃：

```text
消息已发送到 Redis
-> Relay 进程退出
-> Outbox 还停留在 PUBLISHING
```

Outbox 租约到期后，另一个 Relay 会重新发布该事件。因此同一个消息可能被发送两次。

本项目接受这个事实：

```text
投递语义：至少一次
业务目标：重复执行不产生重复结果
```

不要把它误解成“消息只会出现一次”。

### 2.4 Worker 也可能执行到一半退出

例如 Worker 已经：

```text
读取文件
-> 切分段落
-> 生成向量
```

但还没有提交最终成功状态就退出。

系统需要知道：

```text
哪个 Worker 正在执行
它是否还活着
当前执行权是否可以被接管
旧 Worker 恢复后是否还能继续写入
```

因此项目增加了：

```text
worker_id
heartbeat_at
lease_expires_at
attempt_no
```

它们共同构成可恢复的任务认领协议。

## 3. 熟悉概念与新概念对照

### 3.1 和前端请求状态对照

| 前端熟悉概念 | 异步任务中的对应概念 |
|---|---|
| 请求 ID | `task.id` |
| 当前请求状态 | `task.status` |
| 第几次重新请求 | `task.attempt_no` |
| 请求错误信息 | `task.error_code` / `error_message` |
| AbortController 标记取消 | `task.cancel_requested` |
| 轮询请求结果 | `GET /api/tasks/{task_id}` |
| 防止旧响应覆盖新响应 | attempt 和 worker 所有权校验 |

前端常见竞态是：

```text
请求 1 先发出
请求 2 后发出
请求 2 先返回
请求 1 后返回并覆盖新状态
```

任务系统中的旧消息问题非常相似：

```text
attempt 1 的消息延迟到达
用户已经发起 attempt 2
旧消息不能再执行并覆盖新结果
```

本项目通过 `task_id + attempt_no` 条件认领阻止旧消息。

### 3.2 和数据库乐观更新对照

前端或后端常用条件更新避免覆盖：

```sql
UPDATE resource
SET value = :new_value
WHERE id = :id
  AND version = :expected_version;
```

如果影响行数为 `0`，表示当前版本已经变化。

本项目认领任务使用相同思想：

```sql
UPDATE task
SET status = 'RUNNING',
    worker_id = :worker_id
WHERE id = :task_id
  AND attempt_no = :attempt_no
  AND cancel_requested = false
  AND status 在可认领范围内;
```

只有影响一行的 Worker 获得执行权。

### 3.3 和订单支付对照

可以把任务处理理解成订单履约：

```text
Task             订单当前状态
TaskAttempt      每次履约尝试记录
OutboxEvent      待发送的履约通知
Relay            发通知的扫描器
Celery/Redis     消息运输通道
Worker           实际履约者
```

订单表已经提交，不代表通知一定发送成功；通知发送两次，也不应重复扣款。

对应到本项目：

```text
Task 已创建，不代表 Worker 已收到消息。
Worker 收到两次消息，不应生成两套段落和向量。
```

## 4. 不使用与使用方案对比

### 4.1 同步执行

不使用异步任务：

```python
@router.post("/documents")
async def upload_document(...):
    document = save_document(...)
    process_document(document.id)
    return document
```

问题：

```text
HTTP 请求承担全部耗时
任务状态只能依赖请求是否返回
进程崩溃后难以恢复
无法独立扩容索引 Worker
```

使用异步任务：

```python
document, task = create_document_task(...)
return {
    "document": document,
    "task": task,
}
```

后台独立完成：

```text
Outbox Relay -> Celery -> Worker -> 更新 Task
```

### 4.2 直接发送消息

不使用 Outbox：

```python
db.add(task)
db.commit()
celery_app.send_task("index_document", args=[task.id])
```

故障窗口：

```text
数据库提交成功
进程退出
消息永远没有发送
```

使用 Outbox：

```python
db.add(task)
db.add(
    OutboxEventModel(
        task_id=task.id,
        attempt_no=task.attempt_no,
        status="PENDING",
    )
)
db.commit()
```

此时只有两种结果：

```text
事务成功：
Task 和 OutboxEvent 同时存在，Relay 后续可以补发。

事务失败：
Task 和 OutboxEvent 都不存在，不会出现孤立任务。
```

### 4.3 无条件执行消息

不做条件认领：

```python
def run_document_task(task_id: str):
    process_document(task_id)
```

重复消息会导致：

```text
重复切分
重复段落
重复向量
旧任务覆盖新任务状态
两个 Worker 并发写同一文档
```

使用条件认领：

```python
document_id = _claim_task(
    db,
    task_id=task_id,
    attempt_no=attempt_no,
    worker_id=worker_id,
)
if document_id is None:
    return "IGNORED"
```

只有认领成功的 Worker 可以继续。

### 4.4 随机写入 ID

如果每次重试都生成随机段落 ID 和向量 ID：

```text
第一次执行写入 A
Worker 崩溃
第二次执行写入 B
最终可能同时留下 A 和 B
```

本项目使用稳定 ID：

```python
paragraph_id = uuid.uuid5(
    uuid.NAMESPACE_URL,
    f"mini-maxkb:paragraph:{task_id}:{position}:{content_hash}",
)

vector_id = uuid.uuid5(
    uuid.NAMESPACE_URL,
    f"mini-maxkb:vector:{paragraph_id}",
)
```

同一任务、同一位置、同一内容会得到相同 ID，再配合 upsert：

```text
第一次写入 ID X
重复执行仍写入 ID X
结果被覆盖或保持一致，而不是新增 ID Y
```

## 5. 本项目代码链路

### 5.1 上传接口创建任务

入口：

```text
backend/app/api/document_api.py
-> backend/app/services/document_service.py
```

`create_document_task` 先保存实体文件，然后在一个数据库事务中创建：

```text
FileModel
DocumentModel(status=PENDING)
TaskModel(status=PENDING, attempt_no=1)
OutboxEventModel(status=PENDING)
```

核心关系：

```text
File 1 -> N Document
Document 1 -> N Task
Task 1 -> N TaskAttempt
Task 1 -> N OutboxEvent
```

文件已经先写到磁盘，因此数据库事务失败时还需要删除实体文件。这属于数据库事务之外的补偿。

### 5.2 Outbox 事件与业务数据同事务提交

代码位置：

```text
backend/app/services/outbox_service.py
```

`enqueue_document_task_event` 只执行 `db.add(event)`，不自行提交：

```python
event = OutboxEventModel(
    task_id=task.id,
    attempt_no=task.attempt_no,
    deduplication_key=f"DOCUMENT_INDEX_REQUESTED:{task.id}:{task.attempt_no}",
    payload={
        "task_id": task.id,
        "attempt_no": task.attempt_no,
    },
    status="PENDING",
)
db.add(event)
```

提交权保留给外层调用者，才能保证：

```text
Task 与 OutboxEvent 一起 commit
Task 与 OutboxEvent 一起 rollback
```

`deduplication_key` 对同一个任务 attempt 唯一，防止业务代码重复创建相同事件。

### 5.3 Relay 认领 Outbox

代码位置：

```text
backend/app/repositories/outbox_repository.py
backend/app/services/outbox_service.py
```

Relay 查询：

```text
available_at 已到期
并且：
  status = PENDING
  或 status = PUBLISHING 且 leased_until 已过期
```

认领后更新：

```text
status = PUBLISHING
leased_until = 当前时间 + 租约时间
attempts += 1
```

生产 PostgreSQL 使用：

```sql
FOR UPDATE SKIP LOCKED
```

这样多个 Relay 可以并发领取不同事件。

网络发布在数据库认领事务提交后进行，避免发送 Redis 请求时长期占用数据库行锁。

### 5.4 Relay 发布消息

Celery 模式下：

```text
Outbox Relay
-> CeleryTaskPublisher
-> Redis
-> Celery Worker
```

消息只携带：

```json
{
  "task_id": "task-id",
  "attempt_no": 1
}
```

不传递：

```text
SQLAlchemy Session
ORM 对象
embedding 实例
完整文档内容
```

因为跨进程消息应该只传稳定、可序列化、可重新查询的最小标识。

本地 `background` 模式下：

```text
Web 进程内 Outbox Relay 线程
-> BackgroundTaskPublisher
-> run_document_task(...)
```

它不需要 Redis，但仍然复用相同的：

```text
Outbox
Task 状态机
attempt 条件认领
幂等索引逻辑
```

因此它是本地执行适配器，不是另一套业务流程。

### 5.5 Worker 条件认领 Task

代码位置：

```text
backend/app/tasks/document_tasks.py
-> backend/app/services/task_service.py
```

`_claim_task` 使用单条条件 `UPDATE`。

认领条件包括：

```text
task.id 匹配
task.type 匹配
task.attempt_no 等于消息中的 attempt_no
cancel_requested = false
状态为 PENDING / QUEUED / RETRYING
或者 RUNNING 但租约已过期
next_retry_at 已到期
```

认领成功后：

```text
Task.status = RUNNING
Task.worker_id = 当前 Worker
Task.heartbeat_at = 当前时间
Task.lease_expires_at = 当前时间 + 租约
Document.status = PROCESSING
创建或更新 TaskAttempt
```

如果条件更新影响行数不是 `1`，消息被忽略。

常见被忽略的消息：

```text
同一 attempt 的重复投递
人工重试前遗留的旧 attempt 消息
已取消任务的消息
任务已经成功后的迟到消息
另一个 Worker 仍持有有效租约
```

### 5.6 Lease 与 heartbeat

Lease 表示：

```text
当前 Worker 在 lease_expires_at 之前拥有执行权。
```

Heartbeat 表示：

```text
Worker 周期性证明自己仍在运行，并延长 lease_expires_at。
```

正常执行：

```text
Worker 认领
-> 启动独立心跳线程
-> 每隔 TASK_HEARTBEAT_INTERVAL_SECONDS 续租
-> 完成后清空租约
```

异常退出：

```text
Worker 不再续租
-> lease_expires_at 到期
-> 后续重复消息可以由新 Worker 接管
```

旧 Worker 如果恢复，会在阶段边界检查：

```text
attempt_no 是否仍匹配
status 是否仍为 RUNNING
worker_id 是否仍属于自己
```

所有权已经变化时，它会停止后续写入。

心跳使用独立 Session，原因是：

```text
索引正文事务可能持续较久
心跳需要独立提交
心跳不能意外提交或回滚正文事务
```

### 5.7 Task 与 TaskAttempt 的区别

`TaskModel` 保存当前快照：

```text
当前状态
当前 attempt_no
当前 worker_id
重试次数
下次重试时间
取消标记
最终错误
```

`TaskAttemptModel` 保存每次执行历史：

```text
第几次执行
由哪个 Worker 执行
何时开始
最后一次心跳
何时结束
本次错误
```

可以类比：

```text
Task          Git 分支当前 HEAD
TaskAttempt   每一次历史 commit
```

只看 Task 可以回答“现在怎样”，查看 TaskAttempt 才能回答“之前发生过什么”。

### 5.8 自动重试

本项目只对明确的临时错误自动重试：

```text
ConnectionError
OperationalError
SoftTimeLimitExceeded
TimeoutError
```

永久性内容错误不会反复重试，例如：

```text
文件不存在
文档内容为空
文件编码或内容不合法
```

临时失败时，同一事务会完成：

```text
当前 TaskAttempt -> FAILED
Task.attempt_no += 1
Task.status -> RETRYING
设置 next_retry_at
创建新 attempt 对应的 OutboxEvent
Document -> PENDING
```

重试间隔使用指数退避和确定性抖动：

```text
基础间隔 * 2^(attempt_no - 1)
最高不超过 TASK_RETRY_MAX_SECONDS
再增加 0% 到 20% 的稳定抖动
```

作用：

```text
避免依赖恢复时大量任务同时重试
避免持续高频请求故障服务
同一 task + attempt 的延迟可重复，便于测试和排查
```

### 5.9 人工重试

接口：

```http
POST /api/tasks/{task_id}/retry
```

只允许：

```text
FAILED
CANCELLED
```

人工重试会：

```text
attempt_no += 1
重新授予自动重试额度
清空旧执行上下文
Task -> RETRYING
Document -> PENDING
创建新的 OutboxEvent
```

旧消息携带旧 `attempt_no`，因此不能认领新任务。

### 5.10 软取消

接口：

```http
POST /api/tasks/{task_id}/cancel
```

未运行任务：

```text
设置 cancel_requested = true
丢弃未发布 Outbox
Task -> CANCELLED
Document -> CANCELLED
```

正在运行的任务：

```text
设置 cancel_requested = true
Worker 在切分、向量准备、向量写入等阶段边界检查
发现取消后停止，并清理可能写入的外部向量
Task -> CANCELLED
Document -> CANCELLED
```

Celery `revoke(..., terminate=False)` 只是尽力减少无效消费。

真正可靠的判断是：

```text
数据库中的 cancel_requested
```

项目不强杀正在执行的 Worker，因为强杀可能发生在任意写入中间点，增加数据半完成和资源泄漏风险。

### 5.11 向量写入的幂等与补偿

pgvector 模式：

```text
Paragraph
EmbeddingRef
向量
Task.SUCCESS
Document.SUCCESS
```

都可以参与同一个 PostgreSQL 事务。失败时 `rollback` 即可撤销本次写入。

Chroma 模式：

```text
SQLite 事务
Chroma 写入
```

无法形成同一个数据库事务。因此失败或取消时，需要按稳定 `vector_id` 尽力删除已写入向量。

两种模式都使用 upsert 和稳定 ID，目的是让至少一次执行最终收敛到同一结果。

## 6. 常见方案与生态

### 6.1 进程内后台任务

常见方案：

```text
FastAPI BackgroundTasks
线程池
本项目 BackgroundTaskPublisher
```

适合：

```text
本地开发
短任务
允许随 Web 进程一起停止
不需要独立扩容
```

限制：

```text
Web 重启会中断正在运行的任务
资源与 Web 请求竞争
不适合多机调度
```

本项目的 background 模式仍通过 Outbox 租约补发未完成事件，比直接调用 `BackgroundTasks.add_task` 多保留了一层数据库恢复能力。

### 6.2 独立任务队列

常见方案：

```text
Celery + Redis
Celery + RabbitMQ
RQ
Dramatiq
Arq
```

本项目使用：

```text
Celery + Redis Broker
```

并配置：

```text
late ack
Worker 丢失时拒绝确认
单任务预取
visibility timeout
soft / hard time limit
```

这些配置增强消息恢复能力，但不能代替业务幂等。

### 6.3 Transactional Outbox 的常见发布方式

```text
轮询数据库表
PostgreSQL LISTEN / NOTIFY 辅助唤醒
CDC 读取数据库变更日志
Debezium + Kafka
```

本项目采用轮询数据库表：

```text
实现直接
容易观察和测试
适合当前规模
```

规模增大后，才需要评估 CDC 或专门消息基础设施。

### 6.4 状态查询方式

常见方式：

```text
前端轮询 GET /tasks/{id}
Server-Sent Events
WebSocket
消息通知
```

当前项目使用数据库任务状态接口，前端可以轮询。

无论采用哪种推送方式，最终状态仍应来自数据库，而不是只相信一次临时通知。

## 7. 优点

### 7.1 HTTP 接口快速返回

上传接口不再等待完整索引结束，减少超时和 Web Worker 长时间占用。

### 7.2 业务提交后任务最终可投递

Task 和 OutboxEvent 同事务写入。即使 API 提交后立即退出，Relay 仍可在后续扫描并投递。

### 7.3 可以承受重复消息

attempt 条件认领、Worker 所有权校验、稳定 ID 和 upsert 共同让重复投递收敛到同一结果。

### 7.4 可以恢复失联 Worker

租约到期后，其他 Worker 可以接管任务，不会永久停留在 `RUNNING`。

### 7.5 状态可查询、历史可审计

Task 提供当前状态，TaskAttempt 保留每次执行细节，便于定位：

```text
是否从未投递
是否重复投递
在哪一次失败
由哪个 Worker 执行
最后心跳时间
```

### 7.6 本地与生产复用同一业务状态机

本地使用 background publisher，生产使用 Celery publisher。二者只替换消息发布和执行位置，不复制文档处理逻辑。

## 8. 缺点与常见坑

### 8.1 至少一次不等于恰好一次

只要发送消息和更新 Outbox 状态不是同一个原子操作，就必须接受重复发布。

正确目标不是幻想消息永不重复，而是：

```text
允许重复到达
拒绝无权执行
重复执行时结果幂等
```

### 8.2 幂等不能只靠 Task 状态

Worker 可能在写入外部 Chroma 后、提交数据库成功状态前退出。

仅检查 `Task.status` 不够，还需要：

```text
稳定业务 ID
upsert
外部存储补偿
数据库唯一约束
```

### 8.3 Redis 不能作为最终状态来源

Celery result backend 可能过期、丢失或与数据库业务状态不一致。

本项目关闭 result backend，统一查询 `task` 表。

### 8.4 租约必须长于合理的心跳间隔

如果租约过短：

```text
Worker 仍在正常执行
心跳偶尔延迟
租约提前到期
另一个 Worker 错误接管
```

因此必须满足：

```text
0 < heartbeat interval < lease duration
```

还要结合任务耗时、数据库抖动和部署环境设置余量。

### 8.5 Celery visibility timeout 必须大于任务 hard time limit

否则任务尚未结束，Redis 就可能把消息重新交给另一个 Worker。

本项目启动时校验：

```text
CELERY_VISIBILITY_TIMEOUT > CELERY_TASK_TIME_LIMIT
```

### 8.6 取消不是瞬时中断

软取消只会在业务设置的检查点生效。

如果某个单步调用长时间不返回，例如远程 embedding 请求卡住，那么取消要等该调用结束或超时后才能被观察到。

所以仍需要给外部请求设置合理 timeout。

### 8.7 Outbox 表也需要治理

长期运行后会积累大量：

```text
PUBLISHED
DISCARDED
```

生产系统通常需要：

```text
保留周期
归档或清理任务
积压量监控
最老 PENDING 时间监控
连续失败告警
```

### 8.8 SQLite 不适合多 Relay 并发

本地 SQLite 可以演示相同状态机，但其写锁模型不适合多个 Relay 和大量 Worker 并发。

生产 PostgreSQL 才使用 `FOR UPDATE SKIP LOCKED` 实现可靠的并发领取。

### 8.9 心跳不能和正文事务共用 Session

如果心跳线程复用正文 Session：

```text
线程不安全
心跳 commit 可能提前提交正文
心跳 rollback 可能撤销正文
```

因此本项目为心跳创建独立 Session。

### 8.10 重试必须区分临时错误和永久错误

对文档内容为空反复重试没有意义，只会制造队列噪声。

反过来，数据库连接短暂断开通常值得自动重试。

需要明确错误分类，而不是对所有异常统一重试。

## 9. 最小记忆模型

先记住三层：

```text
第一层：可靠创建
业务数据 + Task + OutboxEvent 在同一事务提交。

第二层：可靠投递
Relay 通过租约领取 Outbox，失败后退避重试。

第三层：可靠执行
Worker 按 task_id + attempt_no 条件认领，
用 lease + heartbeat 维护执行权，
用稳定 ID + upsert 消化重复执行。
```

再记住三条边界：

```text
数据库是事实来源，Celery 只是运输通道。
至少一次投递一定要配合幂等消费。
跨数据库与外部存储无法原子提交时，需要补偿。
```

最后把本项目主链路压缩成一句话：

```text
上传事务留下 Task 和 Outbox，Relay 最终发出消息，Worker 条件认领并续租执行，
重复消息由 attempt 拒绝，重复写入由稳定 ID 收敛，最终状态统一落回数据库。
```
