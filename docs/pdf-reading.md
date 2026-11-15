# PDF 逐页读取实验

本实验对应 [Issue #6](https://github.com/Zhang-QianBin/campus-policy-agent/issues/6)，使用 [pdf-reading.py](../scripts/pdf-reading.py) 读取单份本地 PDF，逐页提取文字并保留来源与页码，供后续检索开发使用。

当前结果保存在内存列表 `records` 中，并打印到终端；运行结束后不会另存结果文件。扫描件 OCR、表格结构重建和批量导出不在本次实验范围内。

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
.\.venv\Scripts\python.exe scripts/pdf-reading.py
```

当前脚本通过修改开头的 `pdf_path` 变量选择输入，不提供命令行参数。样本须遵循 `data/samples/policy-NNN/` 目录约定，正文与附件的原始来源见 [来源清单](sources.md)。

路径统一使用 `/`，并保持相对于项目根目录。开头不要加 `/`；相对路径按终端当前目录解析，而不是按 `scripts` 目录解析。

### 正常 PDF：默认样本

[电子信息学院 2024 级本科专业培养方案](../data/samples/policy-001/attachments/unpacked/2024级本科专业培养方案/03电子信息学院2024级本科专业培养方案.pdf)

```python
pdf_path = (
    "data/samples/policy-001/attachments/unpacked/"
    "2024级本科专业培养方案/"
    "03电子信息学院2024级本科专业培养方案.pdf"
)
```

### 扫描 PDF

[本科生奖学金评审办法](../data/samples/policy-005/attachments/关于印发《杭州电子科技大学本科生奖学金评审办法》的通知（杭电学〔2026〕79号）.pdf)

```python
pdf_path = (
    "data/samples/policy-005/attachments/"
    "关于印发《杭州电子科技大学本科生奖学金评审办法》的通知（杭电学〔2026〕79号）.pdf"
)
```

### 不存在的文件

使用以下路径验证缺失文件提示，不需要创建这个文件：

```python
pdf_path = "data/samples/policy-005/attachments/not-exist.pdf"
```

### 非 PDF 输入

将已有 [Excel 附件](../data/samples/policy-004/attachments/861caa12-fe0a-4409-b03b-73d359290176.xlsx) 交给 PDF 读取器，用于验证格式错误处理；这不是 Excel 正文解析功能。

```python
pdf_path = "data/samples/policy-004/attachments/861caa12-fe0a-4409-b03b-73d359290176.xlsx"
```

每次只选择一个输入，修改后重新运行同一条命令。完成失败场景验证后，将默认路径恢复为正常 PDF，便于其他成员直接运行。

## 输出字段

每页生成一条字典记录，包含以下字段；没有提取到文字的页也保留来源和页码。

| 字段 | 含义与取值规则 |
| --- | --- |
| `source_id` | 发布记录编号，从相对于 `data/samples` 的第一级目录取得，例如 `policy-001`。同一发布记录下的多个附件共享此编号。 |
| `title` | PDF 文件名去掉扩展名，使用 `Path(pdf_path).stem`；这是当前标题回退规则，不是从 PDF 内识别的正式标题。 |
| `file_path` | 输入文件相对于项目根目录的路径，用于区分同一发布记录下的多个附件。 |
| `page` | 从 1 开始的 PDF 文件页码，未按纸面印刷页码重新编号。 |
| `text` | 本页提取的文字，去除首尾空白；未提取到有效文字时为 `""`。 |

终端逐页展示这五项，并补充字符数。空文字页显示“未提取到有效文字，请人工核对原 PDF。”

`text` 非空仅表示提取到了部分文字，不代表该页或整份文件已完整解析；脚本目前不会自动判断少量文字是否覆盖全文。

## 本地验证记录

以下为 2026-11-15 的本地实验结果，供评审者复现对照；尚未替代同伴在独立环境中的验收。

| 场景 | 已观察结果 | 核对重点 |
| --- | --- | --- |
| 正常培养方案 PDF | 共 37 页，能够逐页提取文字。第 19 页有专业选修课程与“专业选修至少修读10个学分”的条文。 | 来源编号为 `policy-001`；文件路径对应具体 PDF；抽查第 19 页文字与原件一致。 |
| 奖学金扫描 PDF | 共 7 页，前 6 页均为 0 字符并提示人工核对，第 7 页提取到 147 个字符。 | 来源编号为 `policy-005`；空文字页仍有记录；第 7 页的少量文字不能代表全文。 |
| 不存在的路径 | 显示“文件不存在:”和输入路径，随后以状态码 1 退出。 | 进入 `FileNotFoundError` 处理分支，不继续读取页面。 |
| Excel 输入 | 显示“无法读取 PDF 文件:”、路径和具体失败原因，随后以状态码 1 退出。 | 进入 `PdfReadError` 处理分支；实验中原因包含 `Stream has ended unexpectedly`。 |

非 PDF 输入时，pypdf 还可能先输出 `invalid pdf header` 或 `EOF marker not found` 等诊断日志。库日志和脚本自定义提示会同时出现，不能仅凭日志仍在输出就判断异常未被捕获。

## 已知限制

- pypdf 提取已有文字信息，不执行 OCR。奖学金扫描件前 6 页的可见文字存储在图像中；第 7 页同时有图像和少量可提取文字。因此当前无法用该脚本获得完整奖学金正文。
- 培养方案的表格存在断行、列顺序和数字粘连问题。当前保留文字及页码，未重建表格结构，涉及课程、学分等内容时仍需核对原件。
- 当前异常处理覆盖读取过程中的 `FileNotFoundError` 与 `PdfReadError`。非 PDF 输入不等于穷尽所有损坏 PDF；其他系统或输入错误尚未全面验证。
- 来源编号依赖现有样本目录结构，当前未支持任意外部路径或从文件内容识别来源编号。
- 尚未实现结果持久化、批量导出或检索问答；扫描件未识别的部分不能作为已成功解析的知识库正文。

## 同伴复现

1. 获取包含本脚本与样本的分支，在自己的机器上按环境准备步骤配置依赖。
2. 从项目根目录运行默认样本，检查五个字段，并对照原件核对第 19 页。
3. 依次切换扫描件、不存在的路径和 Excel 输入，对照上表记录实际结果。
4. 在 PR 中说明环境、运行命令、核对结果及差异。公共依赖配置与工程初始化任务协调维护，复现完成后恢复默认样本。

实验通过 PR 关联 Issue #6 交付；是否完成验收以实际复现和评审结果为准。
