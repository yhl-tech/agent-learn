# Mini MaxKB RAG 后端

这是 `mini-maxkb-rag` 的第一版后端，用来跑通最小 RAG 链路：

```text
创建知识库 -> 上传文档 -> 文本切分 -> 生成向量 -> 检索段落 -> 生成回答
```

## 1. 安装依赖

建议在 `backend` 目录下创建虚拟环境：

```bash
cd /Users/bytedance/Desktop/code/agent/mini-maxkb-rag/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 启动服务

```bash
uvicorn app.main:app --reload
```

启动后可以打开：

```text
http://127.0.0.1:8000/docs
```

FastAPI 会自动生成接口调试页面。

## 3. 可选模型配置

如果不配置 `OPENAI_API_KEY`，问答接口会返回基于召回段落的简化回答。

如果要接入 OpenAI-compatible Chat API，可以配置：

```bash
export OPENAI_API_KEY="你的 API Key"
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_CHAT_MODEL="gpt-4o-mini"
```

## 4. 当前接口

```text
GET  /api/health

POST /api/knowledges
GET  /api/knowledges

POST /api/knowledges/{knowledge_id}/documents
GET  /api/knowledges/{knowledge_id}/documents

GET  /api/documents/{document_id}/paragraphs

POST /api/knowledges/{knowledge_id}/chat
```

## 5. 运行时数据

运行时数据默认保存在：

```text
backend/data/
  app.db
  files/
  chroma/
```

这些数据是本地开发数据，不应该提交到 Git。
