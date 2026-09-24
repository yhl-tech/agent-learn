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
# 第一版用 SQLite，后续 v0.5 可以替换成 PostgreSQL。
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")

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


def ensure_runtime_dirs() -> None:
    """
    确保运行时目录存在。

    FastAPI 启动时会调用这个函数。
    这样用户第一次运行项目时，不需要手动创建 data/files 或 data/chroma。
    """

    FILES_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
