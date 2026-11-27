# PDF 逐页读取实验

本实验最初由 [Issue #6](https://github.com/Zhang-QianBin/campus-policy-agent/issues/6) 实现，并在 [#11](https://github.com/Zhang-QianBin/campus-policy-agent/issues/11) 中封装函数与命令行入口。使用 [pdf_reading.py](../scripts/pdf_reading.py) 读取单份本地 PDF，逐页提取文字并保留页码。

调用 `read_pdf(file_path)` 可获取记录列表，命令行会将列表输出为 JSON 数组。已登记样本的来源信息与 JSON 保存见 [统一读取与导出](document-storage.md)。扫描件 OCR、表格结构重建和批量导出留待后续任务。

## 环境准备

- 验证平台：Windows，PowerShell。
- Python：3.12.10。
- PDF 读取库：pypdf 7.1.0。

先安装 Python 3.12.10，在项目根目录执行以下命令。已有 `.venv` 时直接使用现有环境，不必重复创建。

```powershell
py -3.12 --version
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install pypdf==7.1.0
```

核对实际运行环境：

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import pypdf; print(pypdf.__version__)"
```

预期分别显示 `Python 3.12.10` 和 `7.1.0`。直接指定虚拟环境内的解释器即可运行；`.venv` 已被 Git 忽略，成员应在自己的机器上创建环境。

## 运行与输入

在项目根目录运行：

```powershell
.\.venv\Scripts\python.exe scripts/pdf_reading.py "data/samples/policy-001/attachments/unpacked/2024级本科专业培养方案/03电子信息学院2024级本科专业培养方案.pdf"
```

文件路径是必填参数，支持相对路径和绝对路径。相对路径按终端当前目录解析。已登记样本的发布页面和附件来源见 [来源清单](sources.md)。

成功时退出码为 `0`，stdout 输出一个 JSON 数组（中文可读，缩进 2）。空文字页保留记录，提示写入 stderr。读取失败时，`main()` 显示输入路径及具体原因，退出码为 `1`，stdout 为空。未提供路径时 argparse 显示用法，退出码为 `2`。

四种读取脚本统一采用 `main()` 成功返回 0、读取失败返回 1，文件入口使用 `raise SystemExit(main())` 将返回值交给操作系统。读取函数只返回数据或抛出异常，不主动结束进程。

查看帮助和退出码：

```powershell
.\.venv\Scripts\python.exe scripts/pdf_reading.py --help
$LASTEXITCODE
```

`$LASTEXITCODE` 应在待检查的运行命令之后查看。`--help` 成功显示帮助时为 `0`。

### 正常 PDF

[电子信息学院 2024 级本科专业培养方案](../data/samples/policy-001/attachments/unpacked/2024级本科专业培养方案/03电子信息学院2024级本科专业培养方案.pdf)

```powershell
.\.venv\Scripts\python.exe scripts/pdf_reading.py "data/samples/policy-001/attachments/unpacked/2024级本科专业培养方案/03电子信息学院2024级本科专业培养方案.pdf"
```

### 扫描 PDF

[本科生奖学金评审办法](../data/samples/policy-005/attachments/关于印发《杭州电子科技大学本科生奖学金评审办法》的通知（杭电学〔2026〕79号）.pdf)

```powershell
.\.venv\Scripts\python.exe scripts/pdf_reading.py "data/samples/policy-005/attachments/关于印发《杭州电子科技大学本科生奖学金评审办法》的通知（杭电学〔2026〕79号）.pdf"
```

### 不存在的文件

使用以下路径验证缺失文件提示，不需要创建这个文件：

```powershell
.\.venv\Scripts\python.exe scripts/pdf_reading.py "data/samples/policy-005/attachments/not-exist.pdf"
```

### 非 PDF 输入

将已有 [Excel 附件](../data/samples/policy-004/attachments/861caa12-fe0a-4409-b03b-73d359290176.xlsx) 交给 PDF 读取器，用于验证格式错误处理；这不是 Excel 正文解析功能。

```powershell
.\.venv\Scripts\python.exe scripts/pdf_reading.py "data/samples/policy-004/attachments/861caa12-fe0a-4409-b03b-73d359290176.xlsx"
```

### 在其他代码中调用

在项目根目录启动 Python，或从项目根目录运行调用代码：

```python
from scripts.pdf_reading import read_pdf

records = read_pdf(
    "data/samples/policy-001/attachments/unpacked/"
    "2024级本科专业培养方案/03电子信息学院2024级本科专业培养方案.pdf"
)
print(len(records))                     # 当前样本为 37
print(records[18]["location"]["page"])  # 第 19 页，列表索引为 18
print(records[18]["text"][:200])
```

`read_pdf(file_path)` 接收路径字符串或 `Path`，返回逐页记录列表。只导入模块不会读取文件、打印结果或退出进程。函数失败时抛出异常，由调用方处理。pypdf 可能输出诊断日志。函数通过 `finally` 关闭已成功创建的 `reader`。

检查调用失败时，可由自己的代码捕获异常：

```python
from scripts.pdf_reading import read_pdf

try:
    read_pdf("data/samples/policy-005/attachments/not-exist.pdf")
except FileNotFoundError as error:
    print("已捕获文件不存在异常：", error)
```

直接调用函数时，空文字页保留为 `text=""`，不会自动显示人工核对提示；调用方可按需检查。命令行入口 `main()` 则会逐页输出该提示。Excel 的函数调用方式见 [excel-reading.md](excel-reading.md)。

## 输出字段

记录列表按 PDF 文件页顺序排列。下面的示例展示第一页。

```python
[
    {"type": "page", "text": "本页实际提取的文字", "location": {"page": 1}},
]
```

| 字段 | 含义与取值规则 |
| --- | --- |
| `type` | 固定为 `page` |
| `text` | 本页提取的文字，去除首尾空白。未提取到有效文字时为 `""` |
| `location.page` | 从 1 开始的 PDF 文件页码 |

空文字页也追加记录，页码连续保留。命令行中会提示“第 N 页未提取到文字，请人工核对原 PDF。”；字符数可由调用方使用 `len(record["text"])` 获取，不作为返回字段。

`text` 非空仅表示提取到了部分文字，不代表该页或整份文件已完整解析；脚本目前不会自动判断少量文字是否覆盖全文。

## 本地验证记录

以下为 2026-11-15 的本地实验结果。记录结构和来源字段以本页当前调用示例及统一读取说明为准。

| 场景 | 已观察结果 | 核对重点 |
| --- | --- | --- |
| 导入及函数调用 | 导入无业务输出；函数返回 metadata/records，连续读取两个样本各自独立。 | 直接使用返回值，不需要解析终端文字。 |
| 正常培养方案 PDF | 共 37 页，能够逐页提取文字。第 19 页有专业选修课程与“专业选修至少修读10个学分”的条文。 | 来源编号为 `policy-001`；文件路径对应具体 PDF；抽查第 19 页文字与原件一致。 |
| 奖学金扫描 PDF | 共 7 页，前 6 页均为 0 字符并提示人工核对，第 7 页提取到 147 个字符。 | 来源编号为 `policy-005`；空文字页仍有记录；第 7 页的少量文字不能代表全文。 |
| 不存在的路径 | 函数抛出 FileNotFoundError；CLI 显示“无法读取 PDF 文件：”及路径、“错误信息：”及原因，退出码为 1，stdout 为空。 | 不再因 reader 尚未创建而产生 UnboundLocalError。 |
| Excel 输入 | 函数抛出 PdfReadError；CLI 显示路径及具体原因，退出码为 1，stdout 为空。 | pypdf 可能同时输出诊断日志；不宣称覆盖全部损坏形式。 |
| 缺少参数 / 帮助 | 无参数退出码为 2；--help 显示帮助，退出码为 0。 | 不再使用内置默认样本。 |
| 资源清理 | 使用模拟读取器验证正常与中途提取异常两条路径均调用 close。 | 仅对成功创建的 reader 执行关闭。 |

非 PDF 输入时，pypdf 还可能先输出 `invalid pdf header` 或 `EOF marker not found` 等诊断日志。库日志和脚本自定义提示会同时出现，不能仅凭日志仍在输出就判断异常未被捕获。

## 已知限制

- pypdf 提取已有文字信息，不执行 OCR。奖学金扫描件前 6 页的可见文字存储在图像中；第 7 页同时有图像和少量可提取文字。因此当前无法用该脚本获得完整奖学金正文。
- 培养方案的表格存在断行、列顺序和数字粘连问题。当前保留文字及页码，未重建表格结构，涉及课程、学分等内容时仍需核对原件。
- 函数保留原始读取异常，当前 CLI 使用较宽的 `except Exception` 显示错误并退出；这不能替代对不同错误原因的定位，其他系统或输入错误尚未全面验证。
- 统一入口支持单份已登记样本的 JSON 导出。批量导出和检索问答在后续任务实现。扫描件未提取到文字的部分不能作为知识库证据。
- CLI 退出码 0 表示完成逐页提取流程，不代表全文完整；即使存在空文字页仍会返回记录并提示。`if not records` 只表示没有页记录，不能用它判断全文是否有文字。

## 同伴复现

1. 获取包含本脚本与样本的分支，在自己的机器上按环境准备步骤配置依赖。
2. 导入 `read_pdf`，调用正常样本，检查记录列表并对照原件核对 `location.page` 为 19 的记录。
3. 按命令行示例运行正常 PDF、扫描件、不存在的路径和 Excel 输入，对照上表检查 JSON、stderr 提示及退出码。
4. 在 PR 中说明环境、运行命令、核对结果及差异。公共依赖配置与工程初始化任务协调维护，不提交临时文件或虚拟环境。

原始读取实验由 #6 / PR #8 交付；本次函数封装与 Excel 一起通过 PR 关联 #11。上述本地验证不代替同伴复现，是否完成验收以实际评审结果为准。
