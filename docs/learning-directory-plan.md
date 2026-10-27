# 学习目录整理规划

## 目标

只解决当前最明显的问题：顶层目录混杂，学习文档和代码入口不好找。

不做过度整理，不重命名大量文件，不调整可运行代码结构。

## 推荐顶层结构

```text
agent/
├── README.md
├── docs/
├── python-agent-learning/
├── projects/
├── references/
└── .tools/
```

职责：

- `docs/`：放全局学习路线、目录规划和可跨项目复用的知识笔记。
- `python-agent-learning/`：Agent 开发学习入口，保留在顶层。
- `projects/`：放其他自己的学习项目和可运行项目。
- `references/`：放外部开源库、课程源码和参考资料。
- `.tools/`：本地工具目录，保持不动。

## 当前目录怎么放

```text
docs/
├── agent-development-learning-path.md
├── backend/
├── python-agent-development-learning-path.md
└── learning-directory-plan.md

python-agent-learning/

projects/
└── mini-maxkb-rag/

references/
├── langchain/
├── langgraph/
└── open-source-agent-learning/
```

## 项目内部分类

`python-agent-learning`：

```text
根目录：Agent 练习脚本、README、依赖配置
docs/：Agent 学习资料、学习计划、面试题、每日笔记
data/：脚本使用的知识库样例
tests/：测试
```

`projects/mini-maxkb-rag`：

```text
backend/：后端项目代码
docs/：只保留项目方案、项目规格等强绑定文档
agent.code-workspace：项目工作区配置
```

## 后续记录规则

Agent 相关知识点：

```text
python-agent-learning/docs/
```

后端相关知识点：

```text
docs/backend/
```

外部开源项目：

```text
references/
```

## 不做的事

- 不拆太多子目录。
- 不为了目录好看移动代码文件。
- 不改脚本运行方式。
- 不改测试路径。

## 当前顶层

```text
agent/
├── README.md
├── docs/
│   └── backend/
├── python-agent-learning/
├── projects/
├── references/
└── .tools/
```

说明：

- 如果顶层临时出现 `open-source-agent-learning/knowledge-base/MaxKB/.tools/tmp/worker_heartbeat_celery`，这是正在运行的 MaxKB / Celery 进程写入的心跳文件，不属于学习目录分类；停止相关进程后再移动即可。
