# 文档结果 JSON 保存与加载

[document_storage.py](../scripts/document_storage.py) 提供统一读取、保存与加载函数。导出器使用必填的 `-o/--output` 指定目标文件，已有输出文件不覆盖。

## 命令行导出

在项目根目录运行，依赖使用根目录 requirements.txt：

```powershell
.\.venv\Scripts\python.exe -m scripts.document_storage "data/samples/policy-002/body.md" --output "data/processed/policy-002/body.json"
```

也可将 `--output` 写成 `-o`。输入路径是位置参数，输出路径是必填命名选项；不会自动选样本或默认覆盖文件。此接口替换开发期间的两个位置参数写法，`args.output_path` 名称保持不变。

由于使用 `scripts` 包内导入，导出命令使用 `python -m scripts.document_storage`。输入仍须为 `data/samples/<source_id>/` 下的项目相对路径；输出位置由调用方指定，建议放入已忽略的 `data/processed/`。

成功时 stdout 显示“已保存：”及目标路径，退出码为 0。失败时 stderr 显示输入路径和原因，退出码为 1；参数缺失或错误时 argparse 返回 2。`--help` 查看用法，返回 0。

导出器的主要结果是磁盘上的 JSON 文件，终端显示保存状态；各单独读取脚本的 stdout 则是结果 JSON，两者用途不同。

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
| read_document(path) | 按扩展名调用已有读取器，返回 metadata/records；支持 .pdf、.xlsx、.docx、.md、.markdown，扩展名不区分大小写 |
| save_document(result, output_path) | 先序列化，再创建父目录并以 x 模式写入 UTF-8 JSON；中文可读，缩进 2，末尾换行 |
| load_document(file_path) | 读取 UTF-8 JSON 并还原 Python 数据，不重新解析原始文档 |

三个函数都接受路径字符串或 Path。函数失败时向调用方抛出异常，不主动打印或退出；CLI 的 main 负责提示并返回退出码，入口使用 SystemExit(main())。

JSON 数据中的 null 会还原为 None。保存前先序列化，可以避免不可序列化对象导致新建的文件只写了一半；这不等同于磁盘写失败或断电情况下的原子保存保证。本轮只保存现有读取器产生的普通字典/列表/字符串等数据，不增加复杂对象的自定义编码。

统一入口仍沿用各读取器的限制，例如 PDF 空文字页保留、Word 顶层内容范围及合并网格重复；导出成功不代表全文解析完整。扫描页提示可在 PDF 专用命令中查看，统一导出器不额外推断解析完整性。

## 验证

新增 [test_document_storage.py](../tests/test_document_storage.py)，与既有读取器测试一起运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

覆盖中文/None 往返、父目录创建、已有输出保护、序列化失败不留目标文件、缺失/损坏 JSON、Markdown 扩展名别名，以及 -o/--output、缺参和读取/保存失败退出码。临时数据自动清理，不改原始政策。
