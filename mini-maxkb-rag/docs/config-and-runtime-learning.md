# 配置与运行时目录学习笔记

## 1. 配置解决什么问题

项目运行时会依赖很多可变信息。

例如：

```text
数据库文件放哪里
上传文件放哪里
Chroma 向量数据放哪里
允许哪个前端域名访问
是否配置了大模型 API Key
默认召回多少段
embedding 维度是多少
```

这些信息不适合散落在各个业务文件里。

所以本项目集中放在：

```text
backend/app/config.py
```

一句话：

```text
config.py 负责把运行环境整理成代码可以直接使用的常量。
```

## 2. 本项目配置文件做什么

`config.py` 负责：

```text
读取环境变量
组织项目路径
提供默认配置
创建运行时目录
```

业务代码使用时直接导入：

```python
from app.config import DATABASE_URL
from app.config import CHROMA_DIR
from app.config import DEFAULT_TOP_K
```

这样好处是：

```text
配置入口统一
默认值清楚
后续改配置来源时影响范围小
业务代码不用到处 os.getenv
```

## 3. 路径配置

核心路径：

```python
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("MINI_MAXKB_DATA_DIR", BACKEND_DIR / "data"))
FILES_DIR = DATA_DIR / "files"
CHROMA_DIR = DATA_DIR / "chroma"
```

含义：

```text
BACKEND_DIR  backend 目录
DATA_DIR     后端运行时数据目录
FILES_DIR    上传文件保存目录
CHROMA_DIR   Chroma 持久化目录
```

默认结构：

```text
backend/data/
  app.db
  files/
  chroma/
```

## 4. `Path(__file__)` 是什么

代码：

```python
BACKEND_DIR = Path(__file__).resolve().parent.parent
```

拆开理解：

```text
__file__          当前文件路径，也就是 backend/app/config.py
Path(__file__)    把字符串路径变成 Path 对象
resolve()         转成绝对路径
parent            上一级目录
parent.parent     上两级目录
```

所以：

```text
backend/app/config.py
-> parent 是 backend/app
-> parent.parent 是 backend
```

最终：

```text
BACKEND_DIR 指向 backend 目录
```

## 5. `DATA_DIR` 为什么支持环境变量

代码：

```python
DATA_DIR = Path(os.getenv("MINI_MAXKB_DATA_DIR", BACKEND_DIR / "data"))
```

含义：

```text
如果设置了 MINI_MAXKB_DATA_DIR，就用环境变量指定的目录
如果没设置，就用 backend/data
```

这样本地学习可以直接运行。

部署或测试时也可以切换目录：

```bash
MINI_MAXKB_DATA_DIR=/tmp/mini-maxkb-data
```

好处：

```text
开发环境和测试环境可以用不同数据目录
不会把临时数据写死到代码里
```

## 6. 数据库配置

代码：

```python
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'app.db'}")
```

默认使用 SQLite：

```text
sqlite:///backend/data/app.db
```

如果设置环境变量：

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

项目就可以切到其他数据库。

学习版先用 SQLite 的原因：

```text
无需单独安装数据库服务
启动成本低
数据文件直观
适合理解 RAG 主链路
```

真实项目通常会使用：

```text
PostgreSQL
MySQL
云数据库
```

## 7. 文件目录配置

上传文件目录：

```python
FILES_DIR = DATA_DIR / "files"
```

使用位置：

```text
backend/app/storage/file_storage.py
```

保存路径形态：

```text
backend/data/files/{knowledge_id}/{uuid}-{filename}
```

为什么路径里包含 `knowledge_id`？

```text
不同知识库的上传文件天然分目录隔离
排查时更容易知道文件属于哪个知识库
```

为什么文件名前加 uuid？

```text
避免同名上传文件互相覆盖
```

## 8. Chroma 目录配置

向量数据目录：

```python
CHROMA_DIR = DATA_DIR / "chroma"
```

使用位置：

```text
backend/app/storage/vector_store.py
```

初始化：

```python
self.client = chromadb.PersistentClient(path=str(CHROMA_DIR), ...)
```

含义：

```text
Chroma 向量索引持久化保存到 backend/data/chroma。
```

如果删除这个目录：

```text
SQLite 业务数据可能还在
但向量索引会丢失
检索会查不到已上传文档对应的向量
```

所以 `app.db` 和 `chroma/` 要保持一致。

## 9. CORS 配置

代码：

```python
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]
```

含义：

```text
允许哪些前端地址跨域访问后端。
```

默认允许：

```text
http://localhost:5173
http://127.0.0.1:5173
```

因为前端 Vite 本地开发常用：

```text
5173
```

在 `main.py` 中使用：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

如果前端请求后端时报跨域错误，优先检查：

```text
CORS_ORIGINS 是否包含当前前端地址
协议、域名、端口是否完全一致
```

## 10. 大模型配置

代码：

```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
```

本项目支持 OpenAI-compatible Chat API。

意思是：

```text
只要服务兼容 /chat/completions 协议，就可以通过这些环境变量切换。
```

如果配置了 `OPENAI_API_KEY`：

```text
chat_service 会调用真实模型。
```

如果没有配置：

```text
chat_service 会走 fallback 简化回答。
```

这样设计的目的：

```text
没有 API Key 也能跑通上传、切分、向量化、检索和引用返回。
```

## 11. Embedding 配置

代码：

```python
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "256"))
```

含义：

```text
HashEmbeddingService 默认生成 256 维向量。
```

这个值影响：

```text
embedding_service.py 生成向量的长度
Chroma 中保存的向量维度
```

需要注意：

```text
同一个 Chroma collection 里向量维度必须一致。
```

如果改了 `EMBEDDING_DIMENSION`：

```text
旧向量通常需要重建
否则新旧维度可能不一致
```

## 12. 检索配置

代码：

```python
DEFAULT_TOP_K = int(os.getenv("DEFAULT_TOP_K", "4"))
```

含义：

```text
问答时默认召回 4 个段落。
```

在 `chat_api.py` 中：

```python
top_k = payload.top_k or DEFAULT_TOP_K
```

同时 `ChatRequest` 中也定义了默认值：

```python
top_k: int = Field(default=4, ge=1, le=20)
```

这说明：

```text
Schema 控制请求字段默认和范围
config 提供项目级默认配置
```

当前两处默认值都是 4。

## 13. 启动时准备什么

在 `main.py` 中：

```python
ensure_runtime_dirs()
create_tables()
```

`ensure_runtime_dirs()`：

```python
FILES_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)
```

作用：

```text
确保上传文件目录和 Chroma 目录存在。
```

`create_tables()`：

```python
Base.metadata.create_all(bind=engine)
```

作用：

```text
根据 SQLAlchemy Model 创建数据库表。
```

所以第一次启动项目时，不需要手动创建：

```text
backend/data/files
backend/data/chroma
backend/data/app.db 对应的表
```

## 14. 运行时数据是什么

运行时数据指：

```text
程序运行后生成的数据
```

本项目包括：

```text
SQLite 数据库文件
用户上传的原始文件
Chroma 向量索引
```

它们不是源码。

它们通常不应该被当作业务代码提交。

学习时可以删除这些数据重新跑。

但要知道：

```text
删除 app.db 会丢业务表数据
删除 files/ 会丢原始上传文件
删除 chroma/ 会丢向量索引
```

## 15. 常见环境变量

本项目常用环境变量：

```text
MINI_MAXKB_DATA_DIR   运行时数据根目录
DATABASE_URL          SQLAlchemy 数据库连接串
CORS_ORIGINS          允许跨域访问的前端地址
OPENAI_API_KEY        大模型 API Key
OPENAI_BASE_URL       OpenAI-compatible API 地址
OPENAI_CHAT_MODEL     聊天模型名
EMBEDDING_DIMENSION   本地哈希向量维度
DEFAULT_TOP_K         默认检索条数
```

配置优先级：

```text
环境变量存在 -> 使用环境变量
环境变量不存在 -> 使用代码里的默认值
```

## 16. 常见问题排查

问题：上传文件失败。

检查：

```text
FILES_DIR 是否创建成功
文件后缀是否是 .txt 或 .md
进程是否有写入 backend/data/files 的权限
```

问题：检索不到内容。

检查：

```text
CHROMA_DIR 是否存在
上传文档后 Chroma 是否写入成功
是否误删了 backend/data/chroma
EMBEDDING_DIMENSION 是否改过
```

问题：数据库没有表。

检查：

```text
main.py 是否执行 create_tables()
DATABASE_URL 是否指向预期的 app.db
```

问题：前端跨域。

检查：

```text
CORS_ORIGINS 是否包含前端实际 origin
localhost 和 127.0.0.1 是否混用
端口是否一致
```

问题：没有调用真实模型。

检查：

```text
OPENAI_API_KEY 是否设置
OPENAI_BASE_URL 是否正确
OPENAI_CHAT_MODEL 是否可用
```

## 17. 学习项目和生产项目的区别

学习项目：

```text
启动时自动 create_all
本地 SQLite
本地文件系统
本地 Chroma 持久化目录
没有复杂配置中心
```

生产项目通常会有：

```text
数据库迁移工具
对象存储
独立向量数据库服务
配置中心或密钥管理
多环境配置
日志和监控
异步任务
```

但核心思想一样：

```text
业务代码不要到处硬编码环境差异。
```

## 18. 最小记忆模型

```text
config.py = 配置集中入口
DATA_DIR = 运行时数据根目录
FILES_DIR = 原始文件目录
CHROMA_DIR = 向量索引目录
DATABASE_URL = 数据库连接串
CORS_ORIGINS = 前端跨域白名单
ensure_runtime_dirs = 启动时创建必要目录
```
