"""
FastAPI 应用入口。

启动后会提供：
- 知识库文件夹接口
- 知识库接口
- 文档上传接口
- 文档段落查看接口
- 问题增强接口
- 知识库问答接口

运行命令：
uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat_api import router as chat_router
from app.api.document_api import router as document_router
from app.api.knowledge_folder_api import router as knowledge_folder_router
from app.api.knowledge_api import router as knowledge_router
from app.api.problem_api import router as problem_router
from app.api.task_api import router as task_router
from app.config import CORS_ORIGINS, OUTBOX_RELAY_IN_WEB, ensure_runtime_dirs
from app.database import create_tables
from app.services.outbox_service import OutboxRelay


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    """
    单机 background 模式随 Web 启动 Relay；生产 Celery 模式运行独立进程。
    """

    relay = OutboxRelay() if OUTBOX_RELAY_IN_WEB else None
    if relay is not None:
        relay.start()
    try:
        yield
    finally:
        if relay is not None:
            relay.stop()


def create_app() -> FastAPI:
    """
    创建 FastAPI app。

    把 app 创建过程放进函数里，后续写测试时可以直接复用 create_app。
    """

    ensure_runtime_dirs()
    create_tables()

    app = FastAPI(
        title="Mini MaxKB RAG API",
        description="一个用于学习 MaxKB RAG 主链路的简化后端",
        version="0.7.0",
        lifespan=app_lifespan,
    )

    # CORS 用于允许本地前端访问后端。
    # 前端 Vite 默认地址通常是 http://localhost:5173。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(knowledge_folder_router)
    app.include_router(knowledge_router)
    app.include_router(document_router)
    app.include_router(problem_router)
    app.include_router(task_router)
    app.include_router(chat_router)

    return app


app = create_app()


@app.get("/api/health")
def health_check():
    """
    健康检查接口。

    前端或部署平台可以调用它确认后端是否已启动。
    """

    return {"status": "ok"}
