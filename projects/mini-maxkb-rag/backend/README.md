# Mini MaxKB RAG 后端

这是 `mini-maxkb-rag` 的学习版后端，当前已覆盖：

```text
知识库/文件夹 -> Outbox 异步文档入库 -> 混合检索 -> 问题增强 -> 生成回答
```

## 1. 安装依赖

建议在 `backend` 目录下创建虚拟环境：

```bash
cd /Users/bytedance/Desktop/code/agent/mini-maxkb-rag/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. SQLite + Chroma 启动

```bash
uvicorn app.main:app --reload
```

启动后可以打开：

```text
http://127.0.0.1:8000/docs
```

FastAPI 会自动生成接口调试页面。

SQLite 会在启动时自动建表并执行兼容迁移，向量默认写入 `data/chroma/`。
默认 `TASK_EXECUTOR=background`，Web 进程会启动一个内嵌 Outbox Relay，适合
本地单进程开发，不需要 Redis。

## 3. PostgreSQL + pgvector + Celery 启动

生产模式要求 PostgreSQL 已安装 `vector` 扩展，并准备 Redis broker：

```bash
export DATABASE_URL="postgresql+psycopg://user:password@127.0.0.1:5432/mini_maxkb"
export VECTOR_BACKEND="pgvector"
export TASK_EXECUTOR="celery"
export OUTBOX_RELAY_IN_WEB="false"
export CELERY_BROKER_URL="redis://127.0.0.1:6379/0"

alembic upgrade head
```

分别启动 Web、Worker 和 Outbox Relay：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
celery -A app.celery_app:celery_app worker --loglevel=INFO
python -m app.outbox_relay
```

PostgreSQL 模式必须先执行 Alembic。迁移会创建 `vector` 扩展、HNSW 向量
索引、`tsvector`/GIN 全文检索索引，以及 `task_attempt`、`outbox_event`
任务可靠性表。

`VECTOR_BACKEND=auto` 是默认值：PostgreSQL 自动使用 pgvector，SQLite 自动
使用 Chroma。迁移阶段也可以显式设置 `chroma` 或 `pgvector`。

Celery 已启用 late ack、Worker 丢失重投、单任务预取、JSON 消息，并关闭
result backend。Redis 生产实例应使用 `noeviction`、AOF 持久化和 TLS；
`CELERY_VISIBILITY_TIMEOUT` 必须大于任务 hard time limit。

生产多 Worker 必须使用 PostgreSQL 和可共享的 pgvector/外部向量库。当前原始
文件仍保存在本地目录，多节点部署前应将 `file_storage` 适配为对象存储。

## 4. 任务可靠性配置

```text
TASK_MAX_ATTEMPTS=3
TASK_RETRY_BASE_SECONDS=5
TASK_RETRY_MAX_SECONDS=300
TASK_LEASE_SECONDS=120
TASK_HEARTBEAT_INTERVAL_SECONDS=15
OUTBOX_BATCH_SIZE=10
OUTBOX_LEASE_SECONDS=60
OUTBOX_POLL_INTERVAL_SECONDS=0.2
CELERY_TASK_SOFT_TIME_LIMIT=3300
CELERY_TASK_TIME_LIMIT=3600
CELERY_VISIBILITY_TIMEOUT=3900
```

上传事务会同时提交 `File + Document + Task + Outbox`。Relay 使用
`FOR UPDATE SKIP LOCKED` 并按租约发布；即使发布后进程在回写前退出，事件也会
再次投递。Worker 通过 `task_id + attempt_no` 条件认领，重复消息不会重复建索引。

## 5. 可选模型配置

如果不配置 `OPENAI_API_KEY`，问答接口会返回基于召回段落的简化回答。

如果要接入 OpenAI-compatible Chat API，可以配置：

```bash
export OPENAI_API_KEY="你的 API Key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_CHAT_MODEL="gpt-4o-mini"
```

## 6. 当前接口

```text
GET  /api/health

POST /api/knowledges
GET  /api/knowledges
PATCH /api/knowledges/{knowledge_id}/folder
PATCH /api/knowledges/{knowledge_id}/retrieval-config

POST   /api/knowledge-folders
GET    /api/knowledge-folders
PATCH  /api/knowledge-folders/{folder_id}
DELETE /api/knowledge-folders/{folder_id}

POST /api/knowledges/{knowledge_id}/documents
GET  /api/knowledges/{knowledge_id}/documents

GET  /api/documents/{document_id}/paragraphs
GET  /api/documents/{document_id}/file
DELETE /api/documents/{document_id}
POST   /api/documents/{document_id}/reindex

POST   /api/paragraphs/{paragraph_id}/problems
GET    /api/paragraphs/{paragraph_id}/problems
DELETE /api/problems/{problem_id}

GET  /api/tasks/{task_id}
POST /api/tasks/{task_id}/retry
POST /api/tasks/{task_id}/cancel

POST /api/knowledges/{knowledge_id}/chat
POST /api/knowledges/{knowledge_id}/retrieval-test
```

上传接口返回 `202 Accepted`，响应包含 PENDING 文档字段和 `task`。前端通过
`GET /api/tasks/{task_id}` 轮询最终结果。

文档和任务状态包括：

```text
document.status  PENDING / PROCESSING / SUCCESS / FAILED / CANCELLED
task.status      PENDING / QUEUED / RETRYING / RUNNING / SUCCESS / FAILED / CANCELLED
error_message    最近一次处理失败原因
paragraph_count  当前段落数量
source_file_id   原始文件元数据 ID
```

问题增强会为常见问法单独建立向量。检索命中问题向量后，服务会通过
`problem_paragraph_mapping` 回到原始段落，因此回答引用始终展示文档原文。

## 7. 测试

```bash
python -m unittest discover -s tests -v
```

测试覆盖重复消息、旧 attempt、Outbox 发布失败补发、自动重试上限、取消、
SQLite 旧库迁移和文档/向量补偿。

## 8. 运行时数据

运行时数据默认保存在：

```text
backend/data/
  app.db
  files/
  chroma/
```

这些数据是本地开发数据，不应该提交到 Git。
