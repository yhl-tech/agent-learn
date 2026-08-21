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
