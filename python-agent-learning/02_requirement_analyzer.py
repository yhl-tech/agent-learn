"""
结构化输出技术导读

1. 这个技术是什么
   结构化输出是让模型按照预先定义的字段和类型返回结果，例如 JSON 或 Pydantic 对象。
   它的目标不是让模型“说得好听”，而是让模型输出能被程序稳定消费。

2. 它解决什么问题
   真实业务里，模型输出通常要继续进入前端页面、数据库、流程引擎或下游工具。
   如果只返回自然语言，程序很难可靠解析；结构化输出可以把模型结果约束成明确字段。

3. 工程中常见方案
   - Pydantic：Python 中常用的数据模型和校验工具。
   - JSON Schema：跨语言通用的结构描述方式。
   - Zod：TypeScript 项目中常用的 schema 工具。
   - LangChain with_structured_output：把 schema 交给模型，要求模型按结构返回。
   - Output Parser + Retry：解析失败时自动重试或提示模型修正格式。

4. 当前业界实践效果
   对需求拆解、信息抽取、分类、表单填充、接口参数生成等场景很实用。
   但模型仍可能漏字段、填错类型或输出不符合业务约束，所以不能只依赖模型自觉。

5. 常见问题
   - 字段描述太模糊，模型不知道该填什么。
   - schema 太复杂，一次输出过多字段，稳定性下降。
   - 模型输出格式看似正确，但业务语义不一定正确。
   - 解析失败后没有重试或错误提示。

6. 常见解决思路
   - 字段命名语义化，Field(description=...) 写清楚含义。
   - 先从少量关键字段开始，再逐步扩展。
   - 对关键字段做二次业务校验。
   - 保存失败样例，加入 Eval 或单测。
   - 对解析失败加重试、兜底提示和日志。

7. 本文件做什么
   本文件用 Pydantic 定义 RequirementAnalysis，
   让模型把一段页面需求拆成前端可执行的结构化信息。
"""

from typing import List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class RequirementAnalysis(BaseModel):
    # Pydantic schema 会约束模型输出结构，让结果可以被程序稳定消费。
    # Field(description=...) 会作为字段说明传给模型，帮助模型理解每个字段应该填什么。
    page_goal: str = Field(description="页面目标")
    user_roles: List[str] = Field(description="用户角色")
    core_interactions: List[str] = Field(description="核心交互")
    api_dependencies: List[str] = Field(description="可能依赖的 API")
    component_plan: List[str] = Field(description="建议拆分的前端组件")
    state_design: List[str] = Field(description="前端状态设计建议")
    risk_points: List[str] = Field(description="实现风险")
    test_cases: List[str] = Field(description="建议补充的测试用例")


def main() -> None:
    # 读取 .env 中的模型服务配置。
    load_dotenv()

    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # with_structured_output 会要求模型按 RequirementAnalysis 的结构返回结果。
    structured_model = model.with_structured_output(RequirementAnalysis)

    # 这里模拟一段产品需求。真实项目里可以替换成用户输入、PRD 文档或接口返回。
    requirement = """
    做一个审批列表页，支持搜索、筛选、分页、批量通过、查看审批详情。
    不同角色看到的操作按钮不同，审批失败需要展示错误原因。
    """

    result = structured_model.invoke(
        [
            ("system", "你是资深前端技术负责人，请把需求拆成可执行的前端开发信息。"),
            ("human", requirement),
        ]
    )

    # result 已经是 RequirementAnalysis 对象，不是普通字符串。
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
