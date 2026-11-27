# Markdown 政策正文读取

[markdown_reading.py](../scripts/markdown_reading.py) 提供 `read_markdown(file_path)`。正文按整份文件保存为一条记录，读取器返回记录列表。命令行输出包含发布标题、来源编号和正文记录。[统一读取与导出](document-storage.md)

## 环境与运行

从项目根目录运行，使用 Python 3.12.10。Markdown 本身只使用标准库；整个项目的依赖可统一安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.document_storage "data/samples/policy-002/body.md" --print
```

命令行接受已登记文件的相对或绝对路径。`--print` 打印完整 JSON，`-o` 可将结果写入文件。PowerShell 中用 `$LASTEXITCODE` 查看退出码。[命令行用法](document-storage.md#命令行)

## 函数调用

在项目根目录运行 `.\.venv\Scripts\python.exe`，进入 Python 交互环境后输入：

```python
from scripts.markdown_reading import read_markdown

records = read_markdown("data/samples/policy-002/body.md")
print(len(records))  # 正文输出 1 条记录
print(records[0]["text"])
```

只导入不会读取文件、打印或退出进程。函数失败时抛出异常，由调用方处理；输入 `exit()` 可返回 PowerShell。

## 返回结构与规则

| 字段 | 规则 |
| --- | --- |
| `type` | 固定为 `body` |
| `text` | 完整正文，去除全文首尾空白，保留内部段落、换行及缩进 |
| `location` | 正文整份读取，使用空字典 `{}` |

支持 `.md`、`.markdown`，不区分扩展名大小写。按 UTF-8 读取并兼容 UTF-8 BOM，文件读取后自动关闭。

## 验证与失败场景

- 真实样本的 `text` 保留通知正文及其中的标题行。[policy-002/body.md](../data/samples/policy-002/body.md)
- 直接调用函数读取不存在的文件会抛出 `FileNotFoundError`。用命令行传入未登记路径时，stderr 显示清单错误，退出码为 `1`。
- 空文件或只有空白时，函数返回 `[]`。统一命令可为已登记的空文件输出 `empty` 及告警。
- 非 UTF-8 内容：函数抛出 UnicodeDecodeError，不使用忽略错误的方式丢弃字节。
- 不支持的扩展名：函数抛出 ValueError，不将 PDF 或 Excel 当作 Markdown 读取。

自动验证使用标准库 unittest，包含中文与 BOM、段落保留、空内容、编码错误、重复调用、命令行参数和失败场景：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试临时文件自动清理，不改原始政策。当前不检查网页来源是否更新，不提取图片里的文字，也不从正文自动推断适用对象或政策有效性。来源信息见 [sources.md](sources.md)。
