# 中文 Agent 开发课程与学习资料

## 推荐学习顺序

1. 先用 Hugging Face Agents Course 建立 Agent 核心概念，并跟着做少量实战。
2. 再用 LangChain Academy 的 LangGraph 课程补状态、节点、边、Memory 等工程概念。
3. 回头泛读 `hello-agents`，只抓 ReAct、Planning、Tool、Memory、MCP 这些关键词。
4. 用 `learn-claude-code` 学 Agent Harness 的工程骨架。
5. 补 `MCP-Chinese-Getting-Started-Guide`，理解工具协议和 MCP Server/Client。
6. 用 `ai-agents-from-zero` 跑 LangChain/LangGraph 项目实战。
7. 最后按需查 `Agent-Learning-Hub`、`AgentGuide` 和其他资料库。

如果只想看中文：

1. 先看 `hello-agents` 在线教程和视频课导航，跳过太长的历史背景。
2. 再看 Datawhale 的 Deep Agents 实战，重点学 LangChain/LangGraph 生态里的 Agent Harness。
3. 想偏产品落地，就看 Dify、扣子 Coze、魔搭 Agent 大本营。
4. 想看非程序员视角的智能体设计，可以补中山大学岭南学院《经济金融智能体设计》。

## 核心课程

### 1. datawhalechina/hello-agents

- 地址：https://github.com/datawhalechina/hello-agents
- 在线阅读：https://hello-agents.datawhale.cc/
- 视频课导航：https://github.com/datawhalechina/hello-agents/blob/main/Extra-Chapter/Extra13-Hello-Agents%E8%A7%86%E9%A2%91%E8%AF%BE%E5%BD%95%E5%88%B6%E5%85%B1%E5%88%9B.md
- B 站入口：https://www.bilibili.com/video/BV1uj7W6hESS/
- 定位：《从零开始构建智能体》，系统性中文 Agent 教程。
- 重点内容：Agent 概念、ReAct、Plan-and-Solve、Reflection、LangGraph、AutoGen、RAG、Memory、MCP、A2A、评估、DeepResearch、多 Agent 实战。
- 适合阶段：最适合作为主线课程。

### 2. shareAI-lab/learn-claude-code

- 地址：https://github.com/shareAI-lab/learn-claude-code
- 定位：从 0 搭建 Claude Code 风格的 Agent Harness。
- 重点内容：agent loop、tool use、权限、hooks、子 Agent、Skill、上下文压缩、任务系统、MCP、目标闭环。
- 适合阶段：适合工程向深入，理解真实 Agent 产品骨架。

### 3. datawhalechina/Agent-Learning-Hub

- 地址：https://github.com/datawhalechina/Agent-Learning-Hub
- 定位：中文 Agent 学习路线和资料库。
- 重点内容：Agent loop、工具调用、RAG、Memory、Harness、评测、安全、项目阶梯。
- 适合阶段：适合作为学习地图和资料索引。

### 4. didilili/ai-agents-from-zero

- 地址：https://github.com/didilili/ai-agents-from-zero
- 定位：Python + LangChain/LangGraph 方向的实战教程。
- 重点内容：Coze、Dify、MCP、RAG、企业级项目、NL2SQL、电商问数、深度研搜。
- 适合阶段：适合跑完整项目，积累可展示作品。

### 5. adongwanai/AgentGuide

- 地址：https://github.com/adongwanai/AgentGuide
- 定位：Agent 开发、求职和面试导向的中文知识库。
- 重点内容：LangGraph、高级 RAG、Harness、Eval、Agentic RL、项目和面试题。
- 适合阶段：适合系统补齐知识点和准备岗位表达。

### 6. shareAI-lab/claw0

- 地址：https://github.com/shareAI-lab/claw0
- 定位：从 0 到 1 构建 AI Agent Gateway。
- 重点内容：session、channel、gateway routing、memory、heartbeat、delivery、resilience、concurrency。
- 适合阶段：适合学习生产级 Agent 网关和长期运行机制。

### 7. liaokongVFX/MCP-Chinese-Getting-Started-Guide

- 地址：https://github.com/liaokongVFX/MCP-Chinese-Getting-Started-Guide
- 定位：MCP 中文极速入门。
- 重点内容：MCP Server、MCP Client、stdio、tool 注册、Inspector 调试。
- 适合阶段：适合快速理解 MCP 工具协议。

## 免费公开课程与网站

### 1. Hugging Face Agents Course

- 地址：https://huggingface.co/learn/agents-course/unit0/introduction
- 定位：免费 Agent 系统课程，从概念到实战。
- 重点内容：Agent 基础、Tools、Thought/Action/Observation、smolagents、LlamaIndex、LangGraph、Agentic RAG、评估挑战。
- 适合阶段：最适合替代长篇理论阅读，直接作为第一门主线课程。
- 注意点：英文为主，但结构清晰，适合配合翻译工具学习。

### 2. LangChain Academy

- 地址：https://academy.langchain.com/
- 定位：LangChain 官方免费课程站，围绕 Agent 开发生命周期组织。
- 重点内容：LangGraph、Deep Agents、LangSmith、测试、部署、监控。
- 适合阶段：适合在理解 Agent 基本循环后，学习可控工作流和工程化实践。
- 推荐入口：
  - Introduction to LangGraph - Python：https://academy.langchain.com/courses/intro-to-langgraph
  - Quickstart: LangGraph Essentials - Python：https://academy.langchain.com/courses/langgraph-essentials-python
  - Project: Deep Research with LangGraph：https://academy.langchain.com/courses/deep-research-with-langgraph/

### 3. DeepLearning.AI Short Courses

- 地址：https://www.deeplearning.ai/short-courses/
- 定位：短课集合，适合按主题补单点能力。
- 重点内容：LangGraph、crewAI、LlamaIndex、Agentic RAG、多 Agent。
- 适合阶段：适合选修，不建议一口气刷完。
- 推荐课程：
  - AI Agents in LangGraph：https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/
  - Multi AI Agent Systems with crewAI：https://www.deeplearning.ai/short-courses/multi-ai-agent-systems-with-crewai/
  - Building Agentic RAG with LlamaIndex：https://www.deeplearning.ai/short-courses/building-agentic-rag-with-llamaindex/
- 注意点：课程访问当前标注为 beta 期间免费，证书/作业能力可能需要 PRO。

### 4. Microsoft Learn - Develop AI agents on Azure

- 地址：https://learn.microsoft.com/en-us/training/paths/develop-ai-agents-azure/
- 定位：微软官方 Agent 学习路径。
- 重点内容：Microsoft Foundry Agent Service、自定义工具、MCP Tools、RAG、多 Agent 编排、A2A。
- 适合阶段：适合了解企业级 Agent 服务形态，不适合作为第一门课。

### 5. Dify 官方文档与教程

- 地址：https://docs.dify.ai/
- B 站检索：https://search.bilibili.com/all?keyword=Dify%20Agent%20%E6%95%99%E7%A8%8B
- 定位：可视化 Agentic Workflow 平台文档。
- 重点内容：工作流、工具、知识库、应用发布、典型场景教程。
- 适合阶段：适合理解低代码 Agent/Workflow 产品如何组织能力。

### 6. 扣子 Coze 官方文档

- 地址：https://docs.coze.cn/
- B 站检索：https://search.bilibili.com/all?keyword=Coze%20%E6%89%A3%E5%AD%90%20%E6%99%BA%E8%83%BD%E4%BD%93%20%E6%95%99%E7%A8%8B
- 定位：低代码智能体与工作流平台文档。
- 重点内容：单 Agent、多 Agent、插件、工作流、知识库、发布。
- 适合阶段：适合学习产品化 Agent 的编排概念和交互形态。

### 7. 魔搭 ModelScope Agent 大本营

- 地址：https://www.modelscope.cn/brand/view/agent
- 定位：ModelScope 的 Agent 教程与实操合集。
- 重点内容：零代码创建 Agent、工具调用、Code Interpreter、Agent 应用发布。
- 适合阶段：适合快速体验中文生态里的 Agent 应用搭建。

## 中文视频课程与国内公开教学

### 1. Datawhale - Hello-Agents 视频课

- 地址：https://github.com/datawhalechina/hello-agents/blob/main/Extra-Chapter/Extra13-Hello-Agents%E8%A7%86%E9%A2%91%E8%AF%BE%E5%BD%95%E5%88%B6%E5%85%B1%E5%88%9B.md
- B 站入口：https://www.bilibili.com/video/BV1uj7W6hESS/
- 定位：`hello-agents` 的配套视频课程和共创导航。
- 重点内容：ReAct、Plan-and-Solve、Reflection、Coze、LangGraph、Memory、上下文工程、DeepResearch。
- 适合阶段：适合替代直接啃长文档，先用视频建立概念。

### 2. Datawhale - Deep Agents 实战

- 地址：https://datawhalechina.github.io/deepagents-in-action/
- B 站合集：https://space.bilibili.com/28357052/lists/7757577?type=season
- 定位：基于 LangChain / LangGraph 生态的生产级 Agent Harness 实战课程。
- 重点内容：Agent Harness、Context Engineering、虚拟文件系统、任务规划、子 Agent、Skills、长期记忆、Human-in-the-Loop、沙箱、MCP、Streaming。
- 适合阶段：适合在理解 Agent 基本循环后，学习更接近真实工程的 Agent 结构。
- 注意点：比 `hello-agents` 更偏工程进阶，不建议作为第一门课。

### 3. 中山大学岭南学院 - 经济金融智能体设计

- 地址：https://ai.lingnan.top/
- 定位：高校公开课程，面向经济金融场景的智能体设计。
- 重点内容：智能体设计、工作流编排、Skills、子代理、评估迭代、办公/金融/科研场景智能体。
- 适合阶段：适合学习“怎么把 Agent 用到真实业务问题里”，不强调编程。
- 注意点：偏方法论和场景设计，不是代码实战主线。

### 4. 阿里云 - AI 编码项目实战工坊

- 地址：https://edu.aliyun.com/trainingcamp/3522804
- 定位：阿里云公开训练营，偏 AI 编码和智能体实验。
- 重点内容：通义灵码、Prompt、百炼智能体、工作流、Assistant API、Multi Agent、MCP 多智能体平台。
- 适合阶段：适合了解国内云厂商的 Agent 开发与平台化实践。

### 5. B 站资料筛选建议

- 推荐优先看：Datawhale、官方文档配套视频、框架作者/官方大使、带课程主页和代码仓库的合集。
- 谨慎看：标题里强调“几天就业”“全网最全”“几百集”“少走 99% 弯路”的搬运合集。
- 推荐检索词：
  - `Hello Agents Datawhale`
  - `Deep Agents 实战`
  - `LangGraph 智能体 实战`
  - `Dify Agent 工作流`
  - `Coze 扣子 智能体 工作流`

## 补充资料

### datawhalechina/llm-cookbook

- 地址：https://github.com/datawhalechina/llm-cookbook
- 用途：补 LLM 基础、Prompt、LangChain、Tools/Agents 入门。

### chatchat-space/Langchain-Chatchat

- 地址：https://github.com/chatchat-space/Langchain-Chatchat
- 用途：参考中文 RAG、本地知识库问答和应用工程结构。

### yzfly/Awesome-MCP-ZH

- 地址：https://github.com/yzfly/Awesome-MCP-ZH
- 用途：查 MCP 客户端、Server 和生态资源。

### liguodongiot/llm-action

- 地址：https://github.com/liguodongiot/llm-action
- 用途：补大模型工程化、推理、训练、评测等背景知识。

### liyupi/ai-guide

- 地址：https://github.com/liyupi/ai-guide
- 用途：泛读 AI 编程、Vibe Coding、Agent 工具和实践经验。
