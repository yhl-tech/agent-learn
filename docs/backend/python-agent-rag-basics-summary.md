# Python Agent 与 RAG 基础概念速查

这份笔记整理学习 `03_tool_calling.py` 和 `04_rag_qa.py` 时遇到的基础概念。

目标不是覆盖所有细节，而是把高频概念压缩成容易复习的判断规则。

## 1. `from pydantic import BaseModel, Field`

```python
from pydantic import BaseModel, Field
```

可以按职责理解：

```text
BaseModel  让普通类变成 Pydantic 数据模型
Field      给字段补充说明、默认值或校验规则
```

在 Agent 开发里，Pydantic 常用于：

```text
工具参数 schema
模型结构化输出
FastAPI 请求体
FastAPI 响应体
配置校验
```

## 2. `class FileItem(BaseModel)` 是什么

```python
class FileItem(BaseModel):
    path: str = Field(description="文件路径")
    purpose: str = Field(description="文件用途")
```

这是 Python 的类继承语法。

```text
class 子类名(父类名):
```

含义是：

```text
定义 FileItem 类，并继承 BaseModel 的能力。
```

继承 `BaseModel` 后，`FileItem` 会获得：

```text
字段校验
类型转换
schema 生成
model_validate
model_dump
model_dump_json
```

## 3. `Field(description=...)` 是什么

```python
path: str = Field(description="文件路径")
```

可以拆成两部分：

```text
path: str                 字段名和类型
Field(description="...")  字段说明
```

在 Tool Calling 里，`description` 会帮助模型理解这个字段应该填什么。

它不是给 Python 运行逻辑看的核心数据，而是给 schema、文档、模型和 IDE 使用的说明信息。

## 4. `model_validate` 谁可以用

`model_validate` 是 Pydantic v2 的 `BaseModel` 类方法。

谁继承了 `BaseModel`，谁就可以用：

```python
FileItem.model_validate(...)
FilePlanInput.model_validate(...)
```

普通类默认不能用：

```python
class User:
    pass

User.model_validate(...)  # 不行
```

典型用途：

```python
item = {"path": "src/App.tsx", "purpose": "页面组件"}
file_item = FileItem.model_validate(item)
```

结果是把外部 `dict` 校验并转换成 `FileItem` 对象。

## 5. `tool_call: Dict[str, Any]` 是什么

```python
def run_tool_call(tool_call: Dict[str, Any]) -> str:
```

这是函数参数和返回值的类型标注。

```text
tool_call        参数名
Dict[str, Any]   字符串 key、任意 value 的字典
-> str           函数返回字符串
```

可以类比 TypeScript：

```ts
Record<string, any>
```

在 Tool Calling 里，`tool_call` 通常长这样：

```python
{
    "name": "create_file_plan",
    "args": {
        "page_name": "订单列表页",
        "files": [...]
    }
}
```

所以代码里可以读取：

```python
tool_call["name"]
tool_call["args"]
```

## 6. 生产项目是否都写类型标注

不是所有 Python 代码都必须写类型标注。

但正式生产项目里，类型标注越来越常见，尤其是：

```text
后端服务
SDK
Agent 工程
FastAPI 项目
Pydantic 项目
多人协作项目
```

优先写这些位置：

```text
函数入参
函数返回值
数据模型
公共接口
配置对象
工具参数
```

可以少写的位置：

```text
临时脚本
Notebook
很短的局部变量
一次性验证代码
```

判断标准：

```text
长期维护、多人协作、接口边界清晰 -> 建议写
临时实验、一次性脚本 -> 可以少写
```

## 7. 常见基类

Agent 和后端开发中常见的基类：

| 基类 | 来自 | 常见用途 |
| --- | --- | --- |
| `BaseModel` | `pydantic` | 结构化数据、字段校验、工具参数、API schema |
| `BaseSettings` | `pydantic-settings` | 环境变量配置模型 |
| `TypedDict` | `typing` | 定义字典形状，常用于 LangGraph State |
| `Enum` | `enum` | 定义固定选项，例如状态、类型、错误码 |
| `ABC` | `abc` | 定义抽象基类，要求子类实现方法 |
| `Protocol` | `typing` | 定义接口形状，关注“能不能这么用” |
| `Exception` | 内置 | 自定义异常 |
| `DeclarativeBase` | `sqlalchemy.orm` | SQLAlchemy ORM 模型基类 |
| `TestCase` | `unittest` | 单元测试类，项目里也常直接用 pytest 函数风格 |

优先掌握：

```text
BaseModel -> 结构化数据和校验
TypedDict -> LangGraph 状态
Enum -> 固定状态和类型
Exception -> 明确错误类型
DeclarativeBase -> 数据库模型
```

## 8. RAG 里的 metadata 是什么

metadata 是“描述数据的数据”。

正文内容：

```text
Button 支持 primary、secondary、danger 三种类型。
```

metadata：

```python
{
    "source": "docs/components/button.md",
    "title": "Button 组件说明",
    "updated_at": "2026-10-29",
    "permission": "frontend"
}
```

区别：

```text
page_content  内容本身
metadata      内容的来源、标题、权限、更新时间等说明信息
```

RAG 使用 metadata 做这些事：

```text
标明答案来源
按权限过滤文档
按知识库或文件过滤
定位原始文档
排查回答依据
```

## 9. chunk 是什么

RAG 通常不会把整篇文档直接交给模型，而是先切成多个小片段。

这些片段就是 chunk。

```text
原始文档
-> chunk1
-> chunk2
-> chunk3
```

chunk 是 RAG 的最小检索单位。

用户提问时，系统不是检索整篇文档，而是检索最相关的 chunk。

## 10. `chunk_size` 和 `chunk_overlap`

```python
RecursiveCharacterTextSplitter(
    chunk_size=220,
    chunk_overlap=40,
)
```

含义：

```text
chunk_size     每个 chunk 的大致长度
chunk_overlap  相邻 chunk 之间重复保留的内容长度
```

为什么需要 overlap：

```text
切文档时，关键语义可能刚好落在边界附近。
overlap 可以让边界附近内容同时出现在前后两个 chunk 里。
```

参数影响：

```text
chunk_size 太大     上下文浪费，容易混入无关信息
chunk_size 太小     语义被切碎，答案可能不完整
overlap 太小        边界语义可能被切断
overlap 太大        重复内容变多，成本上升
```

## 11. Top-K 是什么

Top-K 是检索阶段的参数。

含义：

```text
所有 chunk 排序后，只取前 K 个最相关结果。
```

在示例代码里：

```python
def retrieve_context(question: str, chunks: Iterable[Document], k: int = 3):
    ...
    return ranked_chunks[:k]
```

`k=3` 表示：

```text
排序后只拿前 3 个 chunk 给模型。
```

## 12. `chunk_size / overlap` 和 Top-K 的区别

它们发生在不同阶段：

```text
chunk_size / chunk_overlap  控制文档怎么切
Top-K                       控制检索后取几个
```

完整流程：

```text
原始文档
-> 按 chunk_size / overlap 切成 chunks
-> 用户提问
-> 给 chunks 排序
-> 取 Top-K 个 chunk
-> 拼成 context
-> 交给模型回答
```

一句话：

```text
chunk 参数决定候选材料怎么生产，Top-K 决定最后挑几份材料交给模型。
```

## 13. Top-K 由什么决定

Top-K 不是模型天然决定的，一般由开发者根据效果和成本配置。

主要看：

```text
问题复杂度    跨多个文档的问题通常需要更大的 k
chunk_size    chunk 越大，单块信息越多，k 可以小一点
上下文窗口    模型能吃的 token 有限，k 不能无限大
检索质量      检索不稳定时，适当增大 k 提高召回
噪音成本      k 太大会塞入无关资料，干扰模型
延迟成本      k 越大，上下文越长，模型调用越慢越贵
```

经验起点：

```text
简单 FAQ           k = 3
普通知识库问答     k = 3 ~ 5
复杂跨文档问题     k = 5 ~ 10
有 rerank 的系统   先召回 20 ~ 50，再 rerank 取 3 ~ 8
```

最可靠的方式是用 Eval 调参：

```text
准备固定问题集
分别测试 k=3、5、8
看正确来源是否被检索到
看回答是否更准确
看无关内容是否变多
```

## 14. 召回率低是什么意思

召回率衡量“相关内容有没有找全”。

公式：

```text
召回率 = 被找出来的相关内容 / 所有真实相关内容
```

例子：

```text
知识库里真实相关内容有 5 段
检索只找出来 2 段
召回率 = 2 / 5 = 40%
```

召回率低说明：

```text
相关内容明明在知识库里，但检索阶段漏掉了。
```

在 RAG 里的后果：

```text
检索没找全资料
-> 模型拿不到足够上下文
-> 回答不完整、答错或说不确定
```

和准确率的区别：

```text
召回率低  该找的没找全，问题是“漏”
准确率低  找出来的很多不相关，问题是“杂”
```

常见原因：

```text
chunk 切得不好
Top-K 太小
问题表达和文档表达差异大
embedding 模型效果一般
metadata 过滤条件太严
缺少关键词 + 向量混合检索
```

## 15. 一句话速记

```text
BaseModel 让类具备数据校验能力。
Field 给字段补充说明和规则。
model_validate 把外部数据校验并转换成模型对象。
类型标注帮助 IDE、读代码的人和检查工具理解数据结构。
metadata 说明内容从哪里来、属于谁、能不能用。
chunk 是 RAG 的最小检索单位。
chunk_size / overlap 决定文档怎么切。
Top-K 决定检索后取几个 chunk。
召回率低说明相关资料没找全。
```
