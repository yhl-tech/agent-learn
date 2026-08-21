"""
LLM 调用技术导读

1. 这个技术是什么
   LLM 调用是 Agent 开发的最小起点：程序把一组消息发给大语言模型，
   模型返回自然语言、结构化内容或工具调用请求。

2. 它解决什么问题
   它让应用具备“理解文本、生成文本、总结、解释、改写、推理”的能力。
   但单次 LLM 调用本身不等于 Agent，它只是 Agent 系统里的模型能力层。

3. 工程中常见方案
   - 直接调用模型 SDK，例如 OpenAI SDK、各云厂商 SDK。
   - 使用 LangChain 的 ChatOpenAI 等统一封装，方便后续接 Prompt、Tool、RAG。
   - 在服务端封装成 API，由前端通过 HTTP 或 SSE 调用。
   - 在生产环境中配合日志、限流、超时、重试和成本监控。

4. 当前业界实践效果
   对问答、总结、解释、文本生成类任务效果已经比较成熟。
   但模型输出不稳定，不能默认当作事实来源；涉及真实业务时，需要工具、检索、
   结构化输出和校验逻辑兜底。

5. 常见问题
   - Prompt 写得不清楚，输出格式不稳定。
   - temperature 过高，导致回答发散。
   - 上下文太长，成本高、延迟高。
   - 模型可能幻觉，编造不存在的信息。
   - 网络、证书、API Key、限流等工程问题会导致调用失败。

6. 常见解决思路
   - 用 system message 固定角色、边界和输出要求。
   - 学习阶段设置较低 temperature，先追求稳定。
   - 对需要程序消费的结果使用结构化输出。
   - 对事实性问题接入 RAG 或工具查询。
   - 对失败场景增加异常处理、重试和日志。

7. 本文件做什么
   本文件只演示最小 LLM 调用：读取 .env 配置，创建 ChatOpenAI，
   传入 system / human 消息，并打印模型回答。
"""

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


def main() -> None:
    # 读取 .env 中的 OPENAI_API_KEY / OPENAI_BASE_URL 等配置。
    load_dotenv()

    # ChatOpenAI 是 LangChain 对聊天模型的统一封装。
    # temperature 越低，回答越稳定；越高，回答越发散。
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
    )

    # invoke 接收一组消息。system 负责设定角色和规则，human 代表用户输入。
    response = model.invoke(
        [
            ("system", "你是一个严格、简洁的前端技术导师。"),
            ("human", "解释 React useMemo 的适用场景，并给出一个不应该使用 useMemo 的反例。"),
        ]
    )

    print(response.content)


if __name__ == "__main__":
    main()
