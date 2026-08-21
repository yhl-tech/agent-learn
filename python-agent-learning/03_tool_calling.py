"""
Tool Calling 技术导读

1. 这个技术是什么
   Tool Calling 是让模型根据用户目标，生成“要调用哪个工具、传什么参数”的请求。
   模型本身不会直接执行本地代码，真正执行工具的是 Python 程序。

2. 它解决什么问题
   普通 Chatbot 只能回答文本；Agent 需要读文件、查数据库、调用 API、运行测试、
   生成计划或等待人工确认。Tool Calling 就是模型连接外部能力的工程接口。

3. 工程中常见方案
   - 用 @tool 定义 LangChain 工具。
   - 用 Pydantic / JSON Schema 定义工具参数结构。
   - 让模型返回 tool_calls，再由程序统一调度执行。
   - 对只读工具、写操作工具、危险工具做权限分级。
   - 对工具执行记录 trace，包括工具名、参数、结果、耗时和错误。

4. 当前业界实践效果
   在搜索、代码库问答、数据查询、工单处理、文件计划生成等场景非常常见。
   但模型可能选错工具、传错参数，工具也可能超时、失败或产生副作用。

5. 常见问题
   - 工具 schema 不清楚，模型生成参数不稳定。
   - 工具返回太长，模型无法有效理解。
   - 写文件、删文件、执行命令等危险操作缺少人工确认。
   - 工具失败后程序直接崩溃，没有错误兜底。
   - 模型把“工具调用计划”误当成“工具已经执行成功”。

6. 常见解决思路
   - 用严格 schema 限制工具参数。
   - 工具描述写清楚用途、边界和返回格式。
   - 工具执行层加 try/except、超时、重试和日志。
   - 写操作前展示计划或 diff，等待人工确认。
   - 工具返回尽量结构化，方便后续节点或模型消费。

7. 本文件做什么
   本文件定义 create_file_plan 工具，让模型根据页面需求生成文件计划。
   它只生成计划，不真正写文件，用来练习 tool_calls 和 invoke 的关系。
"""

# typing 里的类型用于“类型标注”，帮助 IDE、Pydantic 和读代码的人理解数据结构。
# Any 表示任意类型；Dict 表示字典；List 表示列表。
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


# class 用来定义一个类。这里的 FileItem 是一个“文件计划项”的数据结构。
# 继承 BaseModel 后，Pydantic 会自动帮我们做字段校验和类型转换。
class FileItem(BaseModel):
    # 单个文件计划项。这个 schema 会被工具参数复用。
    # path: str 表示 path 字段必须是字符串。
    path: str = Field(description="文件路径")
    # Field(description=...) 是字段说明，会提供给大模型理解字段含义。
    purpose: str = Field(description="文件用途")


# FilePlanInput 是工具 create_file_plan 的入参结构。
# 也就是说，大模型调用工具时，参数必须符合这个类定义的格式。
class FilePlanInput(BaseModel):
    # 工具入参 schema。模型调用工具时，参数必须符合这个结构。
    page_name: str = Field(description="页面名称")
    # List[FileItem] 表示 files 是一个列表，列表里的每一项都应该是 FileItem。
    files: List[FileItem] = Field(description="需要创建或修改的文件")


# def 用来定义函数。
# item: Any 表示参数 item 可以是任意类型。
# -> FileItem 表示这个函数的返回值应该是 FileItem。
def normalize_file_item(item: Any) -> FileItem:
    # LangChain 工具调用时，嵌套对象可能已经是 FileItem，也可能是 dict。
    # 这里统一转换成 FileItem，降低不同返回形态带来的干扰。
    # isinstance(item, FileItem) 用来判断 item 是否已经是 FileItem 类型。
    if isinstance(item, FileItem):
        return item
    # model_validate 会把 dict 等数据校验并转换成 FileItem。
    return FileItem.model_validate(item)


# @tool 是 Python 装饰器语法。
# 这里表示把 create_file_plan 这个普通 Python 函数包装成 LangChain 工具。
@tool(args_schema=FilePlanInput)
def create_file_plan(page_name: str, files: List[Any]) -> str:
    """根据页面需求生成前端文件计划，但不直接写文件。"""
    # 工具函数是真实执行逻辑。模型只负责决定是否调用以及生成参数。
    # 这是列表推导式，等价于：
    # normalized_files = []
    # for item in files:
    #     normalized_files.append(normalize_file_item(item))
    normalized_files = [normalize_file_item(item) for item in files]

    # f"页面：{page_name}" 是 f-string，可以把变量 page_name 插入字符串。
    lines = [f"页面：{page_name}", "文件计划："]
    # for 循环会逐个取出 normalized_files 里的 FileItem。
    for item in normalized_files:
        # 因为前面已经统一转换成 FileItem，这里可以稳定使用 item.path / item.purpose。
        lines.append(f"- {item.path}: {item.purpose}")

    # "\n".join(lines) 会用换行符把字符串列表拼成一段文本。
    return "\n".join(lines)


def run_tool_call(tool_call: Dict[str, Any]) -> str:
    # response.tool_calls 只是模型提出的工具调用请求；这里才是真正执行工具。
    # tool_call["name"] 是从字典里读取 name 字段。
    if tool_call["name"] != "create_file_plan":
        return f"未识别的工具：{tool_call['name']}"

    try:
        # invoke 会执行 LangChain 工具；tool_call["args"] 是模型生成的工具参数。
        return create_file_plan.invoke(tool_call["args"])
    except Exception as error:
        # 工具执行失败时不要让整个程序崩掉，先把错误类型和信息返回出来，方便排查。
        return f"工具 create_file_plan 执行失败：{type(error).__name__}: {error}"


def main() -> None:
    # 读取 .env 中的模型服务配置。
    load_dotenv()

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # bind_tools 把 Python 函数暴露给模型，模型会基于工具描述和 schema 决定是否调用。
    model_with_tools = model.bind_tools([create_file_plan])

    # 这一步只会得到模型回复和工具调用请求，不会自动执行本地函数。
    response = model_with_tools.invoke(
        [
            ("system", "你是前端工程助手。需要生成文件计划时必须调用工具。"),
            ("human", "我要做一个订单列表页，支持搜索、分页、导出。"),
        ]
    )

    print("模型返回的工具调用：")
    print(response.tool_calls)

    print("\n工具执行结果：")
    for tool_call in response.tool_calls:
        # 遍历模型返回的 tool_calls，逐个执行对应工具。
        print(run_tool_call(tool_call))


# 这是一种 Python 常见入口写法。
# 当你直接运行 python 03_tool_calling.py 时，__name__ 会等于 "__main__"，main() 会执行。
# 如果这个文件被其他 Python 文件 import，main() 不会自动执行。
if __name__ == "__main__":
    main()
