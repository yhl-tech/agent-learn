# 混合检索与 RRF 学习笔记

## 1. 一句话定义

```text
混合检索是同时使用语义向量和关键词召回候选，再把两路排名融合成最终结果。
```

本项目支持三种检索模式：

```text
embedding   只使用向量检索
keywords    只使用关键词全文检索
blend       同时使用两路检索，再用加权 RRF 融合
```

核心代码：

```text
backend/app/services/retrieval_service.py
backend/app/services/rerank_service.py
backend/app/repositories/paragraph_repository.py
backend/app/repositories/embedding_repository.py
```

## 2. 它解决什么问题

单独使用一种检索方式会有明显盲区。

向量检索擅长理解语义：

```text
用户问题：怎么退钱？
文档内容：退款将在三个工作日内到账。
```

即使字面不完全相同，向量仍可能判断它们语义接近。

但向量检索可能不擅长精确标识：

```text
订单号
错误码 E1007
API 名称
类名、字段名、产品型号
```

关键词检索正好相反。它擅长匹配明确词语，但不理解近义表达。

因此：

```text
向量检索     解决“意思相近”
关键词检索   解决“字面命中”
混合检索     同时利用两种信号
```

## 3. 和前端搜索的类比

可以把它类比成前端列表搜索。

普通字符串过滤：

```typescript
items.filter(item => item.name.includes(keyword))
```

它类似关键词检索，只能找到包含指定文本的记录。

语义检索更像：

```text
把查询和每条记录转换成特征向量
再按“含义有多接近”排序
```

混合检索则类似：

```text
一组结果来自文本精确匹配
另一组结果来自智能推荐
最后把两组结果合并排序
```

## 4. 不使用和使用混合检索的区别

只使用向量检索：

```python
query_embedding = embedding_service.embed_text(question)
results = vector_store.search(
    db=db,
    knowledge_id=knowledge_id,
    query_embedding=query_embedding,
    top_k=top_k,
)
```

使用混合检索：

```python
embedding_candidates = ...
keyword_candidates = ...

ranked_candidates = rerank_blended(
    embedding_candidates=embedding_candidates,
    keyword_candidates=keyword_candidates,
    top_k=top_k,
    score_threshold=score_threshold,
    embedding_weight=blend_weight,
)
```

关键变化不是“多查一次”，而是：

```text
先分别召回
-> 转换成统一候选结构
-> 按排名融合
-> 再回数据库加载业务对象
```

## 5. 本项目的完整检索链路

入口函数：

```python
retrieve_paragraphs(...)
```

完整流程：

```text
读取知识库检索配置
-> 根据 search_mode 选择召回通道
-> 向量通道生成问题向量并查询向量库
-> 关键词通道查询 FTS 全文索引
-> 转换成 RetrievalCandidate
-> 单路排序或加权 RRF 融合
-> 批量读取 Paragraph 和 Document
-> 返回 RetrievedParagraph
```

其中统一候选结构是：

```python
@dataclass(frozen=True)
class RetrievalCandidate:
    paragraph_id: str
    score: float
    match_type: str
    score_meta: dict
```

这样重排层只处理：

```text
段落 ID
分数
命中类型
调试信息
```

它不需要依赖完整 ORM 对象。

## 6. 三种检索模式

### 6.1 `embedding`

```text
问题
-> Embedding
-> 向量相似度检索
-> 段落候选
```

适合：

```text
自然语言问答
同义词和近义表达
用户问题与原文措辞不同
```

### 6.2 `keywords`

```text
问题文本
-> 全文检索表达式
-> BM25 / ts_rank_cd 排序
-> 段落候选
```

适合：

```text
错误码
专业术语
接口名
精确产品名称
```

### 6.3 `blend`

```text
               -> 向量召回 ----\
用户问题                         -> RRF -> 最终候选
               -> 关键词召回 --/
```

适合大多数通用 RAG 场景，因为它降低了单一检索信号失效的风险。

## 7. 关键词检索如何兼容 SQLite 和 PostgreSQL

统一入口：

```python
search_paragraphs_by_keywords(...)
```

Repository 根据数据库方言选择实现：

```python
if dialect == "sqlite":
    rows = _search_sqlite_fts(...)
elif dialect == "postgresql":
    rows = _search_postgresql_fts(...)
else:
    rows = _search_portable_like(...)
```

对应关系：

| 数据库 | 实现 | 排序方式 |
| --- | --- | --- |
| SQLite | FTS5 | `bm25(...)` |
| PostgreSQL | `tsvector` / `tsquery` | `ts_rank_cd(...)` |
| 其他数据库 | `LIKE` 保底 | 固定分数 |

业务层只依赖：

```text
list[KeywordSearchResult]
```

因此数据库差异被限制在 Repository 内。

## 8. 为什么不能直接使用用户输入拼接 FTS 查询

FTS 查询有自己的语法。

用户输入可能包含：

```text
引号
减号
括号
特殊操作符
```

如果直接拼接，可能改变查询含义或触发语法错误。

本项目先提取安全词项：

```python
terms = re.findall(r"[0-9A-Za-z_]+|[\u3400-\u9fff]+", query)
```

再转换成 phrase OR 查询：

```text
"退款" OR "到账"
```

这和 SQL 参数绑定解决的问题不同：

```text
SQL 参数绑定       防止输入改变 SQL 结构
FTS 查询转换       防止输入改变全文检索表达式结构
```

两层都需要处理。

## 9. BM25 分数为什么不能直接和向量分数相加

向量检索可能返回：

```text
0.91
0.84
0.77
```

SQLite FTS5 的 BM25 原始值可能是负数，PostgreSQL 的相关度又是另一套尺度。

因此下面的做法不可靠：

```python
final_score = vector_score + keyword_raw_score
```

问题在于：

```text
两种分数范围不同
分数方向可能不同
不同数据库的关键词分数也不同
```

本项目选择 RRF，因为它主要使用排名，而不是直接比较原始分数。

## 10. RRF 是什么

RRF 全称：

```text
Reciprocal Rank Fusion
```

核心思想：

```text
某条结果在每一路排得越靠前，贡献越大。
```

单路贡献：

```text
weight / (k + rank)
```

本项目：

```python
contribution = weight / (RRF_RANK_CONSTANT + rank)
```

假设：

```text
k = 60
向量权重 = 0.6
关键词权重 = 0.4
```

某段落在向量结果排第 1、关键词结果排第 3：

```text
0.6 / (60 + 1)
+ 0.4 / (60 + 3)
```

同一段落被两路同时命中时，会累加两次贡献。

## 11. `blend_weight` 控制什么

```text
embedding_weight = blend_weight
keyword_weight = 1 - blend_weight
```

例如：

```text
blend_weight = 0.7
```

表示：

```text
向量通道权重     0.7
关键词通道权重   0.3
```

它不是“70% 结果必须来自向量”，而是控制两路排名贡献的相对大小。

## 12. 为什么混合模式先多召回再截断

本项目先计算：

```python
candidate_limit = min(max(top_k * 3, top_k), 60)
```

如果最终只要 4 条：

```text
向量通道先取最多 12 条
关键词通道先取最多 12 条
融合后再保留 4 条
```

原因：

```text
如果每路一开始只取 4 条，融合层没有足够候选重新排序。
```

上限 60 用来限制查询量，避免 `top_k` 放大后无限增长。

## 13. 配置覆盖顺序

`resolve_retrieval_config` 合并三层配置：

```text
系统默认值
-> 知识库 retrieval_config
-> 单次请求参数
```

优先级：

```text
单次请求 > 知识库配置 > 系统默认值
```

单次覆盖不会写回数据库，适合检索测试接口临时调参。

主要配置：

```text
top_k             最终返回数量
score_threshold   最低分数阈值
search_mode       embedding / keywords / blend
blend_weight      混合模式中的向量权重
```

## 14. 为什么排序后还要回数据库

召回层只产生候选 ID 和分数。

回答需要的是可信业务数据：

```text
段落正文
文档名称
文档归属
知识库隔离
```

因此 `_load_retrieved_paragraphs` 会批量读取：

```text
ParagraphModel
DocumentModel
```

并再次检查 `knowledge_id`。

这形成两层隔离：

```text
向量或全文检索时按 knowledge_id 过滤
回源业务表时再次按 knowledge_id 校验
```

## 15. `score_meta` 有什么用

混合检索不仅要给出结果，还要能解释排序。

示例：

```json
{
  "algorithm": "weighted_rrf",
  "embedding_weight": 0.6,
  "keyword_weight": 0.4,
  "sources": {
    "embedding": {
      "rank": 1,
      "score": 0.91
    },
    "keywords": {
      "rank": 3,
      "score": 0.72
    }
  }
}
```

它适合：

```text
检索测试
问题排查
参数调优
解释某条结果为什么靠前
```

动态检索分数只随响应返回，不写回共享数据库记录，避免并发查询互相覆盖。

## 16. 常见方案和生态

常见检索组合：

| 方案 | 语义检索 | 关键词检索 | 融合方式 |
| --- | --- | --- | --- |
| 本项目本地模式 | Chroma | SQLite FTS5 | 加权 RRF |
| 本项目 PostgreSQL 模式 | pgvector | `tsvector` | 加权 RRF |
| Elasticsearch | dense vector | BM25 | RRF / 自定义打分 |
| OpenSearch | k-NN | BM25 | Hybrid Search |

更复杂的系统还可能增加：

```text
Cross Encoder reranker
LLM rerank
查询改写
多路召回
召回评估集
```

本项目当前的 `rerank_service.py` 是轻量排名融合，不是模型重排。

## 17. 优点

```text
兼顾语义和精确词匹配
降低单一检索方式的盲区
RRF 不依赖不同后端的原始分数量纲
统一入口让 Chat 和检索测试保持一致
score_meta 便于解释和调试
```

## 18. 缺点与坑

### 18.1 查询成本更高

混合模式会执行两路召回，数据库和向量库都要工作。

### 18.2 阈值不能脱离算法理解

`embedding` 分数和归一化后的 RRF 分数含义不同，不能机械复用同一阈值经验。

### 18.3 权重不是越偏向向量越好

包含大量错误码、产品名和 API 名的知识库，关键词通道通常更重要。

### 18.4 全文检索仍受分词影响

SQLite `unicode61`、PostgreSQL `simple` 都不是完整中文分词方案。

### 18.5 召回高不等于回答好

还要检查：

```text
切分是否合理
返回上下文是否过多
问题增强是否准确
LLM 是否正确使用引用
```

## 19. 推荐阅读代码顺序

```text
backend/app/services/retrieval_service.py
-> backend/app/repositories/paragraph_repository.py
-> backend/app/repositories/embedding_repository.py
-> backend/app/services/rerank_service.py
-> backend/app/api/chat_api.py
```

重点观察：

```text
配置如何合并
两路候选如何变成统一结构
RRF 如何计算
结果如何回到 Paragraph 和 Document
knowledge_id 如何做双重隔离
```

## 20. 最小记忆模型

```text
向量检索     找意思相近的内容
关键词检索   找字面命中的内容
混合检索     同时召回两路结果
RRF          按排名而不是原始分数融合
blend_weight 控制两路排名贡献
top_k        控制最终返回数量
candidate_limit 给重排保留更多候选
score_meta   解释结果为什么排在这里
回源数据库   把候选 ID 转成可信业务段落
```

一句话总结：

```text
混合检索不是把两种分数直接相加，而是先独立召回，再用统一排名规则融合。
```
