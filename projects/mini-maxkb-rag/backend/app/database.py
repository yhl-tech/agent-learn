"""
数据库连接模块。

这个项目第一版使用 SQLite，是为了降低学习成本。
真实项目中，这一层可以替换成 PostgreSQL，业务代码尽量不用关心底层数据库变化。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL


# create_engine 创建数据库引擎。
# connect_args={"check_same_thread": False} 是 SQLite 在 FastAPI 场景下常见配置：
# FastAPI 请求可能在不同线程处理，SQLite 默认不允许跨线程使用同一个连接。
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,
)

# SessionLocal 是数据库会话工厂。
# 每个 API 请求都会创建一个 Session，用完后关闭。
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """
    所有 SQLAlchemy 模型的基类。

    models.py 里的 Knowledge、Document 等表模型都会继承它。
    """


def get_db():
    """
    FastAPI 依赖函数：给每个请求提供数据库会话。

    yield 之前的 db 会传给 API 函数。
    请求结束后 finally 会关闭连接，避免连接泄漏。
    """

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """
    初始化当前数据库表。

    SQLite 为保持零配置体验继续自动建表并执行轻量迁移；PostgreSQL 的扩展、
    生成列和 HNSW/GIN 索引必须通过 Alembic 明确管理。
    """

    # 显式导入 models，确保即使测试或脚本只调用 create_tables()，
    # SQLAlchemy 的 metadata 里也已经注册了所有业务表。
    from app import models as _models  # noqa: F401
    from app.migrations import run_lightweight_migrations

    if engine.dialect.name != "sqlite":
        return

    Base.metadata.create_all(bind=engine)
    # create_all 不会修改已经存在的表，因此建表后还要执行兼容迁移。
    # 新数据库已经包含完整字段，迁移函数会检查后直接跳过 ALTER TABLE。
    run_lightweight_migrations(engine)
