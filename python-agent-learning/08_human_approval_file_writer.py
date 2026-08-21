"""
Human-in-the-loop 与危险操作安全边界技术导读

1. 这个技术是什么
   Human-in-the-loop 指 Agent 在关键步骤暂停，等待人工确认后再继续执行。
   它常用于写文件、删文件、执行命令、提交代码、调用生产接口等有副作用的操作。

2. 它解决什么问题
   模型可能误解用户意图、生成错误参数或执行高风险动作。
   如果 Agent 完全自动执行危险工具，可能造成数据丢失、代码污染、生产事故或权限泄露。

3. 工程中常见方案
   - 先生成计划，再让用户确认。
   - 写文件前展示路径、原因和内容预览。
   - 修改代码前展示 diff。
   - 执行命令前展示命令和风险等级。
   - 对危险工具做白名单、目录限制、权限校验和审计日志。
   - 在 LangGraph 中使用 interrupt / waiting_approval 节点等待审批。

4. 当前业界实践效果
   对代码 Agent、运维 Agent、数据 Agent 来说，人机确认是非常关键的安全机制。
   成熟系统通常不会让模型直接拥有无限权限，而是把能力拆成受控工具，并在高风险动作前
   要求用户审批。

5. 常见问题
   - 模型生成 ../ 之类路径，试图写到允许目录之外。
   - 用户没有看到完整 diff 就确认，风险不可控。
   - 所有操作都要求确认，体验太差。
   - 没有审计日志，事后无法追踪是谁批准了什么。
   - 只在 UI 上限制，后端工具本身没有权限边界。

6. 常见解决思路
   - 按风险分级：只读工具可自动执行，高风险工具必须确认。
   - 工具层做硬限制，例如只允许写入指定目录。
   - 对路径使用 resolve() 做规范化，防止路径穿越。
   - 展示计划、参数、diff、影响范围，再等待 yes / approve。
   - 保存审批记录、执行结果和失败原因。

7. 本文件做什么
   本文件定义 create_file_draft 工具，它只生成写文件草稿。
   真正写入磁盘前，会展示路径、原因、内容预览，并要求用户输入 yes。
   同时限制文件只能写入 generated 目录。
"""

# json 用来把文件草稿转成 JSON 字符串，方便工具返回结构化结果。
import json
# os 用来读取环境变量，这里主要判断是否配置了 OPENAI_API_KEY。
import os
# pathlib.Path 用面向对象的方式处理文件路径。
from pathlib import Path
# Any / Dict 是类型标注，表示 tool_call 是一个字典结构。
from typing import Any, Dict

# load_dotenv 会读取 .env 文件，把模型服务配置加载到环境变量。
from dotenv import load_dotenv
# @tool 用来把普通 Python 函数包装成 LangChain 工具。
from langchain_core.tools import tool
# ChatOpenAI 是 LangChain 对聊天模型的统一封装。
from langchain_openai import ChatOpenAI
# BaseModel / Field 用来定义工具入参 schema，并提供字段说明。
from pydantic import BaseModel, Field


# 当前脚本所在目录。
PROJECT_ROOT = Path(__file__).parent
# 只允许写入 generated 目录，避免模型生成危险路径改到项目其他文件。
OUTPUT_ROOT = PROJECT_ROOT / "generated"


class FileDraftInput(BaseModel):
    # relative_path 是相对路径，不允许模型直接给绝对路径。
    relative_path: str = Field(description="要写入的相对路径，只允许写入 generated 目录")
    # content 是准备写入文件的内容。
    content: str = Field(description="文件内容")
    # reason 说明为什么要写这个文件，用于人工确认时展示。
    reason: str = Field(description="为什么需要写这个文件")


# 把 create_file_draft 包装成 LangChain 工具。
# 这个工具只生成“写文件草稿”，不直接写磁盘。
@tool(args_schema=FileDraftInput)
def create_file_draft(relative_path: str, content: str, reason: str) -> str:
    """生成文件写入草稿，但不直接写入磁盘。"""
    # 工具返回 JSON 字符串，后续可以再解析回 FileDraftInput。
    return json.dumps(
        {
            "relative_path": relative_path,
            "content": content,
            "reason": reason,
        },
        # ensure_ascii=False 可以让中文正常显示，而不是转成 Unicode 转义。
        ensure_ascii=False,
        # indent=2 让 JSON 更容易阅读。
        indent=2,
    )


def run_tool_call(tool_call: Dict[str, Any]) -> str:
    # 先校验工具名，避免执行未知工具。
    if tool_call["name"] != "create_file_draft":
        return f"未识别的工具：{tool_call['name']}"

    try:
        # invoke 会真正执行 LangChain 工具；tool_call["args"] 是模型生成的参数。
        return create_file_draft.invoke(tool_call["args"])
    except Exception as error:
        # 工具执行失败时返回错误类型和信息，方便排查。
        return f"工具 create_file_draft 执行失败：{type(error).__name__}: {error}"


def parse_draft(raw_result: str) -> FileDraftInput:
    # model_validate_json 会把 JSON 字符串校验并转换成 FileDraftInput 对象。
    return FileDraftInput.model_validate_json(raw_result)


def resolve_safe_output_path(relative_path: str) -> Path:
    # resolve() 会把路径转成规范化绝对路径，处理 ..、软链等情况。
    output_root = OUTPUT_ROOT.resolve()
    target_path = (output_root / relative_path).resolve()

    # 写工具必须限制目录范围，避免模型生成 ../../../ 之类的危险路径。
    # target_path 必须等于 output_root，或者位于 output_root 子目录内。
    if target_path != output_root and output_root not in target_path.parents:
        raise ValueError("写入路径越界，只允许写入 generated 目录")

    return target_path


def write_after_approval(draft: FileDraftInput) -> None:
    # 写入前先做路径安全检查。
    target_path = resolve_safe_output_path(draft.relative_path)

    # 展示即将执行的写入计划，让用户决定是否确认。
    print("\n即将写入文件：")
    print(f"路径：{target_path}")
    print(f"原因：{draft.reason}")
    print("内容预览：")
    print(draft.content)

    # 只有用户明确输入 yes，才真正写入磁盘。
    approval = input("\n确认写入请输入 yes：").strip().lower()
    if approval != "yes":
        print("已取消写入。")
        return

    # mkdir(parents=True, exist_ok=True) 会确保父目录存在。
    target_path.parent.mkdir(parents=True, exist_ok=True)
    # write_text 才是真正写文件的动作。
    target_path.write_text(draft.content, encoding="utf-8")
    print(f"写入完成：{target_path}")


def build_fallback_draft() -> str:
    # 没有模型 Key 时，用固定参数直接调用工具，保证仍然可以练习人工确认流程。
    return create_file_draft.invoke(
        {
            "relative_path": "hello_agent.txt",
            "content": "这是一个经过人工确认后写入的 Agent 练习文件。\n",
            "reason": "未配置 OPENAI_API_KEY 时，使用本地草稿演示人工确认流程。",
        }
    )


def main() -> None:
    # 读取 .env 中的模型服务配置。
    load_dotenv()

    # 没有 OPENAI_API_KEY 时，不调用模型，走本地兜底草稿。
    if not os.getenv("OPENAI_API_KEY"):
        raw_result = build_fallback_draft()
        draft = parse_draft(raw_result)
        write_after_approval(draft)
        return

    # 有模型 Key 时，让模型决定是否调用 create_file_draft 工具以及生成什么参数。
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # bind_tools 把 create_file_draft 暴露给模型。
    model_with_tools = model.bind_tools([create_file_draft])
    # 这一步只会得到模型回复和工具调用请求，不会自动写文件。
    response = model_with_tools.invoke(
        [
            ("system", "你是文件生成助手。需要写文件时必须先调用 create_file_draft 生成草稿。"),
            ("human", "生成一个 hello_agent.txt，内容说明我正在学习 Agent 人工确认流程。"),
        ]
    )

    # 遍历模型提出的工具调用请求。
    for tool_call in response.tool_calls:
        # 先执行工具，生成文件草稿。
        raw_result = run_tool_call(tool_call)
        try:
            # 把工具返回的 JSON 字符串解析成 FileDraftInput。
            draft = parse_draft(raw_result)
        except Exception as error:
            # 如果工具返回不是合法草稿，不继续执行写文件。
            print(f"文件草稿解析失败：{type(error).__name__}: {error}")
            print(raw_result)
            continue

        # 最后进入人工确认，确认后才真正写入磁盘。
        write_after_approval(draft)


# 直接运行 python 08_human_approval_file_writer.py 时会执行 main()。
# 如果被测试文件 import，只会复用函数，不会自动执行 main()。
if __name__ == "__main__":
    main()
