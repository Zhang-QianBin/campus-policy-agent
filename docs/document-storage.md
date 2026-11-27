# 文档结果 JSON 保存与加载

[document_storage.py](../scripts/document_storage.py) 提供统一命令行，以及读取、保存和加载函数。

## 命令行

在项目根目录运行。依赖见根目录的 `requirements.txt`。

```powershell
.\.venv\Scripts\python.exe -m scripts.document_storage "data/samples/policy-002/body.md" --print
.\.venv\Scripts\python.exe -m scripts.document_storage "data/samples/policy-002/body.md" --output "data/processed/policy-002/body.json"
```

输入必须已登记且允许解析，可传相对路径或绝对路径。相对路径以当前工作目录为基准。`--print` 和 `-o/--output` 二选一。

| 模式 | 标准输出（stdout） |
| --- | --- |
| `--print` | 一份 UTF-8 JSON，包含元数据、记录、状态和告警 |
| `-o/--output` | 显示“已保存”及目标路径。完整 JSON 写入指定的新文件，已有文件受覆盖保护 |

两种模式的 JSON 结构相同。可读的告警文字写到标准错误流（stderr），告警详情也在 JSON 的 `warnings` 中。

| 退出码 | 含义 |
| --- | --- |
| `0` | 打印或保存成功，结果可以是 `ok`、`partial` 或 `empty`。显示帮助也返回 `0` |
| `1` | 读取或输出失败，stderr 显示路径和原因 |
| `2` | 参数用法错误，例如缺少输出选项或同时选择打印和保存 |

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

测试覆盖打印与保存的 JSON 一致性、参数互斥、覆盖保护、三种状态、缺失与损坏文件。扫描 PDF 的集成测试分别打印和保存结果，核对 7 条页记录、JSON 中的 6 条告警，以及 stderr 上的对应提示。临时数据在测试结束后清理。
