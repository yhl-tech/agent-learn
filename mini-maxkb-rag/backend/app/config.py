"""
应用配置模块。

这个文件只负责读取和组织配置，不写业务逻辑。
把配置集中放在这里有两个好处：
1. 其他模块不用到处拼路径、读环境变量。
2. 后续从本地学习版升级到生产环境时，只需要替换配置来源。
"""

import os
from pathlib import Path


# BACKEND_DIR 指向 backend 目录。
# Path(__file__) 是当前文件 app/config.py，
# parent.parent 就是 backend/。
BACKEND_DIR = Path(__file__).resolve().parent.parent

# DATA_DIR 是后端运行时数据目录。
# SQLite 数据库、上传文件、Chroma 向量数据都会放在这里。
DATA_DIR = Path(os.getenv("MINI_MAXKB_DATA_DIR", BACKEND_DIR / "data"))

# FILES_DIR 保存用户上传的原始文件。
FILES_DIR = DATA_DIR / "files"

# CHROMA_DIR 保存 Chroma 的持久化向量索引。
CHROMA_DIR = DATA_DIR / "chroma"

# DATABASE_URL 是 SQLAlchemy 使用的数据库连接串。
# 默认使用 SQLite；设置 PostgreSQL 连接串后由 Alembic 管理表结构。
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

# VECTOR_BACKEND 控制向量保存位置。
# auto 会在 PostgreSQL 下选择 pgvector，其余数据库保持 Chroma，便于本地学习
# 环境零配置启动，也允许迁移期间显式固定后端以排查问题。
VECTOR_BACKEND = os.getenv("VECTOR_BACKEND", "auto").lower()
if VECTOR_BACKEND == "auto":
    VECTOR_BACKEND = (
        "pgvector"
        if DATABASE_URL.startswith(("postgresql://", "postgresql+"))
        else "chroma"
    )
if VECTOR_BACKEND not in {"chroma", "pgvector"}:
    raise ValueError("VECTOR_BACKEND 只支持 auto、chroma 或 pgvector")

# CORS_ORIGINS 控制允许哪些前端域名访问后端。
# 本地开发时 Vite 默认是 5173。
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

# OpenAI-compatible Chat API 配置。
# 如果没有配置 OPENAI_API_KEY，系统会走本地简化回答逻辑，方便先跑通链路。
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")

# 本地哈希向量维度。
# 维度不用太大，学习项目里 256 维足够演示相似度检索流程。
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "256"))

# 检索默认返回的段落数量。
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "4"))

# TASK_EXECUTOR=background 适合单机开发：Web 进程内的 Relay 线程读取 Outbox，
# 再调用同一套任务执行函数。生产环境使用 celery，由独立 Relay 投递到 Redis。
TASK_EXECUTOR = os.getenv("TASK_EXECUTOR", "background").lower()
if TASK_EXECUTOR not in {"background", "celery"}:
    raise ValueError("TASK_EXECUTOR 只支持 background 或 celery")

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_VISIBILITY_TIMEOUT = int(
    os.getenv("CELERY_VISIBILITY_TIMEOUT", "3900")
)
CELERY_TASK_SOFT_TIME_LIMIT = int(
    os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "3300")
)
CELERY_TASK_TIME_LIMIT = int(os.getenv("CELERY_TASK_TIME_LIMIT", "3600"))
if not 0 < CELERY_TASK_SOFT_TIME_LIMIT < CELERY_TASK_TIME_LIMIT:
    raise ValueError("Celery soft time limit 必须大于 0 且小于 hard time limit")
if CELERY_VISIBILITY_TIMEOUT <= CELERY_TASK_TIME_LIMIT:
    raise ValueError("CELERY_VISIBILITY_TIMEOUT 必须大于 CELERY_TASK_TIME_LIMIT")

TASK_MAX_ATTEMPTS = int(os.getenv("TASK_MAX_ATTEMPTS", "3"))
TASK_RETRY_BASE_SECONDS = int(os.getenv("TASK_RETRY_BASE_SECONDS", "5"))
TASK_RETRY_MAX_SECONDS = int(os.getenv("TASK_RETRY_MAX_SECONDS", "300"))
TASK_LEASE_SECONDS = int(os.getenv("TASK_LEASE_SECONDS", "120"))
TASK_HEARTBEAT_INTERVAL_SECONDS = int(
    os.getenv("TASK_HEARTBEAT_INTERVAL_SECONDS", "15")
)
if TASK_MAX_ATTEMPTS < 1:
    raise ValueError("TASK_MAX_ATTEMPTS 必须大于等于 1")
if TASK_RETRY_BASE_SECONDS < 0 or TASK_RETRY_MAX_SECONDS < TASK_RETRY_BASE_SECONDS:
    raise ValueError("任务重试间隔配置无效")
if not 0 < TASK_HEARTBEAT_INTERVAL_SECONDS < TASK_LEASE_SECONDS:
    raise ValueError("任务心跳间隔必须大于 0 且小于任务租约")

OUTBOX_BATCH_SIZE = int(os.getenv("OUTBOX_BATCH_SIZE", "10"))
OUTBOX_LEASE_SECONDS = int(os.getenv("OUTBOX_LEASE_SECONDS", "60"))
OUTBOX_POLL_INTERVAL_SECONDS = float(
    os.getenv("OUTBOX_POLL_INTERVAL_SECONDS", "0.2")
)
if (
    OUTBOX_BATCH_SIZE < 1
    or OUTBOX_LEASE_SECONDS < 1
    or OUTBOX_POLL_INTERVAL_SECONDS <= 0
):
    raise ValueError("Outbox 批次、租约和轮询间隔必须为正数")
# Celery 部署应运行独立 Relay 进程；background 模式默认随 Web 启动，保持本地
# 零额外进程体验。显式配置后也可关闭内嵌 Relay，验证崩溃后的补发流程。
OUTBOX_RELAY_IN_WEB = os.getenv(
    "OUTBOX_RELAY_IN_WEB",
    "true" if TASK_EXECUTOR == "background" else "false",
).lower() in {"1", "true", "yes", "on"}


def ensure_runtime_dirs() -> None:
    """
    确保运行时目录存在。

    FastAPI 启动时会调用这个函数。
    这样用户第一次运行项目时，不需要手动创建 data/files 或 data/chroma。
    """

    FILES_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
