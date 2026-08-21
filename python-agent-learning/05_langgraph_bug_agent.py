"""
LangGraph 与状态机 Agent 技术导读

1. 这个技术是什么
   LangGraph 是 LangChain 生态中的状态机 / 工作流框架。
   它用 State、Node、Edge、Conditional Edge 描述一个多步骤 Agent 如何推进。

2. 它解决什么问题
   简单任务可以一次模型调用完成；复杂任务通常需要分析、检索、工具调用、观察结果、
   判断是否继续、总结输出。把这些逻辑写在一个大函数里会很难维护。
   LangGraph 让每一步成为清晰节点，并用边控制流程。

3. 工程中常见方案
   - 固定流程图：例如“接收输入 -> 检索 -> 生成 -> 总结”。
   - 条件分支图：信息不足先追问，信息足够再执行。
   - 循环 Agent：计划 -> 执行工具 -> 观察 -> 再计划，直到完成。
   - Human-in-the-loop：关键节点暂停，等待人工审批。
   - Checkpoint：保存中间状态，支持长任务恢复。

4. 当前业界实践效果
   LangGraph 适合构建可控 Agent，尤其适合排障、代码修复、数据分析、审批流、
   多工具任务编排等场景。相比“让模型自由发挥”，显式状态机更容易测试、追踪和干预。

5. 常见问题
   - State 设计混乱，字段含义不清晰。
   - 节点职责过大，一个节点做太多事。
   - 条件分支缺少兜底，流程进入错误路径。
   - 循环没有终止条件，导致无限执行。
   - 工具调用、模型调用、人工确认混在一起，难以测试。

6. 常见解决思路
   - 先定义清晰 State，再拆 Node。
   - 每个 Node 只做一件事，输入输出可测试。
   - Conditional Edge 返回值使用 Literal 限制合法节点名。
   - 给循环设置最大步数、超时和失败出口。
   - 用 trace 记录每个节点的输入、输出、耗时和错误。

7. 本文件做什么
   本文件实现一个最小 Bug 排障 Agent：
   先检查 Bug 描述是否足够，信息不足就追问；信息足够就分析、生成排查命令并总结。
"""

# argparse 用来解析命令行参数，这里用于接收用户传入的 Bug 描述。
import argparse
# os 用来读取环境变量，这里主要判断是否配置了 OPENAI_API_KEY。
import os
# typing 里的类型用于类型标注。
# TypedDict 用来定义字典形状；Literal 用来限制函数返回值只能是几个固定字符串。
from typing import List, Literal, Optional, TypedDict

# truststore 可以让 Python 使用系统证书链，解决 macOS / 公司网络下的 HTTPS 证书校验问题。
try:
    import truststore
except ImportError:
    truststore = None

# load_dotenv 会读取 .env 文件，把模型服务配置加载到环境变量。
from dotenv import load_dotenv
# ChatOpenAI 是 LangChain 对聊天模型的统一封装。
from langchain_openai import ChatOpenAI
# APIConnectionError 是 OpenAI SDK 的连接错误类型，网络、代理、证书问题通常会走到这里。
from openai import APIConnectionError
# StateGraph 是 LangGraph 的状态图；START / END 表示图的开始和结束。
from langgraph.graph import END, START, StateGraph


# 默认模型名。使用 DeepSeek 时，可以在 .env 中配置 OPENAI_MODEL=deepseek-chat 覆盖它。
DEFAULT_MODEL_NAME = "gpt-4o-mini"


# BugState 是整个 LangGraph 流程共享的状态结构。
# 每个节点都会读取 state，也可以返回一部分字段来更新 state。
class BugState(TypedDict, total=False):
    # State 是 LangGraph 贯穿全流程的状态对象。
    # bug_report: 用户输入的 Bug 描述。
    bug_report: str
    # question: 信息不足时，Agent 需要追问用户的问题。
    question: Optional[str]
    # analysis: 模型对 Bug 的分析结果。
    analysis: Optional[str]
    # commands: 建议用户执行的排查命令列表。
    commands: Optional[List[str]]
    # final_answer: 最终输出给用户的完整回答。
    final_answer: Optional[str]


def has_model_key() -> bool:
    # bool(...) 会把环境变量是否存在转成 True / False。
    return bool(os.getenv("OPENAI_API_KEY"))


def configure_ssl_trust_store() -> None:
    # macOS 或公司网络下，Python 自带证书链可能不信任模型服务证书。
    # truststore.inject_into_ssl() 会让 Python 复用系统证书链，通常比关闭 SSL 校验更安全。
    if truststore is not None:
        truststore.inject_into_ssl()


def create_chat_model() -> ChatOpenAI:
    # 创建模型客户端前先配置证书信任链，避免 DeepSeek 等 HTTPS 服务连接失败。
    configure_ssl_trust_store()

    # OPENAI_MODEL 是自定义环境变量，用来切换模型名。
    # 例如使用 DeepSeek 时，可以配置 OPENAI_MODEL=deepseek-chat。
    model_name = os.getenv("OPENAI_MODEL", DEFAULT_MODEL_NAME)
    # OPENAI_BASE_URL 用来配置兼容 OpenAI 协议的模型服务地址。
    # DeepSeek 的地址可以配置为 https://api.deepseek.com。
    base_url = os.getenv("OPENAI_BASE_URL")

    # 没有配置 base_url 时，走 ChatOpenAI 默认服务地址。
    if not base_url:
        return ChatOpenAI(model=model_name, temperature=0)

    # 配置了 base_url 时，LangChain 会把请求发到对应的兼容服务。
    return ChatOpenAI(model=model_name, temperature=0, base_url=base_url)


def ask_model(system_prompt: str, human_prompt: str) -> str:
    """调用模型；没有 Key 时返回本地兜底内容，保证图流程可练习。"""
    # 没有模型 Key 时，不直接报错，而是返回本地兜底文案。
    # 这样你即使暂时没有 Key，也可以先练 LangGraph 的状态流转。
    if not has_model_key():
        return "未配置 OPENAI_API_KEY，当前使用本地兜底分析。请配置 Key 后观察模型输出差异。"

    # temperature=0 表示尽量稳定输出，适合排障、总结、结构化任务。
    model = create_chat_model()
    try:
        # invoke 会真正调用模型。
        response = model.invoke(
            [
                # system_prompt 负责设定模型角色和规则。
                ("system", system_prompt),
                # human_prompt 是本次具体问题。
                ("human", human_prompt),
            ]
        )
    except APIConnectionError as error:
        # 模型连接失败时返回可读错误，避免一大段 traceback 干扰学习。
        return f"模型调用失败：连接模型服务时出现网络或证书问题。\n底层错误：{error}"
    # response.content 是模型返回内容，转成字符串后交给后续节点使用。
    return str(response.content)


def check_input(state: BugState) -> BugState:
    """检查输入是否足够进入分析。"""
    # 这个节点暂时不修改 state，只作为条件分支前的检查节点。
    return state


def route_after_check(state: BugState) -> Literal["ask_more", "analyze_bug"]:
    # strip() 去掉首尾空白，避免用户只输入空格。
    bug_report = state["bug_report"].strip()
    # 如果 Bug 描述太短，信息不足，先进入 ask_more 节点追问。
    if len(bug_report) < 20:
        return "ask_more"
    # 信息足够时，进入 analyze_bug 节点开始分析。
    return "analyze_bug"


def ask_more(state: BugState) -> BugState:
    # 节点返回的字典会被 LangGraph 合并进全局 state。
    return {
        "question": "请补充复现步骤、期望表现、实际表现、相关日志或截图。",
        "final_answer": "信息不足，先不要进入修复。请补充：复现步骤、期望表现、实际表现、相关日志或截图。",
    }


def analyze_bug(state: BugState) -> BugState:
    # 从 state 中读取 bug_report，交给模型分析。
    analysis = ask_model(
        "你是资深前端排障工程师。请用清晰、可验证的方式分析 Bug。",
        f"Bug 描述：{state['bug_report']}\n\n请输出可能原因和优先排查方向。",
    )
    # 只返回需要更新的字段即可，不需要返回完整 state。
    return {"analysis": analysis}


def propose_commands(state: BugState) -> BugState:
    # 根据 Bug 描述和上一步 analysis，生成建议排查命令。
    command_text = ask_model(
        "请给出用于验证 Bug 的命令，只输出命令列表。",
        f"Bug：{state['bug_report']}\n分析：{state.get('analysis')}",
    )

    # 没有模型 Key 或模型调用失败时，使用固定命令，保证这个节点仍然能演示完整流程。
    if not has_model_key() or command_text.startswith("模型调用失败："):
        commands = [
            "pytest -q",
            "python 04_rag_qa.py --no-model 'Tool Calling 失败怎么处理？'",
        ]
    else:
        # 模型返回通常是多行文本，这里按行拆分，整理成命令列表。
        commands = [
            line.strip("- ").strip()
            for line in command_text.splitlines()
            if line.strip()
        ]

    # 返回 commands，供 summarize 节点拼最终回答。
    return {"commands": commands}


def summarize(state: BugState) -> BugState:
    # state.get("commands") 可能是 None，所以用 or [] 兜底成空列表。
    commands = state.get("commands") or []
    # 把前面节点产生的 analysis 和 commands 拼成 Markdown 文本。
    final_answer = "\n".join(
        [
            "## Bug 分析",
            state.get("analysis") or "",
            "",
            "## 建议排查命令",
            *[f"- `{command}`" for command in commands],
            "",
            "## 下一步",
            "先执行排查命令，再根据真实结果决定是否修改代码。",
        ]
    )
    # final_answer 是这个图最终要输出的核心字段。
    return {"final_answer": final_answer}


def build_graph():
    # StateGraph(BugState) 表示创建一个以 BugState 为状态结构的 LangGraph。
    graph_builder = StateGraph(BugState)
    # add_node 用来注册节点。节点名是字符串，节点逻辑是 Python 函数。
    graph_builder.add_node("check_input", check_input)
    graph_builder.add_node("ask_more", ask_more)
    graph_builder.add_node("analyze_bug", analyze_bug)
    graph_builder.add_node("propose_commands", propose_commands)
    graph_builder.add_node("summarize", summarize)

    # add_edge 表示固定流转：从 START 进入 check_input。
    graph_builder.add_edge(START, "check_input")
    # add_conditional_edges 表示条件分支。
    # route_after_check 返回哪个节点名，流程就进入哪个节点。
    graph_builder.add_conditional_edges("check_input", route_after_check)
    # 信息不足时，ask_more 之后直接结束。
    graph_builder.add_edge("ask_more", END)
    # 信息足够时，按“分析 -> 建议命令 -> 总结”的顺序执行。
    graph_builder.add_edge("analyze_bug", "propose_commands")
    graph_builder.add_edge("propose_commands", "summarize")
    graph_builder.add_edge("summarize", END)

    # compile() 会把图编译成可执行对象，后续可以调用 graph.invoke(...)。
    return graph_builder.compile()


def main() -> None:
    # 读取 .env 中的模型服务配置。
    load_dotenv()

    # 定义命令行参数。用户可以直接在命令行传入 Bug 描述。
    parser = argparse.ArgumentParser(description="LangGraph Bug 排障 Agent 练习")
    parser.add_argument(
        "bug_report",
        # nargs="?" 表示这个参数可选；不传时使用 default。
        nargs="?",
        default="点击保存后按钮一直 loading，接口实际已经返回 200，但页面没有恢复可点击状态。",
        help="Bug 描述",
    )
    # parse_args 会把命令行输入解析成 args.bug_report。
    args = parser.parse_args()

    # 构建并编译 LangGraph。
    graph = build_graph()
    # invoke 会启动整张图。传入的是初始 state。
    result = graph.invoke(
        {
            "bug_report": args.bug_report,
            "question": None,
            "analysis": None,
            "commands": None,
            "final_answer": None,
        }
    )

    # 打印最终回答。短输入时来自 ask_more，长输入时来自 summarize。
    print(result["final_answer"])


# 直接运行 python 05_langgraph_bug_agent.py 时会执行 main()。
# 如果被其他文件 import 复用 build_graph()，则不会自动执行 main()。
if __name__ == "__main__":
    main()
