# Markdown 政策正文读取

[markdown_reading.py](../scripts/markdown_reading.py) 提供 `read_markdown(file_path)` 和命令行入口。正文按整份文件保存为一条记录，读取器返回记录列表。带发布标题和来源编号的读取结果见 [统一读取与导出](document-storage.md)。

## 环境与运行

从项目根目录运行，使用 Python 3.12.10。Markdown 本身只使用标准库；整个项目的依赖可统一安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/markdown_reading.py "data/samples/policy-002/body.md"
```

路径是必填参数，支持绝对路径和相对路径。相对路径以当前工作目录为基准。使用 `--help` 查看帮助，缺少路径时退出码为 `2`。

成功时 stdout 输出 JSON 数组，退出码为 `0`。读取失败时 stdout 为空，stderr 显示路径和具体原因，退出码为 `1`。PowerShell 中在运行后用 `$LASTEXITCODE` 查看退出码。

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
- 不存在路径：传入 `data/samples/policy-002/not-exist.md`，函数抛出 FileNotFoundError，CLI 提示后以 1 退出。
- 空文件或只有空白：函数抛出 ValueError，不产生伪造的成功正文。
- 非 UTF-8 内容：函数抛出 UnicodeDecodeError，不使用忽略错误的方式丢弃字节。
- 不支持的扩展名：函数抛出 ValueError，不将 PDF 或 Excel 当作 Markdown 读取。

自动验证使用标准库 unittest，包含中文与 BOM、段落保留、空内容、编码错误、重复调用、命令行参数和失败场景：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

测试临时文件自动清理，不改原始政策。当前不检查网页来源是否更新，不提取图片里的文字，也不从正文自动推断适用对象或政策有效性。来源信息见 [sources.md](sources.md)。
