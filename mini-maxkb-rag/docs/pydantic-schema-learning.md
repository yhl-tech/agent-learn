# Pydantic Schema 学习笔记

## 1. Schema 是什么

在这个项目里：

```text
SQLAlchemy Model 描述数据库怎么存
Pydantic Schema 描述 API 怎么收、怎么返回
```

对应文件：

```text
数据库模型：backend/app/models.py
接口模型：backend/app/schemas.py
```

一句话：

```text
Model 是数据库合同，Schema 是接口合同。
```

## 2. 为什么不能只用 Model

数据库表字段和接口字段不一定一样。

例如 `DocumentModel` 里有：

```text
id
knowledge_id
name
file_path
char_length
created_at
updated_at
```

但返回给前端的 `DocumentRead` 没有 `file_path`：

```python
class DocumentRead(BaseModel):
    id: str
    knowledge_id: str
    name: str
    char_length: int
    created_at: datetime
    updated_at: datetime
```

原因：

```text
file_path 是后端内部存储路径
前端通常不需要知道
也不应该把服务器本地路径直接暴露出去
```

所以 Schema 可以隔离：

```text
数据库内部结构
API 对外结构
```

## 3. 请求体 Schema

请求体 Schema 用来校验前端传入的数据。

例如创建知识库：

```python
class KnowledgeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str = ""
```

它表示：

```text
name 必须是字符串
name 长度至少 1
name 长度最多 150
description 是字符串
description 不传时默认为空字符串
```

前端请求：

```json
{
  "name": "产品文档",
  "description": "用于测试 RAG"
}
```

FastAPI 会自动把 JSON 转成：

```text
KnowledgeCreate 对象
```

然后接口里可以直接用：

```python
payload.name
payload.description
```

## 4. 问答请求体

问答请求：

```python
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=20)
```

字段含义：

```text
question  用户问题
top_k     最多召回多少个段落
```

校验规则：

```text
question 不能为空
question 最多 2000 个字符
top_k 默认 4
top_k 最小 1
top_k 最大 20
```

合法请求：

```json
{
  "question": "如何上传文档？",
  "top_k": 4
}
```

非法请求：

```json
{
  "question": "",
  "top_k": 100
}
```

非法时，FastAPI 会自动返回：

```text
422 Unprocessable Entity
```

业务函数甚至不会进入。

## 5. `Field` 是什么

`Field` 用来给字段补充规则和默认值。

例子：

```python
name: str = Field(min_length=1, max_length=150)
top_k: int = Field(default=4, ge=1, le=20)
```

常见参数：

```text
default      默认值
min_length   字符串最小长度
max_length   字符串最大长度
ge           greater or equal，大于等于
le           less or equal，小于等于
```

所以：

```python
top_k: int = Field(default=4, ge=1, le=20)
```

可以读成：

```text
top_k 是整数
默认是 4
必须大于等于 1
必须小于等于 20
```

## 6. 响应 Schema

响应 Schema 用来规定后端返回什么。

例如：

```python
class ChatResponse(BaseModel):
    answer: str
    references: List[ReferenceRead]
```

表示问答接口返回：

```json
{
  "answer": "...",
  "references": [...]
}
```

引用来源：

```python
class ReferenceRead(BaseModel):
    document_id: str
    document_name: str
    paragraph_id: str
    content: str
    score: float
```

它告诉前端：

```text
答案来自哪份文档
来自哪个段落
引用原文是什么
相似度分数是多少
```

## 7. `response_model` 和 Schema 的关系

接口中使用：

```python
@router.post("/{knowledge_id}/chat", response_model=ChatResponse)
```

含义：

```text
这个接口的返回值必须符合 ChatResponse。
```

FastAPI 会根据 `response_model`：

```text
转换返回对象
过滤多余字段
生成 OpenAPI 文档
让 /docs 显示响应结构
```

例如上传文档接口：

```python
@router.post("/api/knowledges/{knowledge_id}/documents", response_model=DocumentRead)
```

service 返回的是：

```text
DocumentModel
```

接口响应会按：

```text
DocumentRead
```

输出给前端。

## 8. `from_attributes=True`

代码：

```python
model_config = {"from_attributes": True}
```

作用：

```text
允许 Pydantic 从对象属性里读取字段。
```

为什么需要？

service 返回的是 SQLAlchemy 对象：

```python
return knowledge
```

它不是 dict。

它是：

```text
KnowledgeModel 实例
```

有了 `from_attributes=True`，Pydantic 可以从对象属性读取：

```text
knowledge.id
knowledge.name
knowledge.description
knowledge.created_at
knowledge.updated_at
```

然后生成：

```text
KnowledgeRead
```

如果没有这个配置，Pydantic 可能不知道如何从 ORM 对象里取字段。

## 9. `BaseModel` 是什么

所有 Schema 都继承：

```python
BaseModel
```

它提供：

```text
字段声明
类型校验
默认值处理
序列化成 JSON
从 JSON 解析成对象
错误信息生成
```

例如：

```python
class KnowledgeCreate(BaseModel):
    name: str
```

就表示：

```text
KnowledgeCreate 必须有一个 name 字段，并且它是字符串。
```

## 10. `list[DocumentRead]` 是什么

接口：

```python
@router.get("/api/knowledges/{knowledge_id}/documents", response_model=list[DocumentRead])
```

表示返回一个列表。

列表里的每一项都要符合：

```text
DocumentRead
```

也就是：

```json
[
  {
    "id": "...",
    "knowledge_id": "...",
    "name": "...",
    "char_length": 123,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

## 11. Schema 和类型提示的关系

Pydantic 会读取 Python 类型提示：

```python
question: str
top_k: int
references: List[ReferenceRead]
```

这些类型提示不只是给人看。

FastAPI 会用它们来：

```text
解析请求
校验数据
生成接口文档
序列化响应
```

所以写 Schema 时，类型要尽量准确。

例如 `score` 是：

```python
score: float
```

因为相似度分数不是整数。

## 12. 本项目里的 Schema 分类

创建类：

```text
KnowledgeCreate
```

读取类：

```text
KnowledgeRead
DocumentRead
ParagraphRead
ReferenceRead
```

动作请求类：

```text
ChatRequest
```

动作响应类：

```text
ChatResponse
```

命名习惯：

```text
Create  前端创建资源时传入
Read    后端返回资源时输出
Request 执行动作时的请求体
Response 执行动作后的响应体
```

## 13. Schema 不是业务逻辑

Schema 负责数据结构和校验。

它不应该负责：

```text
创建数据库记录
保存文件
切分文本
调用向量库
生成回答
```

这些应该放在 service 或 storage。

例如：

```python
class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=4, ge=1, le=20)
```

它只说明：

```text
问题是什么
召回几条
字段是否合法
```

真正的检索由：

```text
retrieval_service.py
```

完成。

## 14. 常见误区

误区一：把数据库字段全部返回给前端。

```text
不一定需要。
例如 file_path 是后端内部路径，DocumentRead 没有暴露。
```

误区二：请求和响应共用一个 Schema。

```text
创建时前端不传 id、created_at。
返回时后端需要带 id、created_at。
所以 Create 和 Read 通常分开。
```

误区三：把业务默认值都放 Schema。

```text
字段默认值可以放 Schema。
但复杂业务默认值应该放 service 或 config。
```

误区四：忽略字段范围。

```text
top_k 如果不限制，用户传 10000 可能导致检索和 prompt 都变重。
```

## 15. 最小记忆模型

```text
Schema = API 数据合同
请求 Schema = 校验前端输入
响应 Schema = 控制后端输出
Field = 字段规则
response_model = 接口返回结构
from_attributes=True = 允许从 ORM 对象读字段
```
