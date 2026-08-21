# Agent UI 设计

Agent UI 不应该只是一个输入框和消息列表。

长任务需要展示当前阶段，例如 planning、retrieving、calling_tool、waiting_approval、summarizing、completed、failed。

工具调用需要展示工具名称、参数摘要、执行结果和错误信息。

涉及危险操作时，页面必须进入 waiting_approval 状态，等待用户确认后再继续执行。
