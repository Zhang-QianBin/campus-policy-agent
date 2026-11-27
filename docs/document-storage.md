# 文档结果 JSON 保存与加载

[document_storage.py](../scripts/document_storage.py) 提供统一读取、保存与加载函数。导出器使用必填的 `-o/--output` 指定目标文件，已有输出文件不覆盖。

## 命令行导出

在项目根目录运行，依赖使用根目录 requirements.txt：

```powershell
.\.venv\Scripts\python.exe -m scripts.document_storage "data/samples/policy-002/body.md" --output "data/processed/policy-002/body.json"
```

也可将 `--output` 写成 `-o`。输入路径是位置参数，输出路径是必填命名选项；不会自动选样本或默认覆盖文件。此接口替换开发期间的两个位置参数写法，`args.output_path` 名称保持不变。

导出命令使用 `python -m scripts.document_storage`。输入必须已登记且允许解析，可传相对路径或绝对路径。相对输入路径以当前工作目录为基准。输出位置由调用方指定，建议放入已忽略的 `data/processed/`。

写入 `ok`、`partial` 或 `empty` 的结果后，stdout 显示“已保存：”及目标路径，退出码为 0。读取或保存失败时，stderr 显示输入路径和原因，退出码为 1。参数缺失或错误时 argparse 返回 2。`--help` 查看用法，返回 0。

导出器将元数据、记录、提取状态和告警写入 JSON 文件。四个独立读取脚本在成功时将记录列表直接输出为 JSON 数组。

## 函数调用

在项目根目录启动 Python 后：

```python
from scripts.document_storage import read_document, save_document, load_document

result = read_document("data/samples/policy-002/body.md")
save_document(result, "data/processed/policy-002/body.json")
loaded = load_document("data/processed/policy-002/body.json")
print(loaded == result)  # 预期 True
```

函数示例和命令行示例使用相同输出路径，选择一种执行即可。再次保存到已有路径会抛出 FileExistsError；可换新输出文件名，删除已有结果应由使用者明确决定。

| 函数 | 行为 |
| --- | --- |
| `read_document(path, sources=None, samples_dir=SAMPLES_DIR)` | 按完整路径查询清单，再按扩展名调用读取器，返回 `metadata`、`records`、`status` 和 `warnings`。支持 `.pdf`、`.xlsx`、`.docx`、`.md`、`.markdown`，扩展名不区分大小写 |
| save_document(result, output_path) | 先序列化，再创建父目录并以 x 模式写入 UTF-8 JSON；中文可读，缩进 2，末尾换行 |
| load_document(file_path) | 读取 UTF-8 JSON 并还原 Python 数据，不重新解析原始文档 |

三个函数都接受路径字符串或 Path。函数失败时向调用方抛出异常，不主动打印或退出；CLI 的 main 负责提示并返回退出码，入口使用 SystemExit(main())。

默认使用项目的 `data/samples/sources.json`。调用方可通过 `sources` 传入已加载的清单，使用自定义样本根目录时同时传入 `samples_dir`。未登记的路径抛出 `LookupError`。登记为 `parse: false` 的文件在进入读取器前抛出 `ValueError`，已登记且允许解析的未知扩展名也会抛出带格式提示的 `ValueError`。

## 结果结构

| `metadata` 字段 | 规则 |
| --- | --- |
| `source_id` | 来源清单中的发布记录编号 |
| `title` | 正文使用清单的发布标题，附件使用去掉扩展名的文件名 |
| `file_path` | 相对样本根目录的路径，使用 `/` 分隔，例如 `policy-002/body.md` |
| `format` | `markdown`、`pdf`、`xlsx` 或 `docx` |
| `schema_version` | 文档结果结构版本，当前为整数 `2`，独立于来源清单的版本 |

`records` 是读取器返回的列表，每条记录由 `type`、`text` 和 `location` 组成。Markdown 正文的 `location` 为 `{}`，PDF 页码、Excel 单元格及 DOCX 段落或表格位置均放在 `location` 内。

| `status` | 判定 |
| --- | --- |
| `ok` | 提取到文字，`warnings` 为 `[]` |
| `partial` | 提取到文字，同时存在告警，例如 PDF 有空文字页或 Excel 有公式缺少缓存值 |
| `empty` | 文件可正常读取，但完全未提取到文字。全空文字 PDF 仍保留页记录 |

`warnings` 是告警列表。每一条包含供程序识别的 `code`、供人查看的 `message` 和可定位的 `location`。文件缺失、损坏、编码或格式错误由读取入口抛出异常。

| `code` | 含义 | `location` |
| --- | --- | --- |
| `empty_page` | PDF 页未提取到文字，保留该页记录 | `page` |
| `missing_formula_cache` | Excel 公式缺少保存的计算值，该单元格无内容记录 | `sheet`、`cell` |
| `empty_document` | 文件没有可用文字，且没有更具体的告警 | `{}` |

JSON 数据中的 null 会还原为 None。保存前先序列化，可以避免不可序列化对象导致新建的文件只写了一半；这不等同于磁盘写失败或断电情况下的原子保存保证。本轮只保存现有读取器产生的普通字典/列表/字符串等数据，不增加复杂对象的自定义编码。

版本 1 的旧 JSON 可以按原结构加载。需要状态和告警时，可将原文重新导出到新路径。

`status` 描述这一次提取到的文字。扫描件的空文字页可以用告警中的页码回到原 PDF 核对。DOCX 的提取范围见 [Word 读取说明](docx-reading.md)。

## 验证

运行存储与读取器测试。[test_document_storage.py](../tests/test_document_storage.py)

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试覆盖三种状态、空文字页和缺失公式缓存的告警位置、清单匹配、正文及附件标题、文件读取异常和 JSON 保存与加载。扫描 PDF 的集成测试调用统一导出命令，读回 JSON 后核对 7 条页记录和前 6 页的告警。临时数据在测试结束后清理。
