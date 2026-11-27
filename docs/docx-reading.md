# Word 政策附件读取

[docx_reading.py](../scripts/docx_reading.py) 提供 `read_docx(file_path)` 和命令行入口，读取 `.docx` 的顶层正文段落与表格单元格，返回记录列表。已登记样本的来源信息由 [统一读取入口](document-storage.md) 添加。

## 环境与依赖

使用 Python 3.12.10、python-docx 1.2.0。在项目根目录安装依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

包名为 `python-docx`，导入名称为 `docx`。只支持 `.docx`；旧版 `.doc` 需要另行转换，不能仅修改扩展名。转换时保留原始文件及其来源。

## 命令行与函数调用

当前语料没有真实 Word 政策附件。独立读取器接受实际存在的 DOCX 文件路径，支持相对路径和绝对路径。运行示例时替换为实际文件。

```powershell
.\.venv\Scripts\python.exe scripts/docx_reading.py "data/samples/policy-001/attachments/example.docx"
```

在项目根目录启动 Python 后也可以直接调用：

```python
from scripts.docx_reading import read_docx

# 替换为实际存在的 DOCX。
records = read_docx("data/samples/policy-001/attachments/example.docx")
print(records[0])
```

只导入模块不会读取文件或打印。函数抛出异常，由调用方处理。CLI 使用必填路径参数，成功向 stdout 输出 JSON 数组，失败向 stderr 显示路径及原因。

| 调用情况 | CLI 退出码 |
| --- | --- |
| 成功读取有效文字 | 0 |
| 缺少路径参数 | 2 |
| --help 显示帮助 | 0 |
| 文件不存在、不支持格式、损坏或未读取到有效文字 | 1 |

`Document(stream)` 在 with 文件上下文内加载文档，随后自动关闭输入文件流；后续遍历已加载的内容，不保存或覆盖原文件。

## 返回字段与位置

每条记录包含 `type`、`text` 和 `location`。

| 字段 | 规则 |
| --- | --- |
| type | paragraph 表示正文段落，table_cell 表示表格单元格 |
| text | 去除首尾空白后的文字；空白记录跳过，内部换行保留 |
| location.block | 在顶层段落与表格序列中的位置，从 1 开始，空白块仍占位置 |
| location.table | 仅表格记录有此字段，顶层表格序号，从 1 开始 |
| location.row | 仅表格记录有此字段，行号，从 1 开始 |
| location.column | 仅表格记录有此字段，表格网格列号，从 1 开始 |

一个段落、一个表格、再一个段落的块位置依次为 1、2、3。表格内的单元格共享 `location.block=2`，并通过行列进一步定位。

## 已知限制

- 按 `iter_inner_content()` 的顶层顺序读取段落和表格，不会把所有段落与所有表格分开后再拼接。
- 表格按 python-docx 提供的网格单元格读取。合并单元格可能在多个网格位置重复相同文字；本轮不去重或恢复 merged_range，不能将重复成员当成独立政策条款。
- 当前不遍历嵌套表格，不读取页眉页脚、文本框、批注、图片或嵌入附件，不执行 OCR；不宣称覆盖 Word 中全部可见内容。
- 保留文字与位置，不还原颜色、字体等排版含义，不计算政策适用条件或生成结论。
- 文档有图片或其他内容但提取不到文字时，也会按“未读取到有效文字”失败，不能据此断言原文为空。

## 验证方法

当前使用临时构造的 DOCX 测试顶层段落、段落间的表格、中文和单元格换行、合并单元格的网格输出、只有表格的文档、空文档、旧格式、无效 ZIP、函数调用及 CLI。测试结束后自动清理临时文件；这些不属于真实政策语料，也不替代真实 Word 附件验收。

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

后续取得真实附件后，需对照原文抽查段落与表格，记录遗漏的内容类型；确认原文件未改变，再将实际结果写入 PR。

API 依据：[python-docx 文档对象](https://python-docx.readthedocs.io/en/latest/api/document.html)、[表格对象](https://python-docx.readthedocs.io/en/latest/api/table.html)。
