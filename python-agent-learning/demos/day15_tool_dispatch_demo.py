"""Day 15 Demo：理解 Tool Calling 的“请求”和“执行”边界。

模型返回 tool_call 只是一个调用请求：

    {"name": "read_project_readme", "args": {"path": "README.md"}}

真正执行 Python 函数、校验工具名、处理错误的仍然是程序。

运行：

    .venv/bin/python demos/day15_tool_dispatch_demo.py
"""

from typing import Any, Callable, Dict


def read_project_readme(path: str) -> Dict[str, Any]:
    """一个只读工具的示例。"""
    # 工具不能因为模型传入了路径就无条件访问文件。
    # 这里用白名单演示最小权限边界。
    if path != "README.md":
        return {
            "success": False,
            "error_code": "PATH_NOT_ALLOWED",
            "error_message": "示例工具只允许读取 README.md",
        }

    return {
        "success": True,
        "data": {
            "summary": "这是 Python Agent Learning 项目说明文件。",
        },
    }


# 工具注册表把可调用的能力限制在明确的白名单里。
# 模型只能请求这里注册过的工具，不能随意拼接任意 Python 函数名。
TOOL_REGISTRY: Dict[str, Callable[..., Dict[str, Any]]] = {
    "read_project_readme": read_project_readme,
}


def dispatch_tool_call(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """校验并执行一次工具调用请求。"""
    # get() 避免模型返回缺少字段时直接触发 KeyError。
    tool_name = tool_call.get("name")
    args = tool_call.get("args", {})

    # 未注册工具直接拒绝，返回结构化错误。
    tool = TOOL_REGISTRY.get(tool_name)
    if tool is None:
        return {
            "success": False,
            "error_code": "UNKNOWN_TOOL",
            "error_message": f"未注册的工具：{tool_name}",
        }

    try:
        # 只有这里才是真正执行 Python 函数的地方。
        result = tool(**args)
    except TypeError as error:
        # 参数名缺失、参数类型不匹配时，返回可恢复错误。
        return {
            "success": False,
            "error_code": "INVALID_ARGS",
            "error_message": f"工具参数错误：{error}",
        }
    except Exception as error:
        # 真实项目还应记录 trace_id、耗时、用户和权限上下文。
        return {
            "success": False,
            "error_code": "TOOL_EXECUTION_FAILED",
            "error_message": f"工具执行失败：{type(error).__name__}: {error}",
        }

    return result


def main() -> None:
    examples = [
        {
            "name": "read_project_readme",
            "args": {"path": "README.md"},
        },
        {
            "name": "unknown_tool",
            "args": {},
        },
        {
            "name": "read_project_readme",
            "args": {"path": "secrets.env"},
        },
    ]

    for example in examples:
        print(dispatch_tool_call(example))


if __name__ == "__main__":
    main()
