# 问题增强召回学习笔记

## 1. 一句话定义

```text
问题增强是为知识段落补充“用户可能怎样提问”，并给这些问题单独建立向量索引。
```

检索命中问题向量后，不把问题文本直接交给大模型，而是回到它关联的原始段落。

核心代码：

```text
backend/app/api/problem_api.py
backend/app/services/problem_service.py
backend/app/services/retrieval_service.py
backend/app/models.py
```

## 2. 它解决什么问题

原始文档通常使用说明性语言：

```text
退款将在三个工作日内到账。
```

用户可能这样问：

```text
退款多久到账？
退的钱什么时候回来？
退款三天能到吗？
```

段落和问题表达方式不同，尤其使用简化 Embedding 模型时，直接检索原文可能漏召回。

问题增强增加一层更接近用户表达的检索入口：

```text
原始段落
-> 补充可能的问题
-> 为问题建立向量
-> 用户提问更容易命中
-> 再回到原始段落回答
```

## 3. 和前端搜索别名的类比

可以把它理解成给一条记录增加搜索别名。

原始数据：

```typescript
const article = {
  title: "退款到账时效",
  content: "退款将在三个工作日内到账。"
}
```

搜索别名：

```typescript
const aliases = [
  "退款多久到账",
  "退的钱什么时候回来"
]
```

用户命中别名后，页面最终展示的仍然是原始文章，而不是只展示别名。

本项目也是同样的关系：

```text
Problem     用于提高召回概率
Paragraph   用于提供真实回答依据
```

## 4. 不使用和使用问题增强的区别

不使用问题增强：

```text
用户问题
-> 和 Paragraph 向量比较
-> 命中段落
```

使用问题增强：

```text
                    -> Paragraph 向量 --\
用户问题 -> 向量                         -> 候选段落
                    -> Problem 向量 ----/
                                           |
                                           -> 回到 Paragraph
```

问题增强没有替代段落向量，而是增加了一条召回通道。

## 5. 本项目的三张核心表

### 5.1 `problem`

保存问题文本：

```text
id
knowledge_id
content
created_at
updated_at
```

示例：

```text
problem-001 | kb-001 | 退款多久到账？
```

### 5.2 `problem_paragraph_mapping`

保存问题与段落的关联：

```text
problem_id
paragraph_id
document_id
knowledge_id
```

示例：

```text
problem-001 -> paragraph-008
```

使用独立映射表的原因：

```text
数据模型允许一个问题关联多个段落
未来可以复用标准问题
关系可以独立查询和扩展
```

当前 API 从单个段落创建问题，但没有把这一阶段的交互限制固化成数据库一对一。

### 5.3 `embedding_ref`

问题向量和段落向量共用同一套向量引用结构，通过字段区分来源：

```text
source_type = PARAGRAPH   普通段落向量
source_type = PROBLEM     问题增强向量
```

问题向量还会保存：

```text
problem_id
paragraph_id
document_id
knowledge_id
vector_id
```

## 6. 为什么需要 Mapping 表

可以直接在 `problem` 表保存 `paragraph_id`：

```text
problem.paragraph_id
```

但这会把关系固定成：

```text
一个 Problem 只能对应一个 Paragraph
```

使用映射表后：

```text
Problem 1 -> N ProblemParagraphMapping
Paragraph 1 -> N ProblemParagraphMapping
```

从数据模型上可以表达多对多。

最小规则：

```text
Problem 保存问题本身
Paragraph 保存原始知识
Mapping 保存两者之间的关系
```

## 7. 创建问题的完整链路

接口：

```http
POST /api/paragraphs/{paragraph_id}/problems
```

请求：

```json
{
  "content": "退款多久到账？"
}
```

Service 流程：

```text
检查问题内容不为空
-> 查询 Paragraph
-> 查询所属 Document
-> 检查同一段落是否已有相同问题
-> 创建 Problem
-> 创建 ProblemParagraphMapping
-> flush 获得数据库 ID
-> 对问题文本生成 Embedding
-> 写入问题向量
-> commit
```

核心写入：

```python
problem = ProblemModel(
    knowledge_id=paragraph.knowledge_id,
    content=payload.content,
)

mapping = ProblemParagraphMappingModel(
    knowledge_id=paragraph.knowledge_id,
    document_id=paragraph.document_id,
    problem_id=problem_id,
    paragraph_id=paragraph.id,
)
```

向量 metadata：

```python
{
    "knowledge_id": paragraph.knowledge_id,
    "document_id": paragraph.document_id,
    "paragraph_id": paragraph.id,
    "problem_id": problem.id,
    "source_type": "PROBLEM",
}
```

## 8. 为什么问题向量仍保存 `paragraph_id`

问题真正的关系来源是：

```text
ProblemParagraphMapping
```

但旧版 SQLite 的 `embedding_ref.paragraph_id` 是非空字段。

因此问题向量仍保存一个主段落 ID：

```text
兼容已有数据库约束
方便向量 metadata 快速定位
真实关系仍以 Mapping 表为准
```

这是一种兼容性设计，不应误解为映射表没有作用。

## 9. 检索命中问题后如何回到原文

`_build_embedding_candidates` 先识别向量来源：

```python
source_type = result.metadata.get(
    "source_type",
    EMBEDDING_SOURCE_PARAGRAPH,
)
```

如果是问题向量：

```text
读取 problem_id
-> 批量查询 ProblemParagraphMapping
-> 找到关联 paragraph_id
-> 生成段落候选
```

候选的命中类型会标记为：

```text
problem
```

最后 `_load_retrieved_paragraphs` 加载真正的：

```text
ParagraphModel
DocumentModel
```

因此给 LLM 的上下文仍然是原始段落。

## 10. 为什么不能把 Problem 当成回答依据

问题文本通常只有一句：

```text
退款多久到账？
```

它不包含答案。

如果直接把 Problem 当成上下文：

```text
用户问题：退款多久到账？
模型上下文：退款多久到账？
```

模型仍然没有事实依据。

正确做法：

```text
问题用于召回
段落用于回答
```

这是问题增强最重要的边界。

## 11. 为什么要防止重复问题

同一段落反复添加完全相同的问题，会产生：

```text
重复数据库记录
重复向量
召回候选重复
无意义的存储和计算
```

本项目在创建前查询：

```text
同一个 paragraph_id
+ 完全相同的 problem.content
```

存在时返回冲突。

当前只检查完全相同文本，不负责识别语义重复：

```text
退款多久到账？
退款何时到账？
```

这两条仍会被视为不同问题。

## 12. SQLite + Chroma 为什么需要补偿

本地模式使用两个独立存储：

```text
SQLite   保存 Problem、Mapping、EmbeddingRef
Chroma   保存真实向量
```

它们没有共同事务。

可能出现：

```text
Chroma 向量写入成功
-> SQLite commit 失败
-> 向量成为孤立数据
```

创建失败时，本项目执行：

```text
SQLite rollback
-> 按预生成 vector_id 删除可能写入的 Chroma 向量
```

这叫补偿操作：

```text
前一步无法通过同一事务回滚
就执行一个反向操作恢复一致状态
```

## 13. 删除问题为什么还要支持恢复向量

删除链路：

```text
删除问题向量
-> 删除 Mapping
-> 删除 Problem
-> commit
```

如果向量删除后数据库提交失败：

```text
数据库记录仍存在
但向量已经没有了
```

因此本项目会保存删除前的引用和映射信息，并尝试：

```text
重新计算问题 Embedding
-> upsert 原 vector_id
-> 恢复问题向量
```

补偿失败时，错误信息会同时保留：

```text
原始失败原因
向量补偿失败原因
```

不能让补偿错误覆盖真正的业务错误。

## 14. PostgreSQL + pgvector 为什么更简单

pgvector 模式中：

```text
Problem
Mapping
EmbeddingRef
真实 embedding
```

都在 PostgreSQL 中，并使用同一个 SQLAlchemy Session。

Repository 声明：

```python
transactional = True
```

这时失败只需要：

```python
db.rollback()
```

不需要额外删除或恢复外部向量。

因此 `transactional` 不是性能配置，而是在告诉业务层：

```text
这个向量后端能否和关系数据共享事务。
```

## 15. 问题从哪里来

当前学习版通过 API 显式传入问题：

```text
人工编写问题
-> 调用接口
-> 建立问题向量
```

真实系统常见来源：

```text
人工维护标准问
LLM 根据段落自动生成问题
历史用户问题聚类
搜索日志中高频未命中问题
领域专家标注
```

自动生成时仍应复用同一写入链路：

```text
只替换问题文本来源
不绕过去重、事务和向量补偿
```

## 16. 常见方案和生态

相近概念：

| 概念 | 作用 |
| --- | --- |
| Question Expansion | 为内容生成可能的问题 |
| Query Expansion | 扩展用户当前查询 |
| HyDE | 先生成假设答案，再用答案向量检索 |
| Multi Query | 把一个问题改写成多个查询 |
| FAQ Index | 直接维护标准问答对 |

区别：

```text
本项目的问题增强发生在入库阶段
Query Expansion 和 Multi Query 通常发生在查询阶段
```

入库阶段的好处：

```text
问题向量可复用
查询时延更稳定
```

代价：

```text
需要额外存储
内容更新时需要同步更新问题
```

## 17. 优点

```text
缩小用户表达和文档表达之间的差异
提高短问题、口语问题的召回概率
命中后仍回到原始段落，保留回答依据
source_type 让召回来源可观测
映射表允许后续扩展一个问题关联多个段落
```

## 18. 缺点与坑

### 18.1 生成的问题可能不准确

错误问题会把无关用户查询引向错误段落。

### 18.2 问题越多不一定越好

大量相似问题会增加索引体积和重复候选。

### 18.3 文档重新索引必须清理旧问题

旧 Paragraph 被替换后，关联问题和问题向量也必须同步删除。

### 18.4 不能只删除数据库记录

Chroma 模式还要删除真实向量，否则会产生悬空结果。

### 18.5 `source_type` 需要向后兼容

历史向量可能没有该字段。本项目缺失时按普通段落向量处理。

### 18.6 问题命中不是最终答案

无论问题向量多相似，都必须回到原始段落检查真实内容。

## 19. 推荐阅读代码顺序

```text
backend/app/models.py
-> backend/app/api/problem_api.py
-> backend/app/services/problem_service.py
-> backend/app/services/retrieval_service.py
-> backend/app/services/document_service.py
```

重点观察：

```text
Problem、Mapping、EmbeddingRef 如何关联
问题向量 metadata 保存了什么
检索如何从 problem_id 回到 paragraph_id
创建失败如何清理向量
删除失败如何恢复向量
文档删除和重新索引如何清理旧问题
```

## 20. 最小记忆模型

```text
Problem                    保存用户可能的提问方式
Paragraph                  保存真实知识和回答依据
ProblemParagraphMapping    保存问题与段落关系
source_type=PROBLEM        标识问题向量
problem_id                 从向量回到问题
paragraph_id               从问题映射回原始段落
问题向量                   用于召回
原始段落                   用于回答
补偿操作                   处理 SQLite 与 Chroma 跨存储一致性
transactional=True         表示 pgvector 可共享数据库事务
```

一句话总结：

```text
问题增强让系统更容易听懂用户怎么问，但最终回答仍必须回到原始段落。
```
