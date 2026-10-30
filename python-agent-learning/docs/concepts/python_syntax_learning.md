# Python 语法学习笔记（预览友好版）

这份文档用于配合本仓库的 `01-08` 练习脚本阅读 Python 代码。为了避免当前 Markdown 预览器把代码块渲染成空白，这里不使用三反引号代码块，也不使用 HTML 代码块；所有示例都用列表、表格和行内代码展示。文档前半部分加入 Python 与 JavaScript 的语法对照，便于从前端语法迁移理解。

阅读约定：

- `····` 表示 4 个空格缩进。
- 表格里的“代码”可以直接按内容理解；真正写到 `.py` 文件时，把 `····` 换成 4 个空格。
- 学习时先把简洁写法翻译成普通 `for` 循环，再反过来理解简洁写法。

## Python 与 JavaScript 语法对照速查

如果你熟悉 JavaScript，可以先用下面这张表建立映射。Python 和 JS 都是从上往下执行，但 Python 更依赖缩进表达代码块，JS 更依赖 `{}`。

| 主题 | Python | JavaScript | 关键区别 |
| --- | --- | --- | --- |
| 变量声明 | `name = "RAG"` | `const name = "RAG"` | Python 不需要 `let` / `const` / `var`。 |
| 字符串 | `"hello"` | `"hello"` | 基础字符串写法接近。 |
| 布尔值 | `True` / `False` | `true` / `false` | Python 首字母大写。 |
| 空值 | `None` | `null` / `undefined` | Python 主要用 `None` 表示没有值。 |
| 列表/数组 | `items = [1, 2, 3]` | `const items = [1, 2, 3]` | Python 叫 `list`，JS 叫 `Array`。 |
| 字典/对象 | `user = {"name": "Tom"}` | `const user = { name: "Tom" }` | Python 字典 key 常写字符串；JS 对象 key 可省略引号。 |
| 读取字段 | `user["name"]` | `user.name` 或 `user["name"]` | Python 字典常用 `[]`；对象属性才用点号。 |
| 函数 | `def add(a, b):` | `function add(a, b) {}` | Python 用 `def` 和缩进；JS 用 `{}`。 |
| 返回值 | `return a + b` | `return a + b` | `return` 含义一致。 |
| if 判断 | `if passed:` | `if (passed) {}` | Python 条件后面要写 `:`，代码块靠缩进。 |
| 否定 | `if not passed:` | `if (!passed) {}` | Python 用 `not`，JS 用 `!`。 |
| 循环 | `for item in items:` | `for (const item of items) {}` | Python 的 `for ... in ...` 接近 JS 的 `for ... of ...`。 |
| 是否包含 | `item in items` | `items.includes(item)` | Python 用 `in`；JS 数组常用 `includes()`。 |
| 长度 | `len(items)` | `items.length` | Python 长度是函数；JS 长度是属性。 |
| 求和 | `sum(numbers)` | `numbers.reduce((a, b) => a + b, 0)` | Python 有内置 `sum()`。 |
| 全部满足 | `all(check(x) for x in items)` | `items.every((x) => check(x))` | Python `all()` 接近 JS `every()`。 |
| 任意满足 | `any(check(x) for x in items)` | `items.some((x) => check(x))` | Python `any()` 接近 JS `some()`。 |
| 映射列表 | `[x * 2 for x in items]` | `items.map((x) => x * 2)` | Python 列表推导式接近 JS `map()`。 |
| 过滤列表 | `[x for x in items if x > 0]` | `items.filter((x) => x > 0)` | Python 把过滤条件写在推导式尾部。 |
| 去重集合 | `{x for x in items}` | `new Set(items)` | Python 用 `set`，JS 用 `Set`。 |
| 模板字符串 | `f"Hello {name}"` | `` `Hello ${name}` `` | Python 是 `f-string`；JS 是反引号模板字符串。 |
| 异常捕获 | `try` / `except Exception as error` | `try` / `catch (error)` | Python 用 `except`，JS 用 `catch`。 |

### 对照 1：if 判断

Python 写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `if not has_expected_source:` |
| 2 | `····print("缺少来源")` |

JavaScript 写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `if (!hasExpectedSource) {` |
| 2 | `····console.log("缺少来源")` |
| 3 | `}` |

对比重点：

- Python 用 `not`，JS 用 `!`。
- Python 用缩进表示代码块，JS 用 `{}` 表示代码块。
- Python 变量常用 snake_case，例如 `has_expected_source`。
- JS 变量常用 camelCase，例如 `hasExpectedSource`。

### 对照 2：for 循环

Python 写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `for source in expected_sources:` |
| 2 | `····print(source)` |

JavaScript 写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `for (const source of expectedSources) {` |
| 2 | `····console.log(source)` |
| 3 | `}` |

对比重点：

- Python 的 `for source in expected_sources` 接近 JS 的 `for (const source of expectedSources)`。
- Python 的 `in` 在循环里表示“逐个取出”。
- JS 里遍历数组一般用 `of`，不是 `in`；`for ... in` 在 JS 里主要遍历对象 key。

### 对照 3：全部满足 all 与 every

Python 写法：

| 代码 | 含义 |
| --- | --- |
| `all(source in sources for source in expected_sources)` | 所有 `expected_sources` 都存在于 `sources` 中。 |

JavaScript 写法：

| 代码 | 含义 |
| --- | --- |
| `expectedSources.every((source) => sources.includes(source))` | 所有 `expectedSources` 都存在于 `sources` 中。 |

如果 JS 里的 `sources` 是 `Set`，更接近 Python `set`：

| 代码 | 含义 |
| --- | --- |
| `expectedSources.every((source) => sources.has(source))` | 所有预期来源都存在于 `Set` 中。 |

对应关系：

| Python | JavaScript |
| --- | --- |
| `all(...)` | `.every(...)` |
| `source in sources` | `sources.includes(source)` 或 `sources.has(source)` |
| `for source in expected_sources` | `(source) => ...` |

### 对照 4：列表推导式与 map

Python 写法：

| 代码 | 含义 |
| --- | --- |
| `[run_eval_case(case) for case in EVAL_CASES]` | 遍历评测用例，返回每条用例的执行结果列表。 |

JavaScript 写法：

| 代码 | 含义 |
| --- | --- |
| `EVAL_CASES.map((caseItem) => runEvalCase(caseItem))` | 遍历评测用例，返回每条用例的执行结果数组。 |

对比重点：

- Python 推导式把“结果表达式”写在前面：`run_eval_case(case)`。
- JS `map()` 把“结果表达式”写在回调函数里：`(caseItem) => runEvalCase(caseItem)`。
- Python 变量名可以叫 `case`；JS 中 `case` 是 `switch` 语句关键字，通常改成 `caseItem`。

### 对照 5：集合推导式与 Set

Python 写法：

| 代码 | 含义 |
| --- | --- |
| `{doc.metadata["source"] for doc in related_docs}` | 从文档列表中提取来源，并去重。 |

JavaScript 写法：

| 代码 | 含义 |
| --- | --- |
| `new Set(relatedDocs.map((doc) => doc.metadata.source))` | 从文档数组中提取来源，并去重。 |

如果 JS 的 `metadata` 是普通对象，可以写 `doc.metadata.source`；如果 key 是动态字符串，也可以写 `doc.metadata["source"]`。

### 对照 6：函数和返回值

Python 写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `def run_eval_case(case: EvalCase) -> bool:` |
| 2 | `····passed = True` |
| 3 | `····return passed` |

JavaScript 写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `function runEvalCase(caseItem) {` |
| 2 | `····const passed = true` |
| 3 | `····return passed` |
| 4 | `}` |

TypeScript 写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `function runEvalCase(caseItem: EvalCase): boolean {` |
| 2 | `····const passed = true` |
| 3 | `····return passed` |
| 4 | `}` |

对比重点：

- Python 类型返回值写成 `-> bool`。
- TypeScript 类型返回值写成 `: boolean`。
- JavaScript 本身没有静态类型标注。

## 1. Python 文件的执行顺序

Python 文件通常从上往下执行。

示例代码：

| 行号 | 代码 |
| --- | --- |
| 1 | `print("第一步")` |
| 2 | `print("第二步")` |
| 3 | `print("第三步")` |

输出顺序：

| 行号 | 输出 |
| --- | --- |
| 1 | `第一步` |
| 2 | `第二步` |
| 3 | `第三步` |

在本项目脚本里，经常能看到这种结构：

| 行号 | 代码 |
| --- | --- |
| 1 | `import sys` |
| 2 | `from dataclasses import dataclass` |
| 3 | 空行 |
| 4 | `def main() -> None:` |
| 5 | `····print("真正的主流程写在这里")` |
| 6 | 空行 |
| 7 | `if __name__ == "__main__":` |
| 8 | `····main()` |

含义：

- `import sys`：导入依赖，会先执行。
- `def main()`：定义函数，不会立刻运行函数体。
- `if __name__ == "__main__":`：判断当前文件是不是被直接执行。
- `main()`：条件成立时才调用主流程。

## 2. 变量和赋值

变量就是给一个值起名字。

| 代码 | 含义 |
| --- | --- |
| `question = "Button 有哪些类型？"` | `question` 保存字符串。 |
| `count = 3` | `count` 保存整数。 |
| `passed = True` | `passed` 保存布尔值。 |

Python 不需要提前声明变量类型，但可以写类型标注：

| 代码 | 含义 |
| --- | --- |
| `question: str = "Button 有哪些类型？"` | `question` 应该是字符串。 |
| `count: int = 3` | `count` 应该是整数。 |
| `passed: bool = True` | `passed` 应该是布尔值。 |

类型标注主要给人、编辑器、类型检查工具看。它能提升可读性，但默认不会像 Pydantic 那样做运行时校验。

## 3. 常见基础类型

| 类型 | 示例 | 说明 |
| --- | --- | --- |
| `str` | `name = "button"` | 字符串。 |
| `int` | `count = 10` | 整数。 |
| `float` | `score = 0.95` | 小数。 |
| `bool` | `passed = True` | 布尔值，只有 `True` / `False`。 |
| `None` | `empty_value = None` | 表示没有值。 |

注意大小写：

- 正确：`True`、`False`、`None`
- 错误：`true`、`false`、`none`

## 4. 列表 list

列表用于保存一组有顺序的数据。

| 代码 | 含义 |
| --- | --- |
| `expected_terms = ["primary", "secondary", "danger"]` | 定义一个字符串列表。 |
| `first_term = expected_terms[0]` | 读取第 1 个元素，结果是 `"primary"`。 |
| `expected_terms.append("loading")` | 往列表末尾追加一个元素。 |

遍历列表：

| 行号 | 代码 |
| --- | --- |
| 1 | `for term in expected_terms:` |
| 2 | `····print(term)` |

执行含义：

- 第 1 次循环：`term = "primary"`
- 第 2 次循环：`term = "secondary"`
- 第 3 次循环：`term = "danger"`

## 5. 集合 set

集合用于保存一组不重复的数据。

| 代码 | 含义 |
| --- | --- |
| `sources = {"data/kb/button.md", "data/kb/form_validation.md"}` | 定义一个来源集合。 |
| `"data/kb/button.md" in sources` | 判断某个来源是否存在于集合中。 |
| `sources.add("data/kb/agent_ui.md")` | 往集合里添加一个元素。 |

集合会自动去重：

| 行号 | 代码 |
| --- | --- |
| 1 | `sources = {"a.md", "a.md", "b.md"}` |
| 2 | `print(sources)` |

输出结果只会保留一次 `a.md`：

- `{"a.md", "b.md"}`

在 `07_eval_regression.py` 中：

- `sources = {doc.metadata["source"] for doc in related_docs}`

这行会把检索命中的所有文档来源提取出来，并自动去重。

## 6. 字典 dict

字典用于保存 key-value 数据。

| 行号 | 代码 |
| --- | --- |
| 1 | `metadata = {` |
| 2 | `····"source": "data/kb/button.md",` |
| 3 | `····"title": "Button 组件规范",` |
| 4 | `}` |

读取字段：

| 代码 | 含义 |
| --- | --- |
| `source = metadata["source"]` | 按 key 读取 value。 |
| `title = metadata.get("title")` | 更稳妥地读取，key 不存在时返回 `None`。 |

区别：

- `metadata["source"]`：key 不存在会报错。
- `metadata.get("source")`：key 不存在不会报错，返回 `None`。

在当前项目里，`doc.metadata["source"]` 是可控数据，所以直接取值更简洁。

## 7. 函数 def

函数用于把一段逻辑封装起来，方便重复调用。

| 行号 | 代码 |
| --- | --- |
| 1 | `def add(a: int, b: int) -> int:` |
| 2 | `····return a + b` |

调用函数：

| 代码 | 结果 |
| --- | --- |
| `result = add(1, 2)` | `result` 等于 `3`。 |

解释：

- `def`：定义函数。
- `add`：函数名。
- `a`、`b`：函数参数。
- `a: int`：参数 `a` 预期是整数。
- `-> int`：函数预期返回整数。
- `return`：把结果返回给调用方。

在 `07_eval_regression.py` 中：

- `def run_eval_case(case: EvalCase) -> bool:`

意思是：传入一条 `EvalCase`，运行评测，最后返回 `True` 或 `False`。

## 8. if 判断

基础判断：

| 行号 | 代码 |
| --- | --- |
| 1 | `passed = True` |
| 2 | 空行 |
| 3 | `if passed:` |
| 4 | `····print("通过")` |
| 5 | `else:` |
| 6 | `····print("失败")` |

`if not` 表示条件取反：

| 行号 | 代码 |
| --- | --- |
| 1 | `has_expected_source = False` |
| 2 | 空行 |
| 3 | `if not has_expected_source:` |
| 4 | `····print("缺少来源")` |

等价理解：

- `if not has_expected_source:` 接近于 `if has_expected_source == False:`
- Python 更推荐写 `if not xxx`

常见写法：

| 代码 | 含义 |
| --- | --- |
| `if name:` | `name` 不是空字符串时成立。 |
| `if not items:` | `items` 是空列表时成立。 |
| `if value is None:` | `value` 没有值时成立。 |
| `if approval != "yes":` | 用户输入不是 `yes` 时成立。 |

## 9. for 循环

`for` 用来遍历列表、集合、字符串等可遍历对象。

| 行号 | 代码 |
| --- | --- |
| 1 | `terms = ["schema", "字段级错误"]` |
| 2 | 空行 |
| 3 | `for term in terms:` |
| 4 | `····print(term)` |

执行过程：

- 第 1 次循环：`term = "schema"`
- 第 2 次循环：`term = "字段级错误"`

循环里可以继续做判断：

| 行号 | 代码 |
| --- | --- |
| 1 | `context = "提交前需要 schema 校验，并展示字段级错误。"` |
| 2 | `terms = ["schema", "字段级错误"]` |
| 3 | 空行 |
| 4 | `for term in terms:` |
| 5 | `····if term in context:` |
| 6 | `········print(f"{term} 出现在上下文里")` |

## 10. in 的两种常见用法

`in` 有两个高频含义。

第一种：用于循环，表示“从里面逐个取出”。

- `for source in expected_sources:`

第二种：用于判断，表示“是否存在于里面”。

- `source in sources`

所以这一句：

- `all(source in sources for source in case.expected_sources)`

里面有两个 `in`：

| 片段 | 含义 |
| --- | --- |
| `source in sources` | 判断 `source` 是否在实际命中来源里。 |
| `for source in case.expected_sources` | 遍历所有预期来源。 |

阅读顺序：

1. 先看 `for source in case.expected_sources`：逐个拿到预期来源。
2. 再看 `source in sources`：判断这个预期来源是否在实际来源集合里。
3. 最后看 `all(...)`：要求所有判断结果都为 `True`。

## 11. 常用内置函数：len

`len()` 用来获取长度。

| 代码 | 结果 |
| --- | --- |
| `len(["a", "b", "c"])` | `3` |
| `len("hello")` | `5` |
| `len([])` | `0` |

在当前项目中：

- `total_count = len(results)`

意思是：统计一共跑了多少条评测用例。

## 12. 常用内置函数：sum

`sum()` 用来求和。

| 代码 | 结果 |
| --- | --- |
| `sum([1, 2, 3])` | `6` |
| `sum([10, 20])` | `30` |

Python 里：

- `True` 可以当成 `1`
- `False` 可以当成 `0`

所以：

| 代码 | 结果 |
| --- | --- |
| `sum([True, True, False, True])` | `3` |

如果列表里有 `None`，会报错：

- `sum([True, None, False])`
- 报错：`TypeError: unsupported operand type(s) for +: 'int' and 'NoneType'`

更稳的统计通过数量写法：

- `passed_count = sum(result is True for result in results)`

含义：只统计明确等于 `True` 的结果。

## 13. 常用内置函数：all

`all()` 用来判断一组条件是否全部为真。

| 代码 | 结果 |
| --- | --- |
| `all([True, True, True])` | `True` |
| `all([True, False, True])` | `False` |
| `all([])` | `True` |

注意：`all([])` 是 `True`，因为没有任何一个条件失败。这个规则叫“空集合上的全称判断为真”。

在当前项目中：

- `has_expected_source = all(source in sources for source in case.expected_sources)`

意思是：所有预期来源都命中了吗？

普通 `for` 循环版本：

| 行号 | 代码 |
| --- | --- |
| 1 | `has_expected_source = True` |
| 2 | 空行 |
| 3 | `for source in case.expected_sources:` |
| 4 | `····if source not in sources:` |
| 5 | `········has_expected_source = False` |
| 6 | `········break` |

## 14. 常用内置函数：any

`any()` 用来判断一组条件里是否至少有一个为真。

| 代码 | 结果 |
| --- | --- |
| `any([False, False, True])` | `True` |
| `any([False, False, False])` | `False` |
| `any([])` | `False` |

例子：

- `has_any_term = any(term in context for term in terms)`

意思是：只要有任意一个关键词出现在上下文里，就返回 `True`。

`all` 和 `any` 的区别：

| 函数 | 判断规则 |
| --- | --- |
| `all(...)` | 全部满足才是 `True`。 |
| `any(...)` | 至少一个满足就是 `True`。 |

## 15. 常用内置函数：sorted、print

`sorted()` 用来排序，并返回一个新的列表。

| 代码 | 结果 |
| --- | --- |
| `sorted({"b.md", "a.md", "c.md"})` | `["a.md", "b.md", "c.md"]` |

在当前项目中：

- `sorted(sources)`：把来源文件按字母顺序排序。

`print()` 用来输出内容：

| 代码 | 输出 |
| --- | --- |
| `print("Hello Python")` | `Hello Python` |
| `print(f"[{status}] {case.question}")` | 例如 `[通过] Button 有哪些类型？` |

## 16. f-string 格式化字符串

`f-string` 用来把变量插入字符串。

| 代码 | 含义 |
| --- | --- |
| `name = "RAG"` | 定义变量。 |
| `print(f"当前学习内容：{name}")` | 输出 `当前学习内容：RAG`。 |

大括号 `{}` 里可以放变量，也可以放表达式。

| 代码 | 输出 |
| --- | --- |
| `print(f"Eval 结果：{passed_count}/{total_count} 通过")` | 例如 `Eval 结果：3/4 通过` |

在 `07_eval_regression.py` 中：

- `print(f"[{status}] {case.question}")`

如果 `status = "通过"`，`case.question = "Button 有哪些类型？"`，输出就是：

- `[通过] Button 有哪些类型？`

## 17. join 字符串拼接

`join()` 用来把多个字符串按指定分隔符拼起来。

| 代码 | 结果 |
| --- | --- |
| `", ".join(["a", "b", "c"])` | `a, b, c` |
| `" / ".join(["api", "rag", "ask"])` | `api / rag / ask` |

在当前项目中：

- `", ".join(sorted(sources))`

执行顺序：

1. `sorted(sources)`：先把来源排序。
2. `", ".join(...)`：再用逗号和空格拼成一个字符串。

## 18. 列表推导式

列表推导式用于用一行代码生成列表。

基本格式：

- `[结果表达式 for 临时变量 in 可遍历对象]`

例子：

- `double_numbers = [number * 2 for number in numbers]`

如果 `numbers = [1, 2, 3]`，结果就是：

- `[2, 4, 6]`

等价普通写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `double_numbers = []` |
| 2 | 空行 |
| 3 | `for number in numbers:` |
| 4 | `····double_numbers.append(number * 2)` |

在当前项目中：

- `results = [run_eval_case(case) for case in EVAL_CASES]`

等价普通写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `results = []` |
| 2 | 空行 |
| 3 | `for case in EVAL_CASES:` |
| 4 | `····result = run_eval_case(case)` |
| 5 | `····results.append(result)` |

阅读规律：

1. 先看右边：`for case in EVAL_CASES`，表示遍历评测用例。
2. 再看左边：`run_eval_case(case)`，表示每次循环要生成什么结果。
3. 最外层是 `[...]`，表示把所有结果收集成列表。

## 19. 带 if 的列表推导式

列表推导式后面可以加过滤条件。

- `even_numbers = [number for number in numbers if number % 2 == 0]`

如果 `numbers = [1, 2, 3, 4, 5]`，结果就是：

- `[2, 4]`

等价普通写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `even_numbers = []` |
| 2 | 空行 |
| 3 | `for number in numbers:` |
| 4 | `····if number % 2 == 0:` |
| 5 | `········even_numbers.append(number)` |

格式规律：

- `[结果表达式 for 临时变量 in 可遍历对象 if 条件]`

意思是：遍历每个元素，只保留满足条件的元素。

## 20. 集合推导式

集合推导式用于生成 `set`，会自动去重。

基本格式：

- `{结果表达式 for 临时变量 in 可遍历对象}`

例子：

- `unique_files = {file for file in files}`

如果 `files = ["a.md", "a.md", "b.md"]`，结果就是：

- `{"a.md", "b.md"}`

等价普通写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `unique_files = set()` |
| 2 | 空行 |
| 3 | `for file in files:` |
| 4 | `····unique_files.add(file)` |

在当前项目中：

- `sources = {doc.metadata["source"] for doc in related_docs}`

等价普通写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `sources = set()` |
| 2 | 空行 |
| 3 | `for doc in related_docs:` |
| 4 | `····source = doc.metadata["source"]` |
| 5 | `····sources.add(source)` |

这里选择集合，是因为多个检索 chunk 可能来自同一个文件，只需要展示一次来源。

## 21. 生成器表达式

生成器表达式长得像列表推导式，但通常不会立刻生成完整列表。

基本格式：

- `(结果表达式 for 临时变量 in 可遍历对象)`

常见用法：

| 代码 | 含义 |
| --- | --- |
| `all(number > 0 for number in numbers)` | 判断所有数字是否都大于 `0`。 |
| `any(number % 2 == 0 for number in numbers)` | 判断是否存在偶数。 |
| `sum(number for number in numbers)` | 把所有数字加起来。 |

当生成器表达式是函数的唯一参数时，外层小括号可以省略：

- 常见写法：`all(number > 0 for number in numbers)`
- 完整理解：`all((number > 0 for number in numbers))`

在当前项目中：

- `has_expected_source = all(source in sources for source in case.expected_sources)`

它会按顺序产生一串布尔值：

- `source_1 in sources`
- `source_2 in sources`
- `source_3 in sources`

也就是类似：

- `True, True, False`

然后 `all()` 判断它们是否全部为 `True`。

## 22. 推导式统一阅读规律

遇到这类语法：

- `表达式 for 变量 in 集合`

不要从左往右硬读，建议按这个顺序读：

1. 先看 `for 变量 in 集合`：它在遍历什么？
2. 再看左侧 `表达式`：每次遍历要产生什么？
3. 最后看外层符号：结果要变成什么类型？

外层符号决定结果类型：

| 写法 | 结果类型 |
| --- | --- |
| `[x for x in items]` | `list`，列表。 |
| `{x for x in items}` | `set`，集合。 |
| `(x for x in items)` | `generator`，生成器。 |

对比：

| 代码 | 结果 |
| --- | --- |
| `[item for item in ["a", "b", "a"]]` | `["a", "b", "a"]` |
| `{item for item in ["a", "b", "a"]}` | `{"a", "b"}` |
| `(item for item in ["a", "b", "a"])` | 生成器对象，按需产出值。 |

## 23. all / any 的短路特性

`all()` 和 `any()` 都有短路特性。

`all()` 的规则：

- 一旦遇到 `False`，就直接返回 `False`。
- 后面的条件不再检查。

例子：

| 行号 | 代码 |
| --- | --- |
| 1 | `def check(value: int) -> bool:` |
| 2 | `····print(f"检查 {value}")` |
| 3 | `····return value < 3` |
| 4 | 空行 |
| 5 | `result = all(check(number) for number in [1, 2, 3, 4])` |

执行时会检查 `1`、`2`、`3`，不会继续检查 `4`，因为 `3 < 3` 已经是 `False`。

`any()` 的规则：

- 一旦遇到 `True`，就直接返回 `True`。
- 后面的条件不再检查。

例子：

| 行号 | 代码 |
| --- | --- |
| 1 | `def check(value: int) -> bool:` |
| 2 | `····print(f"检查 {value}")` |
| 3 | `····return value > 2` |
| 4 | 空行 |
| 5 | `result = any(check(number) for number in [1, 2, 3, 4])` |

执行时会检查 `1`、`2`、`3`，不会继续检查 `4`，因为 `3 > 2` 已经是 `True`。

## 24. dataclass 数据类

`dataclass` 适合定义“主要用来保存数据”的类。

普通类需要手写 `__init__`：

| 行号 | 代码 |
| --- | --- |
| 1 | `class EvalCase:` |
| 2 | `····def __init__(self, question: str, expected_sources: list[str], expected_terms: list[str]):` |
| 3 | `········self.question = question` |
| 4 | `········self.expected_sources = expected_sources` |
| 5 | `········self.expected_terms = expected_terms` |

使用 `dataclass` 后：

| 行号 | 代码 |
| --- | --- |
| 1 | `from dataclasses import dataclass` |
| 2 | 空行 |
| 3 | `@dataclass` |
| 4 | `class EvalCase:` |
| 5 | `····question: str` |
| 6 | `····expected_sources: list[str]` |
| 7 | `····expected_terms: list[str]` |

`@dataclass` 会自动生成初始化方法，所以可以直接创建对象：

| 字段 | 示例值 |
| --- | --- |
| `question` | `"Button 有哪些类型？"` |
| `expected_sources` | `["data/kb/button.md"]` |
| `expected_terms` | `["primary", "secondary", "danger"]` |

读取字段：

| 代码 | 结果 |
| --- | --- |
| `case.question` | 当前评测问题。 |
| `case.expected_sources` | 预期命中的来源文件。 |
| `case.expected_terms` | 预期出现的关键词。 |

## 25. 类型标注：List[str] 和 list[str]

在 `07_eval_regression.py` 中能看到：

- `from typing import List`
- `expected_sources: List[str]`

`List[str]` 表示：这是一个列表，里面每一项都是字符串。

在 Python 3.9+ 中，也可以写成：

- `expected_sources: list[str]`

当前项目使用 Python 3.11.9，所以两种都能用。

类型标注不会自动限制运行时数据：

| 代码 | 说明 |
| --- | --- |
| `def show_count(items: list[str]) -> None:` | 说明 `items` 应该是字符串列表。 |
| `show_count(["a", "b"])` | 符合预期。 |
| `show_count([1, 2])` | 运行时未必立刻报错，但类型检查工具会提示不符合预期。 |

类型标注的主要价值：

- 帮助自己和他人读懂字段含义。
- 帮助编辑器自动补全。
- 帮助类型检查工具提前发现问题。

## 26. typing：Any、Dict

`typing` 是 Python 标准库里的类型标注工具模块。

在 `08_human_approval_file_writer.py` 中：

- `from typing import Any, Dict`

含义：

| 类型 | 说明 |
| --- | --- |
| `Any` | 任意类型。 |
| `Dict` | 字典类型。 |

例子：

- `tool_call: Dict[str, Any]`

表示：

- `tool_call` 是一个字典。
- key 是字符串。
- value 可以是任意类型。

在 Python 3.9+ 也可以写成：

- `tool_call: dict[str, Any]`

## 27. Pydantic：BaseModel 和 Field

`pydantic` 不是 Python 自带语法，而是一个常用第三方库。它用于定义结构化数据，并在运行时做校验。

在 `08_human_approval_file_writer.py` 中：

- `from pydantic import BaseModel, Field`

`BaseModel` 用来定义数据结构：

| 行号 | 代码 |
| --- | --- |
| 1 | `class FileDraftInput(BaseModel):` |
| 2 | `····relative_path: str` |
| 3 | `····content: str` |
| 4 | `····reason: str` |

`Field` 用来给字段加说明：

- `relative_path: str = Field(description="要写入的相对路径，只允许写入 generated 目录")`

`model_validate_json()` 的作用：

- `FileDraftInput.model_validate_json(raw_result)`

含义：

1. 把 JSON 字符串解析成 Python 数据。
2. 校验字段是否符合 `FileDraftInput`。
3. 返回一个 `FileDraftInput` 对象。

校验成功后可以这样读取：

| 代码 | 含义 |
| --- | --- |
| `draft.relative_path` | 文件相对路径。 |
| `draft.content` | 文件内容。 |
| `draft.reason` | 写入原因。 |

## 28. 装饰器：@dataclass 和 @tool

装饰器是放在函数或类上面的一种包装语法。

常见格式：

- `@装饰器`
- `class SomeClass:`

或者：

- `@装饰器(...)`
- `def some_function():`

`@dataclass` 的作用：

- 把普通类包装成数据类。
- 自动生成初始化方法。

`@tool(args_schema=FileDraftInput)` 的作用：

- 把普通 Python 函数包装成 LangChain 工具。
- `args_schema=FileDraftInput` 表示工具参数必须符合 `FileDraftInput`。

在 `08_human_approval_file_writer.py` 中：

| 行号 | 代码 |
| --- | --- |
| 1 | `@tool(args_schema=FileDraftInput)` |
| 2 | `def create_file_draft(relative_path: str, content: str, reason: str) -> str:` |

关键点：

- `@tool` 本身不会执行函数。
- 它只是把函数注册成“模型可以调用的工具”。
- 真正执行工具的是 `.invoke(...)`。

## 29. pathlib.Path 和 resolve

`Path` 是 Python 里更现代的路径处理方式。

在 `08_human_approval_file_writer.py` 中：

- `PROJECT_ROOT = Path(__file__).parent`
- `OUTPUT_ROOT = PROJECT_ROOT / "generated"`
- `output_root = OUTPUT_ROOT.resolve()`

含义：

| 代码 | 说明 |
| --- | --- |
| `Path(__file__)` | 当前脚本文件路径。 |
| `.parent` | 当前脚本所在目录。 |
| `/ "generated"` | 拼接子目录。 |
| `.resolve()` | 转成规范化绝对路径，处理 `.`、`..`、软链接等。 |

为什么要用 `resolve()`：

- 用户或模型可能传入 `../xxx.py` 这种路径。
- 拼接后看起来在 `generated` 目录下。
- 但规范化后可能已经跑到目录外。
- `resolve()` 可以暴露真实目标路径，方便做安全检查。

危险路径例子：

- `relative_path = "../08_human_approval_file_writer.py"`

拼接后看起来像：

- `generated/../08_human_approval_file_writer.py`

规范化后会变成：

- `08_human_approval_file_writer.py`

这时后面的安全判断就能发现它越界了。

## 30. None、False、空列表的区别

这些值在 `if` 里都会被当成假：

| 值 | 在 if 中的真假 | 语义 |
| --- | --- | --- |
| `None` | 假 | 没有值。 |
| `False` | 假 | 明确的布尔假。 |
| `[]` | 假 | 空列表。 |
| `""` | 假 | 空字符串。 |
| `0` | 假 | 数字零。 |

推荐判断方式：

| 场景 | 推荐写法 |
| --- | --- |
| 判断是否没有值 | `if value is None:` |
| 判断布尔值是否为假 | `if not passed:` |
| 判断列表是否为空 | `if not results:` |
| 判断字符串是否为空 | `if not text:` |

## 31. 当前 Eval 脚本核心逻辑展开版

`07_eval_regression.py` 里的核心逻辑可以展开理解为：

| 步骤 | 代码 | 含义 |
| --- | --- | --- |
| 1 | `related_docs = rag_module.retrieve_context(case.question, chunks)` | 根据问题检索相关文档片段。 |
| 2 | `context = rag_module.build_context(related_docs)` | 把文档片段拼成上下文文本。 |
| 3 | `sources = set()` | 准备一个集合保存来源。 |
| 4 | `for doc in related_docs:` | 遍历检索结果。 |
| 5 | `····source = doc.metadata["source"]` | 取出每个文档片段的来源。 |
| 6 | `····sources.add(source)` | 把来源加入集合并自动去重。 |
| 7 | `has_expected_source = True` | 先假设来源命中。 |
| 8 | `for source in case.expected_sources:` | 遍历预期来源。 |
| 9 | `····if source not in sources:` | 如果某个预期来源没有命中。 |
| 10 | `········has_expected_source = False` | 标记来源检查失败。 |
| 11 | `········break` | 不再继续检查来源。 |
| 12 | `has_expected_terms = True` | 先假设关键词命中。 |
| 13 | `for term in case.expected_terms:` | 遍历预期关键词。 |
| 14 | `····if term not in context:` | 如果某个关键词不在上下文里。 |
| 15 | `········has_expected_terms = False` | 标记关键词检查失败。 |
| 16 | `········break` | 不再继续检查关键词。 |
| 17 | `passed = has_expected_source and has_expected_terms` | 来源和关键词都满足才通过。 |
| 18 | `return passed` | 返回评测结果。 |

对应的简洁写法：

| 代码 | 含义 |
| --- | --- |
| `sources = {doc.metadata["source"] for doc in related_docs}` | 提取来源并去重。 |
| `has_expected_source = all(source in sources for source in case.expected_sources)` | 检查预期来源是否全部命中。 |
| `has_expected_terms = all(term in context for term in case.expected_terms)` | 检查预期关键词是否全部出现。 |
| `passed = has_expected_source and has_expected_terms` | 两个条件都满足才通过。 |

## 32. 阅读陌生 Python 语法的套路

看到陌生语法时，按这个顺序拆：

1. 找赋值左边：这个变量最终保存什么？
2. 找最外层结构：是列表 `[]`、集合 `{}`、函数调用 `xxx()`，还是条件判断 `if`？
3. 如果有 `for ... in ...`，先看它在遍历什么。
4. 如果有 `if`，再看过滤条件或分支条件是什么。
5. 如果有 `all` / `any` / `sum`，想象它拿到的是一串值，再判断或统计。

例子：

- `has_expected_terms = all(term in context for term in case.expected_terms)`

拆解：

| 部分 | 说明 |
| --- | --- |
| `has_expected_terms` | 最终保存一个布尔值。 |
| `all(...)` | 要求里面所有判断都为真。 |
| `for term in case.expected_terms` | 遍历预期关键词。 |
| `term in context` | 判断关键词是否出现在上下文里。 |
| 整体含义 | 所有预期关键词是否都出现在 `context` 中。 |

## 33. 小练习

练习 1：判断来源是否全部命中。

| 代码 | 结果 |
| --- | --- |
| `sources = {"a.md", "b.md"}` | 定义实际命中来源。 |
| `expected_sources = ["a.md"]` | 定义预期来源。 |
| `all(source in sources for source in expected_sources)` | `True` |

练习 2：有一个来源没命中。

| 代码 | 结果 |
| --- | --- |
| `sources = {"a.md", "b.md"}` | 定义实际命中来源。 |
| `expected_sources = ["a.md", "c.md"]` | `c.md` 没命中。 |
| `all(source in sources for source in expected_sources)` | `False` |

练习 3：判断关键词是否全部出现。

| 代码 | 结果 |
| --- | --- |
| `context = "Button 支持 primary、secondary、danger 三种类型。"` | 上下文文本。 |
| `terms = ["primary", "danger"]` | 预期关键词。 |
| `all(term in context for term in terms)` | `True` |

练习 4：统计 Eval 通过数量。

| 代码 | 结果 |
| --- | --- |
| `results = [True, True, False, True]` | 4 条评测结果。 |
| `sum(results)` | `3` |
| `len(results)` | `4` |
| `f"Eval 结果：{sum(results)}/{len(results)} 通过"` | `Eval 结果：3/4 通过` |

## 34. 当前最值得优先掌握的语法

优先级建议：

1. `list`、`set`、`dict` 的基本使用。
2. `for` 循环和 `if` 判断。
3. 函数定义、参数、返回值。
4. `len()`、`sum()`、`all()`、`any()`、`sorted()`、`print()`。
5. 列表推导式、集合推导式、生成器表达式。
6. `dataclass` 和简单类型标注。
7. `pydantic` 的 `BaseModel`、`Field`、`model_validate_json()`。
8. 装饰器语法，例如 `@dataclass`、`@tool(...)`。

对当前 Agent 学习最有帮助的是：

- 能读懂数据从哪里来。
- 能读懂循环里每一步处理了什么。
- 能读懂布尔判断为什么通过或失败。
- 能把简洁写法还原成普通 `for` 循环。
- 能区分“模型生成调用请求”和“Python 真正执行工具”。

## 35. 逻辑运算：and、or、not

逻辑运算用于组合多个判断条件。

| Python | JavaScript | 含义 |
| --- | --- | --- |
| `a and b` | `a && b` | 两个条件都为真，整体才为真。 |
| `a or b` | `a || b` | 至少一个条件为真，整体就为真。 |
| `not a` | `!a` | 对条件取反。 |

在 `07_eval_regression.py` 中：

- `passed = has_expected_source and has_expected_terms`

含义：

| `has_expected_source` | `has_expected_terms` | `passed` |
| --- | --- | --- |
| `True` | `True` | `True` |
| `True` | `False` | `False` |
| `False` | `True` | `False` |
| `False` | `False` | `False` |

也就是说：来源命中，并且关键词也命中，这条 Eval 才算通过。

常见例子：

| 代码 | 含义 |
| --- | --- |
| `if user and user.is_active:` | 用户存在，并且用户是活跃状态。 |
| `if error or not result:` | 有错误，或者没有结果。 |
| `if not os.getenv("OPENAI_API_KEY"):` | 没有配置模型 Key。 |

## 36. 比较运算：==、!=、is、is not

比较运算用于判断两个值之间的关系。

| Python | JavaScript | 含义 |
| --- | --- | --- |
| `a == b` | `a === b` | 值是否相等。 |
| `a != b` | `a !== b` | 值是否不相等。 |
| `a > b` | `a > b` | 是否大于。 |
| `a >= b` | `a >= b` | 是否大于等于。 |
| `a < b` | `a < b` | 是否小于。 |
| `a <= b` | `a <= b` | 是否小于等于。 |

`is` 用来判断是不是同一个对象，最常见用法是判断 `None`：

| 推荐写法 | 不推荐写法 | 说明 |
| --- | --- | --- |
| `if value is None:` | `if value == None:` | 判断是否没有值。 |
| `if value is not None:` | `if value != None:` | 判断是否有值。 |

为什么判断 `None` 推荐用 `is`：

- `None` 是 Python 中表示“没有值”的特殊单例对象。
- `value is None` 的语义更准确。
- 这也是 Python 社区最常见写法。

注意：

- 判断普通数字、字符串是否相等，用 `==`。
- 判断是否是 `None`，用 `is None`。

## 37. try / except / finally 异常处理

异常处理用于防止程序因为某一步失败而直接崩溃。

基本结构：

| 行号 | 代码 |
| --- | --- |
| 1 | `try:` |
| 2 | `····result = risky_operation()` |
| 3 | `except Exception as error:` |
| 4 | `····print(f"执行失败：{error}")` |

含义：

- `try`：尝试执行可能失败的代码。
- `except`：如果 `try` 里的代码报错，就进入这里。
- `Exception as error`：把错误对象保存到变量 `error`。

在 `08_human_approval_file_writer.py` 中：

| 行号 | 代码 |
| --- | --- |
| 1 | `try:` |
| 2 | `····draft = parse_draft(raw_result)` |
| 3 | `except Exception as error:` |
| 4 | `····print(f"文件草稿解析失败：{type(error).__name__}: {error}")` |
| 5 | `····continue` |

含义：

- 如果 `parse_draft(raw_result)` 成功，就得到 `draft`。
- 如果 JSON 不合法或字段不符合要求，就打印错误，并跳过当前工具调用。

`finally` 表示无论成功还是失败都会执行：

| 行号 | 代码 |
| --- | --- |
| 1 | `try:` |
| 2 | `····print("执行主要逻辑")` |
| 3 | `except Exception as error:` |
| 4 | `····print(error)` |
| 5 | `finally:` |
| 6 | `····print("收尾逻辑")` |

常见用途：

- 关闭文件。
- 释放连接。
- 打印收尾日志。

## 38. with 上下文管理器

`with` 用于管理需要“打开后关闭”的资源，比如文件、网络连接、锁。

文件读取常见写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `with open("README.md", "r", encoding="utf-8") as file:` |
| 2 | `····content = file.read()` |

含义：

- `open(...)` 打开文件。
- `as file` 把打开后的文件对象命名为 `file`。
- 缩进块执行完后，Python 自动关闭文件。

不用 `with` 时，需要自己关闭：

| 行号 | 代码 |
| --- | --- |
| 1 | `file = open("README.md", "r", encoding="utf-8")` |
| 2 | `content = file.read()` |
| 3 | `file.close()` |

推荐使用 `with`，因为即使中间出错，也更容易保证文件被关闭。

在当前项目中，很多地方使用 `Path.read_text()` 和 `Path.write_text()`，它们把常见文件读写封装得更简单，所以不一定需要直接写 `with open(...)`。

## 39. Path 常见文件操作

`Path` 来自标准库 `pathlib`，用于处理文件路径。

| 代码 | 含义 |
| --- | --- |
| `path = Path("data/kb/button.md")` | 创建一个路径对象。 |
| `path.exists()` | 判断路径是否存在。 |
| `path.is_file()` | 判断是否是文件。 |
| `path.is_dir()` | 判断是否是目录。 |
| `path.parent` | 获取父目录。 |
| `path.name` | 获取文件名。 |
| `path.suffix` | 获取后缀名，例如 `.md`。 |
| `path.read_text(encoding="utf-8")` | 读取文本文件内容。 |
| `path.write_text(content, encoding="utf-8")` | 写入文本文件内容。 |
| `path.mkdir(parents=True, exist_ok=True)` | 创建目录，父目录不存在也一起创建。 |
| `path.resolve()` | 转成规范化绝对路径。 |

在 `08_human_approval_file_writer.py` 中：

- `target_path.parent.mkdir(parents=True, exist_ok=True)`
- `target_path.write_text(draft.content, encoding="utf-8")`

含义：

1. 先确保目标文件所在目录存在。
2. 再把内容写入目标文件。

注意：

- `write_text()` 会真正修改磁盘文件。
- 所以项目里在写文件前加了人工确认和路径安全检查。

## 40. 函数参数：默认参数、关键字参数、*args、**kwargs

函数参数有几种常见形式。

普通参数：

| 行号 | 代码 |
| --- | --- |
| 1 | `def add(a, b):` |
| 2 | `····return a + b` |

调用：

- `add(1, 2)`

默认参数：

| 行号 | 代码 |
| --- | --- |
| 1 | `def greet(name, prefix="你好"):` |
| 2 | `····return f"{prefix}，{name}"` |

调用：

| 代码 | 结果 |
| --- | --- |
| `greet("Tom")` | `你好，Tom` |
| `greet("Tom", prefix="Hello")` | `Hello，Tom` |

关键字参数：

- `greet(name="Tom", prefix="Hello")`

优点：

- 调用时更清楚每个值传给哪个参数。
- 参数顺序不容易搞错。

`*args` 表示接收任意数量的位置参数：

| 行号 | 代码 |
| --- | --- |
| 1 | `def show_args(*args):` |
| 2 | `····print(args)` |

调用：

- `show_args(1, 2, 3)`
- `args` 会是 `(1, 2, 3)`

`**kwargs` 表示接收任意数量的关键字参数：

| 行号 | 代码 |
| --- | --- |
| 1 | `def show_kwargs(**kwargs):` |
| 2 | `····print(kwargs)` |

调用：

- `show_kwargs(name="Tom", age=18)`
- `kwargs` 会是 `{"name": "Tom", "age": 18}`

学习阶段先掌握普通参数、默认参数、关键字参数即可。

## 41. return、break、continue、pass

这几个关键字都用于控制代码执行流程。

| 关键字 | 含义 | 常见位置 |
| --- | --- | --- |
| `return` | 从函数返回结果，并结束函数。 | 函数内部。 |
| `break` | 结束当前循环。 | `for` / `while` 循环内部。 |
| `continue` | 跳过本轮循环，进入下一轮。 | `for` / `while` 循环内部。 |
| `pass` | 什么都不做，占位用。 | 函数、类、if 分支内部。 |

`return` 示例：

| 行号 | 代码 |
| --- | --- |
| 1 | `def is_even(number):` |
| 2 | `····return number % 2 == 0` |

`break` 示例：

| 行号 | 代码 |
| --- | --- |
| 1 | `for number in [1, 2, 3, 4]:` |
| 2 | `····if number == 3:` |
| 3 | `········break` |
| 4 | `····print(number)` |

输出：

- `1`
- `2`

`continue` 示例：

| 行号 | 代码 |
| --- | --- |
| 1 | `for number in [1, 2, 3, 4]:` |
| 2 | `····if number == 3:` |
| 3 | `········continue` |
| 4 | `····print(number)` |

输出：

- `1`
- `2`
- `4`

`pass` 示例：

| 行号 | 代码 |
| --- | --- |
| 1 | `def todo_function():` |
| 2 | `····pass` |

含义：先占一个位置，后续再实现。

## 42. range、enumerate、zip

这三个函数经常和 `for` 循环一起使用。

`range()` 用来生成数字序列：

| 代码 | 产生的值 |
| --- | --- |
| `range(3)` | `0`、`1`、`2` |
| `range(1, 4)` | `1`、`2`、`3` |
| `range(0, 6, 2)` | `0`、`2`、`4` |

示例：

| 行号 | 代码 |
| --- | --- |
| 1 | `for index in range(3):` |
| 2 | `····print(index)` |

`enumerate()` 用来同时拿到索引和值：

| 行号 | 代码 |
| --- | --- |
| 1 | `items = ["a", "b", "c"]` |
| 2 | `for index, item in enumerate(items):` |
| 3 | `····print(index, item)` |

输出：

| index | item |
| --- | --- |
| `0` | `a` |
| `1` | `b` |
| `2` | `c` |

`zip()` 用来同时遍历多个列表：

| 行号 | 代码 |
| --- | --- |
| 1 | `names = ["Tom", "Jerry"]` |
| 2 | `ages = [18, 20]` |
| 3 | `for name, age in zip(names, ages):` |
| 4 | `····print(name, age)` |

输出：

| name | age |
| --- | --- |
| `Tom` | `18` |
| `Jerry` | `20` |

## 43. 切片和索引

索引用于读取单个元素，切片用于读取一段元素。

假设：

- `items = ["a", "b", "c", "d", "e"]`

索引：

| 代码 | 结果 |
| --- | --- |
| `items[0]` | `"a"` |
| `items[1]` | `"b"` |
| `items[-1]` | `"e"` |
| `items[-2]` | `"d"` |

切片：

| 代码 | 结果 |
| --- | --- |
| `items[0:3]` | `["a", "b", "c"]` |
| `items[:3]` | `["a", "b", "c"]` |
| `items[2:]` | `["c", "d", "e"]` |
| `items[1:4]` | `["b", "c", "d"]` |
| `items[:]` | 复制整个列表。 |

规律：

- `items[start:end]` 包含 `start`，不包含 `end`。
- `items[0:3]` 取索引 `0`、`1`、`2`。
- 负数索引从末尾开始数。

字符串也支持索引和切片：

| 代码 | 结果 |
| --- | --- |
| `"hello"[0]` | `"h"` |
| `"hello"[:2]` | `"he"` |

## 44. 元组 tuple 和解包

元组和列表类似，也能保存多个值，但通常用于表示固定结构的数据。

| 类型 | 示例 | 是否常修改 |
| --- | --- | --- |
| `list` | `[1, 2, 3]` | 常用于可变列表。 |
| `tuple` | `(1, 2, 3)` | 常用于固定组合。 |

元组示例：

- `point = (10, 20)`

读取：

| 代码 | 结果 |
| --- | --- |
| `point[0]` | `10` |
| `point[1]` | `20` |

解包语法：

| 代码 | 含义 |
| --- | --- |
| `x, y = point` | 把 `point` 里的两个值分别赋给 `x` 和 `y`。 |

函数可以返回多个值，本质上通常是返回一个元组：

| 行号 | 代码 |
| --- | --- |
| 1 | `def get_user():` |
| 2 | `····return "Tom", 18` |
| 3 | `name, age = get_user()` |

执行后：

| 变量 | 值 |
| --- | --- |
| `name` | `"Tom"` |
| `age` | `18` |

在循环中也常见解包：

- `for index, item in enumerate(items):`
- `for name, age in zip(names, ages):`

## 45. 列表常用方法

列表常用方法如下。

| 方法 | 示例 | 含义 |
| --- | --- | --- |
| `append()` | `items.append("a")` | 在末尾追加一个元素。 |
| `extend()` | `items.extend(["b", "c"])` | 把另一个列表的元素追加进来。 |
| `remove()` | `items.remove("a")` | 删除第一个匹配的元素。 |
| `pop()` | `items.pop()` | 删除并返回最后一个元素。 |
| `sort()` | `items.sort()` | 原地排序，会修改原列表。 |
| `count()` | `items.count("a")` | 统计某个元素出现次数。 |
| `index()` | `items.index("a")` | 查找某个元素的索引。 |

`sorted(items)` 和 `items.sort()` 的区别：

| 写法 | 是否修改原列表 | 返回值 |
| --- | --- | --- |
| `sorted(items)` | 不修改 | 返回新列表。 |
| `items.sort()` | 修改原列表 | 返回 `None`。 |

学习阶段建议：

- 想保留原列表，用 `sorted(items)`。
- 明确要修改原列表，用 `items.sort()`。

## 46. 字典常用方法

字典常用方法如下。

| 方法 | 示例 | 含义 |
| --- | --- | --- |
| `get()` | `user.get("name")` | 获取 key 对应的值，不存在时返回 `None`。 |
| `keys()` | `user.keys()` | 获取所有 key。 |
| `values()` | `user.values()` | 获取所有 value。 |
| `items()` | `user.items()` | 获取所有 key-value 对。 |
| `update()` | `user.update({"age": 18})` | 更新字典。 |
| `pop()` | `user.pop("name")` | 删除 key，并返回对应 value。 |

遍历字典 key：

| 行号 | 代码 |
| --- | --- |
| 1 | `for key in user:` |
| 2 | `····print(key)` |

遍历 key 和 value：

| 行号 | 代码 |
| --- | --- |
| 1 | `for key, value in user.items():` |
| 2 | `····print(key, value)` |

和 JavaScript 对照：

| Python | JavaScript |
| --- | --- |
| `user.keys()` | `Object.keys(user)` |
| `user.values()` | `Object.values(user)` |
| `user.items()` | `Object.entries(user)` |

## 47. json.dumps 和 json.loads

`json` 是 Python 标准库，用于处理 JSON 数据。

常见导入：

- `import json`

`json.dumps()`：把 Python 数据转成 JSON 字符串。

| 代码 | 含义 |
| --- | --- |
| `json.dumps({"name": "Tom"})` | 转成 JSON 字符串。 |
| `json.dumps(data, ensure_ascii=False)` | 中文不要转成 Unicode 转义。 |
| `json.dumps(data, indent=2)` | 输出更容易阅读的缩进格式。 |

`json.loads()`：把 JSON 字符串转成 Python 数据。

| 代码 | 含义 |
| --- | --- |
| `json.loads(raw_text)` | 把 JSON 字符串解析成字典或列表。 |

在 `08_human_approval_file_writer.py` 中：

- `json.dumps({...}, ensure_ascii=False, indent=2)`

含义：

1. 工具函数返回的是字符串。
2. 但字符串内容是标准 JSON。
3. 后面可以用 Pydantic 的 `model_validate_json()` 解析并校验。

和 JavaScript 对照：

| Python | JavaScript | 含义 |
| --- | --- | --- |
| `json.dumps(data)` | `JSON.stringify(data)` | 对象转 JSON 字符串。 |
| `json.loads(text)` | `JSON.parse(text)` | JSON 字符串转对象。 |

## 48. os.getenv 和环境变量

环境变量常用于保存配置和敏感信息，例如 API Key。

常见导入：

- `import os`

读取环境变量：

| 代码 | 含义 |
| --- | --- |
| `os.getenv("OPENAI_API_KEY")` | 读取模型 Key。 |
| `os.getenv("OPENAI_MODEL", "gpt-4o-mini")` | 没有配置时使用默认值。 |

在当前项目中：

- `bool(os.getenv("OPENAI_API_KEY"))`

含义：

- 如果环境变量存在且不是空字符串，结果是 `True`。
- 如果没配置，结果是 `False`。

常见判断：

| 代码 | 含义 |
| --- | --- |
| `if not os.getenv("OPENAI_API_KEY"):` | 没有配置 Key。 |
| `if os.getenv("OPENAI_API_KEY"):` | 已经配置 Key。 |

为什么 API Key 放环境变量：

- 避免写死在代码里。
- 避免提交到 Git。
- 不同环境可以使用不同配置。

## 49. import 的几种写法

`import` 用于导入模块或模块里的对象。

普通导入：

| 代码 | 使用方式 |
| --- | --- |
| `import os` | `os.getenv("OPENAI_API_KEY")` |
| `import json` | `json.dumps(data)` |

从模块导入具体对象：

| 代码 | 使用方式 |
| --- | --- |
| `from pathlib import Path` | `Path("README.md")` |
| `from dataclasses import dataclass` | `@dataclass` |

起别名：

| 代码 | 使用方式 |
| --- | --- |
| `import pandas as pd` | `pd.DataFrame(...)` |
| `import numpy as np` | `np.array(...)` |

动态导入：

| 代码 | 含义 |
| --- | --- |
| `import importlib` | 导入动态导入模块。 |
| `rag_module = importlib.import_module("04_rag_qa")` | 按字符串导入 `04_rag_qa.py`。 |

为什么当前项目用 `importlib.import_module("04_rag_qa")`：

- 文件名 `04_rag_qa.py` 以数字开头。
- Python 不能直接写 `import 04_rag_qa`。
- 所以使用 `importlib` 按字符串导入。

## 50. 普通 class、self、__init__

`class` 用于定义类。类可以理解为一种对象模板。

普通类写法：

| 行号 | 代码 |
| --- | --- |
| 1 | `class User:` |
| 2 | `····def __init__(self, name: str, age: int):` |
| 3 | `········self.name = name` |
| 4 | `········self.age = age` |

创建对象：

| 代码 | 含义 |
| --- | --- |
| `user = User("Tom", 18)` | 创建一个 `User` 对象。 |
| `user.name` | 读取对象的 `name` 属性。 |
| `user.age` | 读取对象的 `age` 属性。 |

`self` 是什么：

- `self` 表示当前这个对象自己。
- `self.name = name` 表示把参数 `name` 保存到当前对象的 `name` 属性上。
- 类方法的第一个参数通常都写 `self`。

`__init__` 是什么：

- 创建对象时自动执行的初始化方法。
- 类似 JavaScript class 里的 `constructor`。

Python 与 JavaScript 对照：

| Python | JavaScript |
| --- | --- |
| `class User:` | `class User {}` |
| `def __init__(self, name):` | `constructor(name) {}` |
| `self.name = name` | `this.name = name` |
| `user.name` | `user.name` |

`@dataclass` 和普通 class 的关系：

- 普通 class：需要自己写 `__init__`。
- `@dataclass`：自动帮你生成 `__init__`。
- 如果类主要只是保存数据，用 `@dataclass` 更省代码。

## 51. 模块、包和 __name__

一个 `.py` 文件就是一个模块。

例子：

| 文件 | 模块名 |
| --- | --- |
| `07_eval_regression.py` | `07_eval_regression` |
| `08_human_approval_file_writer.py` | `08_human_approval_file_writer` |

包通常是一个目录，里面包含多个模块。

`__name__` 是 Python 自动提供的特殊变量。

| 场景 | `__name__` 的值 |
| --- | --- |
| 直接运行当前文件 | `"__main__"` |
| 被其他文件 import | 模块名。 |

所以常见写法是：

| 行号 | 代码 |
| --- | --- |
| 1 | `if __name__ == "__main__":` |
| 2 | `····main()` |

含义：

- 直接运行这个文件时，执行 `main()`。
- 被其他文件导入时，不自动执行 `main()`。

为什么这很重要：

- 测试文件 import 练习脚本时，不希望脚本主流程自动运行。
- 只希望复用里面的函数。

## 52. lambda 匿名函数

`lambda` 用于定义很短的小函数。

普通函数：

| 行号 | 代码 |
| --- | --- |
| 1 | `def double(x):` |
| 2 | `····return x * 2` |

`lambda` 写法：

- `double = lambda x: x * 2`

调用：

- `double(3)` 结果是 `6`

常见使用场景：排序时指定 key。

| 代码 | 含义 |
| --- | --- |
| `items.sort(key=lambda item: item["score"])` | 按每个元素的 `score` 字段排序。 |

和 JavaScript 对照：

| Python | JavaScript |
| --- | --- |
| `lambda x: x * 2` | `(x) => x * 2` |

学习阶段建议：

- 能看懂即可。
- 复杂逻辑不要硬写 `lambda`，用普通 `def` 更清楚。

## 53. while 循环

`while` 表示只要条件成立，就一直循环。

基本格式：

| 行号 | 代码 |
| --- | --- |
| 1 | `count = 0` |
| 2 | `while count < 3:` |
| 3 | `····print(count)` |
| 4 | `····count = count + 1` |

输出：

- `0`
- `1`
- `2`

注意：

- `while` 条件一直为真时，会造成死循环。
- 写 `while` 时要确认循环内部会改变条件。

常见退出方式：

| 代码 | 含义 |
| --- | --- |
| `break` | 立即退出循环。 |
| `continue` | 跳过本轮，进入下一轮。 |

在 Agent 脚本里，`for` 循环更常见；`while` 通常用于命令行交互、轮询、重试等场景。

## 54. assert 断言

`assert` 用来声明“这里应该为真”。

基本写法：

- `assert passed`

如果 `passed` 是 `True`，程序继续执行。

如果 `passed` 是 `False`，程序报 `AssertionError`。

带错误信息：

- `assert passed, "评测应该通过"`

在测试中常见：

| 代码 | 含义 |
| --- | --- |
| `assert result == expected` | 检查实际结果是否等于预期结果。 |
| `assert "source" in metadata` | 检查字典里是否包含 `source`。 |
| `assert len(results) == 4` | 检查结果数量是否为 4。 |

注意：

- `assert` 适合测试和开发期检查。
- 生产逻辑里不要把关键业务校验只依赖 `assert`。

## 55. 真实项目源码语法：list(map(lambda ...))

在 MaxKB 源码里看到的这句：

| 行号 | 代码 |
| --- | --- |
| 1 | `exit_list = list(` |
| 2 | `····map(lambda p: exist(request.auth.role_list, request.auth.permission_list, p, request, **kwargs),` |
| 3 | `········permission))` |

可以先翻译成普通循环：

| 行号 | 代码 |
| --- | --- |
| 1 | `exit_list = []` |
| 2 | `for p in permission:` |
| 3 | `····result = exist(request.auth.role_list, request.auth.permission_list, p, request, **kwargs)` |
| 4 | `····exit_list.append(result)` |

含义：

- `permission` 里有多个权限条件。
- `map(...)` 负责逐个遍历这些权限条件。
- `lambda p: ...` 表示对每一个权限条件 `p` 执行一次检查。
- `exist(...)` 负责判断当前用户是否满足这个权限条件。
- `list(...)` 把所有判断结果收集成列表。

结果可能是：

| 代码 | 含义 |
| --- | --- |
| `exit_list = [True, False, False]` | 三个权限条件里，第一个满足。 |
| `exit_list = [False, False, False]` | 所有权限条件都不满足。 |
| `exit_list = [True, True, False]` | 前两个权限条件满足。 |

## 56. list 的两种常见用法

`list` 在源码里常见两种形态。

第一种：列表字面量，用 `[]`。

| 代码 | 含义 |
| --- | --- |
| `[TokenAuth]` | 一个列表，里面放了 `TokenAuth` 这个类对象。 |
| `[1, 2, 3]` | 一个列表，里面放了 3 个数字。 |
| `["read", "write"]` | 一个列表，里面放了 2 个字符串。 |

第二种：`list(...)` 函数，把可迭代对象转换成列表。

| 代码 | 含义 |
| --- | --- |
| `list(map(lambda x: x * 2, [1, 2, 3]))` | 得到 `[2, 4, 6]`。 |
| `list("abc")` | 得到 `["a", "b", "c"]`。 |
| `list(queryset)` | 把 Django 查询结果转成普通列表。 |

注意：

- `[TokenAuth]` 是直接创建列表。
- `list(map(...))` 是先计算 `map(...)`，再转成列表。
- `list` 是 Python 内置函数；`List[str]` 是类型标注，两者不是一回事。

## 57. map、lambda、for 循环的对应关系

`map(func, items)` 的意思是：对 `items` 里的每一项都执行 `func`。

示例：

| 代码 | 结果 |
| --- | --- |
| `list(map(lambda x: x * 2, [1, 2, 3]))` | `[2, 4, 6]` |

等价循环：

| 行号 | 代码 |
| --- | --- |
| 1 | `result = []` |
| 2 | `for x in [1, 2, 3]:` |
| 3 | `····result.append(x * 2)` |

`lambda x: x * 2` 是匿名函数，等价于：

| 行号 | 代码 |
| --- | --- |
| 1 | `def double(x):` |
| 2 | `····return x * 2` |

所以：

| 代码 | 含义 |
| --- | --- |
| `map(lambda x: x * 2, items)` | 遍历 `items`，每个 `x` 返回 `x * 2`。 |
| `map(lambda p: exist(..., p, ...), permission)` | 遍历 `permission`，每个 `p` 调用一次 `exist(...)`。 |

学习阶段建议：

- 看到 `map(lambda...)`，先改写成 `for` 循环理解。
- 如果 `lambda` 里逻辑很长，用普通 `def` 更清楚。
- 项目代码里为了简洁会用 `map(lambda...)`，但新代码不一定要模仿。

## 58. exist 不是 Python 语法

`exist` 不是 Python 关键字，也不是内置函数。

它只是这个项目自己定义的普通函数名：

| 行号 | 代码 |
| --- | --- |
| 1 | `def exist(user_role, user_permission, permission, request, **kwargs):` |

所以这句：

| 代码 | 含义 |
| --- | --- |
| `exist(request.auth.role_list, request.auth.permission_list, p, request, **kwargs)` | 调用项目里的 `exist` 函数，判断当前用户是否拥有某个权限或角色。 |

参数拆开看：

| 参数 | 含义 |
| --- | --- |
| `request.auth.role_list` | 当前用户拥有的角色列表。 |
| `request.auth.permission_list` | 当前用户拥有的权限列表。 |
| `p` | 当前正在检查的某一个权限条件。 |
| `request` | 当前 HTTP 请求对象。 |
| `**kwargs` | 额外上下文，比如 `workspace_id`、`knowledge_id`。 |

源码阅读时判断一个名字是不是语法：

| 情况 | 怎么判断 |
| --- | --- |
| `def exist(...)` | 说明 `exist` 是当前文件定义的函数。 |
| `from xxx import exist` | 说明 `exist` 是从其他文件导入的函数。 |
| `exist(...)` | 说明正在调用这个函数。 |

所以不要把所有陌生名字都当成 Python 语法。很多名字只是项目作者起的函数名、类名、变量名。

## 59. *permission 和 **kwargs 在这段代码里的意思

这段函数：

| 行号 | 代码 |
| --- | --- |
| 1 | `def is_permissions(*permission, compare=CompareConstants.OR):` |

`*permission` 表示接收任意多个位置参数。

调用：

| 代码 | 函数内部的值 |
| --- | --- |
| `is_permissions(A)` | `permission == (A,)` |
| `is_permissions(A, B, C)` | `permission == (A, B, C)` |

注意：

- `permission` 虽然名字是单数，但因为前面有 `*`，所以它在函数内部是一个元组。
- `for p in permission` 就是在遍历这个元组。

这段函数：

| 行号 | 代码 |
| --- | --- |
| 1 | `def get_is_permissions(request, **kwargs):` |

`**kwargs` 表示接收任意多个关键字参数。

调用：

| 代码 | 函数内部的值 |
| --- | --- |
| `get_is_permissions(request, workspace_id="w1")` | `kwargs == {"workspace_id": "w1"}` |
| `get_is_permissions(request, workspace_id="w1", knowledge_id="k1")` | `kwargs == {"workspace_id": "w1", "knowledge_id": "k1"}` |

再传给别的函数时：

| 代码 | 等价理解 |
| --- | --- |
| `exist(..., **kwargs)` | 把 `kwargs` 展开成 `workspace_id="w1"` 这类参数。 |

## 60. 返回函数本身：return is_permissions

这里最后一行是：

| 代码 | 含义 |
| --- | --- |
| `return is_permissions` | 返回 `is_permissions` 这个函数本身。 |

注意不是：

| 代码 | 含义 |
| --- | --- |
| `return is_permissions()` | 立刻执行 `is_permissions`，返回执行结果。 |

所以这段：

| 行号 | 代码 |
| --- | --- |
| 1 | `checker = get_is_permissions(request, workspace_id=workspace_id)` |
| 2 | `is_import_tool = checker(A, B, C)` |

等价于项目里的连写：

| 代码 |
| --- |
| `is_import_tool = get_is_permissions(request, workspace_id=workspace_id)(A, B, C)` |

理解成两步：

1. `get_is_permissions(...)` 先绑定 `request` 和 `workspace_id`。
2. 返回的 `checker` 再检查 `A/B/C` 这些权限。

## 61. any、all 和三元表达式

这句：

| 代码 |
| --- |
| `return any(exit_list) if compare == CompareConstants.OR else all(exit_list)` |

是 Python 三元表达式。

等价于：

| 行号 | 代码 |
| --- | --- |
| 1 | `if compare == CompareConstants.OR:` |
| 2 | `····return any(exit_list)` |
| 3 | `else:` |
| 4 | `····return all(exit_list)` |

`any` 和 `all`：

| 代码 | 结果 | 含义 |
| --- | --- | --- |
| `any([False, True, False])` | `True` | 只要有一个满足即可。 |
| `all([False, True, False])` | `False` | 必须全部满足。 |
| `all([True, True])` | `True` | 全部满足。 |

在权限场景里：

| compare | 含义 |
| --- | --- |
| `CompareConstants.OR` | 任意一个权限满足即可放行。 |
| 非 `OR`，通常是 `AND` | 所有权限都满足才放行。 |

## 62. 类、类对象和列表中放类

这句：

| 代码 |
| --- |
| `authentication_classes = [TokenAuth]` |

里面的 `TokenAuth` 是类对象，不是字符串，也不是函数调用。

对比：

| 写法 | 含义 |
| --- | --- |
| `TokenAuth` | 类对象本身。 |
| `TokenAuth()` | 创建一个 `TokenAuth` 实例。 |
| `[TokenAuth]` | 创建列表，列表里放这个类对象。 |

DRF 会读取这个列表，然后自己实例化：

| 行号 | 伪代码 |
| --- | --- |
| 1 | `for auth_class in authentication_classes:` |
| 2 | `····authenticator = auth_class()` |
| 3 | `····authenticator.authenticate(request)` |

所以源码里看起来没有直接调用 `TokenAuth()`，但框架会按约定读取 `authentication_classes`。

同类写法：

| 代码 | 含义 |
| --- | --- |
| `parser_classes = [MultiPartParser]` | 告诉 DRF 用 `MultiPartParser` 解析上传文件。 |
| `authentication_classes = [TokenAuth]` | 告诉 DRF 用 `TokenAuth` 做身份认证。 |

## 63. 装饰器和 raise 也是这次源码阅读的重点

装饰器：

| 代码 | 含义 |
| --- | --- |
| `@has_permissions(...)` | 给下面的接口方法加权限检查。 |
| `@log(...)` | 给下面的接口方法加操作日志。 |
| `@transaction.atomic` | 给下面的方法加数据库事务。 |

装饰器等价理解：

| 写法 | 等价理解 |
| --- | --- |
| `@has_permissions(A)` + `def post(...): ...` | `post = has_permissions(A)(post)` |

`raise`：

| 代码 | 含义 |
| --- | --- |
| `raise AppAuthenticationFailed(1003, "Not logged in")` | 抛出异常，中断当前流程。 |

`return` 和 `raise` 的区别：

| 写法 | 含义 |
| --- | --- |
| `return value` | 正常结束函数，返回一个值。 |
| `raise error` | 异常结束函数，把错误交给上层处理。 |

在接口源码里：

- `return result.success(...)` 表示正常返回。
- `raise AppAuthenticationFailed(...)` 表示认证失败，后续业务不执行。
- `raise AppUnauthorizedFailed(...)` 表示权限失败，后续业务不执行。

## 64. 当前文档新增语法的学习顺序

建议按这个顺序继续学：

1. `and` / `or` / `not`，先理解多个条件怎么组合。
2. `==` / `!=` / `is None`，先理解判断语义。
3. `try` / `except`，读懂工具调用和 JSON 解析失败时怎么兜底。
4. `Path`、`with`、文件读写，读懂为什么写文件前要做安全检查。
5. `json.dumps()` / `json.loads()`，读懂工具返回结构化数据的方式。
6. `os.getenv()`，读懂为什么没有 Key 时不调用模型。
7. `class` / `self` / `__init__`，再回头理解 `@dataclass` 为什么省事。
8. `range()` / `enumerate()` / `zip()`，补齐循环能力。
9. 切片、元组、解包，提升阅读 Python 代码的熟练度。
10. `assert`，配合 `pytest` 阅读测试文件。
11. `list(map(lambda...))`，读懂真实项目里把循环写短的方式。
12. `*args` / `**kwargs`，读懂权限、装饰器、框架回调里的参数传递。
13. 函数作为返回值，读懂 `get_is_permissions(...)(...)` 这种连写。
14. 类对象放进列表，读懂 `authentication_classes = [TokenAuth]` 这类框架配置。
15. `raise`，读懂认证失败、权限失败为什么会中断业务流程。

## 65. 当前 Agent Loop 里的 enumerate 写法

这一句来自 `09_requirement_agent_loop.py`：

- `for case_index, requirement in enumerate(SAMPLE_REQUIREMENTS, start=1):`

`enumerate()` 的作用是：遍历列表时，同时拿到序号和值。

| 变量 | 含义 |
| --- | --- |
| `case_index` | 当前是第几个样例，从 `1` 开始。 |
| `requirement` | 当前正在处理的页面需求文本。 |
| `SAMPLE_REQUIREMENTS` | 所有固定页面需求组成的列表。 |

如果不用 `enumerate()`，等价写法是：

| 行号 | 代码 |
| --- | --- |
| 1 | `case_index = 1` |
| 2 | `for requirement in SAMPLE_REQUIREMENTS:` |
| 3 | `····print(f"=== Case {case_index} ===")` |
| 4 | `····case_index += 1` |

`start=1` 表示编号从 `1` 开始。默认不写时从 `0` 开始。

| 写法 | 第一个序号 |
| --- | --- |
| `enumerate(items)` | `0` |
| `enumerate(items, start=1)` | `1` |

使用 `enumerate()` 的好处：

- 不需要自己维护 `case_index += 1`。
- 循环变量更少，代码更不容易写错。
- 读代码时能直接看出“这里既需要序号，也需要元素”。

## 66. 创建 Pydantic 对象：`RequirementAgentState(requirement=requirement)`

这一句来自 `run_agent_loop()`：

- `state = RequirementAgentState(requirement=requirement)`

它的作用是：创建一个 `RequirementAgentState` 对象，并保存到变量 `state`。

可以拆成三部分看：

| 片段 | 含义 |
| --- | --- |
| `RequirementAgentState(...)` | 调用类，创建一个对象。 |
| `requirement=requirement` | 把右边变量 `requirement` 的值，传给对象里的 `requirement` 字段。 |
| `state = ...` | 把创建出来的对象保存到变量 `state`。 |

这里左右两边都叫 `requirement`，但含义不同：

| 位置 | 含义 |
| --- | --- |
| 左边 `requirement=` | 字段名，表示要给对象的哪个字段赋值。 |
| 右边 `requirement` | 当前函数参数或变量，表示实际传进去的数据。 |

更直观的例子：

| 行号 | 代码 |
| --- | --- |
| 1 | `input_text = "做一个审批列表页"` |
| 2 | `state = RequirementAgentState(requirement=input_text)` |

创建完成后，可以用点号读取字段：

| 代码 | 含义 |
| --- | --- |
| `state.requirement` | 读取原始需求文本。 |
| `state.page_goal` | 读取页面目标，初始值是空字符串。 |
| `state.core_components` | 读取组件列表，初始值是空列表。 |
| `state.errors` | 读取错误列表，初始值是空列表。 |

为什么只传了 `requirement`，其他字段没有传？

因为 `RequirementAgentState` 里给其他字段设置了默认值：

| 字段 | 默认值 |
| --- | --- |
| `page_goal` | `""` |
| `core_components` | 空列表 |
| `state_requirements` | 空列表 |
| `risk_points` | 空列表 |
| `test_points` | 空列表 |
| `trace` | 空列表 |
| `errors` | 空列表 |

这也是 Agent Loop 里 `state` 的作用：

- 一开始只保存原始需求。
- 每一步执行后，把新的分析结果写回 `state`。
- 最后返回完整 `state`，里面包含最终结果和执行过程。

和 JavaScript / TypeScript 对比，接近于：

| Python | TypeScript 理解 |
| --- | --- |
| `state = RequirementAgentState(requirement=requirement)` | `const state = new RequirementAgentState({ requirement })` |
| `state.page_goal = "审批工作台"` | `state.pageGoal = "审批工作台"` |
| `state.core_components.append("DataTable")` | `state.coreComponents.push("DataTable")` |

注意：

- `RequirementAgentState` 继承了 Pydantic 的 `BaseModel`。
- 所以它不只是普通对象，还会按字段定义做基础校验。
- 如果必填字段缺失，Pydantic 会报错。
