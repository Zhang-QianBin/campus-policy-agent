# Excel 政策附件读取实验

本实验最初由 Issue [#9](https://github.com/Zhang-QianBin/campus-policy-agent/issues/9) 实现，并在 [#11](https://github.com/Zhang-QianBin/campus-policy-agent/issues/11) 中封装函数与命令行入口。使用 openpyxl 读取本地 Excel 政策附件，保留有效单元格的文字、工作表、坐标和合并范围。

脚本入口：[scripts/excel_reading.py](../scripts/excel_reading.py)。支持函数调用和命令行传参，不设置默认样本路径，不写入数据库或修改原始附件。

## 环境与依赖

已验证环境：Windows、Python 3.12.10、openpyxl 3.1.5。

在项目根目录打开 PowerShell。如果尚未创建虚拟环境，先执行：

```powershell
py -3.12 -m venv .venv
```

安装本实验所需依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install openpyxl==3.1.5
```

`argparse`、`json`、`sys`、`pathlib` 和 `zipfile` 为 Python 标准库，无需另外安装。本说明仅列出本实验依赖，公共依赖配置由工程初始化任务统一维护。

## 运行方式

在项目根目录执行，并传入文件路径；包含空格的路径需要加引号：

```powershell
.\.venv\Scripts\python.exe scripts/excel_reading.py "data/samples/policy-003/attachments/2026级本科生普通类转专业（类）转入实施细则.xlsx"
```

查看退出码：

```powershell
$LASTEXITCODE
```

成功时退出码为 `0`，标准输出（stdout）为记录组成的 JSON 数组。公式缺少缓存值的告警写到标准错误（stderr）。读取失败或没有可用记录时，stderr 显示原因，退出码为 `1`，stdout 为空。

路径是必填参数，省略时 argparse 显示用法并以 `2` 退出。查看帮助：

```powershell
.\.venv\Scripts\python.exe scripts/excel_reading.py --help
```

脚本接受相对路径和绝对路径。相对路径以当前工作目录为基准。已登记样本的文件级来源信息可通过 [统一读取入口](document-storage.md) 获取。

### 样本一：policy-003

[2026级本科生普通类转专业（类）转入实施细则.xlsx](../data/samples/policy-003/attachments/2026级本科生普通类转专业（类）转入实施细则.xlsx)

```powershell
.\.venv\Scripts\python.exe scripts/excel_reading.py "data/samples/policy-003/attachments/2026级本科生普通类转专业（类）转入实施细则.xlsx"
```

### 样本二：policy-004

[卓越学院及复合型双学位选拔细则附件](../data/samples/policy-004/attachments/861caa12-fe0a-4409-b03b-73d359290176.xlsx)

```powershell
.\.venv\Scripts\python.exe scripts/excel_reading.py "data/samples/policy-004/attachments/861caa12-fe0a-4409-b03b-73d359290176.xlsx"
```

发布页面及附件来源见 [sources.md](sources.md)。

### 在其他代码中调用

从项目根目录启动的 Python 代码可以这样调用：

```python
from scripts.excel_reading import read_excel

records = read_excel(
    "data/samples/policy-004/attachments/861caa12-fe0a-4409-b03b-73d359290176.xlsx"
)
print(len(records))
```

`read_excel(file_path)` 接收路径字符串或 `Path`，返回记录列表。工作簿可读但没有有效单元格时返回 `[]`。导入模块时不会读取文件或打印结果。读取失败时向调用方抛出异常。命令行入口 `main()` 负责接收参数、输出 JSON、显示错误及设置退出码。

四种读取脚本统一采用 `main()` 成功返回 0、读取失败返回 1，文件入口使用 `raise SystemExit(main())`。Excel 的 CLI 统一显示“无法读取 Excel 文件：”及路径，再显示“错误信息：”及具体原因；函数原始异常类型保持不变。

在项目根目录执行 `.\.venv\Scripts\python.exe` 可进入 Python 交互环境，再逐行输入上面的导入和调用示例。预期记录数为 `52`，可用 `records[0]` 核对第一条记录。输入 `exit()` 返回 PowerShell。PDF 的对应示例见 [pdf-reading.md](pdf-reading.md)。

## 输出结构

每份文件输出单元格记录列表。下面展示 policy-004 的第一条记录。

```json
[
  {
    "type": "cell",
    "text": "2026级卓越学院校内选拔细则和复合型双学位校内选拔细则",
    "location": {
      "sheet": "Sheet2",
      "cell": "A1",
      "merged_range": "A1:E1"
    }
  }
]
```

| 字段 | 含义 |
| --- | --- |
| `type` | 固定为 `cell` |
| `text` | 单元格值转为字符串并去除首尾空白后的内容 |
| `location.sheet` | 工作表名称 |
| `location.cell` | 单元格坐标，例如 `A1` |
| `location.merged_range` | 所属合并区域，例如 `A1:E1`，未合并时为 Python 的 `None` 或 JSON 的 `null` |

## 读取与清理规则

- 遍历工作簿中的所有工作表，再逐行、逐格读取。
- 公式单元格使用工作簿中已保存的计算值，例如 `=1+1` 保存的结果为 `2` 时，记录文字为 `"2"`。应用直接读取缓存，计算由保存工作簿的表格软件完成。
- 跳过值为 `None` 的单元格，以及清理首尾空白后为空的单元格；数字 `0` 保留为字符串 `"0"`。
- 合并区域只记录实际保存值的左上角单元格，并附上完整合并范围，不向其余单元格重复填充文字。
- 保留原文内容，不根据表格位置自行推断适用对象，也不补充原文未写出的选拔条件。
- 读取完成或中途发生异常时，关闭已成功打开的工作簿。

遇到缺少保存值的公式时跳过该单元格，告警会指出工作表和单元格坐标。需要同时取得记录和告警时，可以调用 `read_excel_with_warnings(path)` 得到 `(records, warnings)`。统一入口会将告警写入结果 JSON。[统一读取结果说明](document-storage.md#结果结构)

## 失败场景与复现方法

将待测文件路径作为命令参数传入。可以将临时文件保存在样本库之外。

| 场景 | 复现方法 | 预期结果 |
| --- | --- | --- |
| 未提供路径 | 直接运行脚本，不加路径参数 | argparse 提示缺少参数，退出码为 `2` |
| 文件不存在 | 将路径改为该目录下不存在的 `not-exist.xlsx` | 函数抛出 `FileNotFoundError`；CLI 提示无法读取、路径及具体原因，退出码为 `1` |
| 格式不支持 | 将路径改为项目中真实存在的 PDF | 函数抛出 `InvalidFileException`；CLI 提示无法读取、路径及具体原因，退出码为 `1` |
| 内容不是有效 ZIP 包 | 创建普通文本文件，将完整文件名改为 `invalid.xlsx` 后作为输入 | 函数抛出 `BadZipFile`；CLI 提示无法读取、路径及具体原因，退出码为 `1` |
| 工作簿为空 | 用 Excel 新建并保存一份不含内容的 `.xlsx`，作为输入 | 提示“工作簿中未读取到有效文字”，退出码为 `1` |
| 只有空白字符 | 在新建工作簿的某格输入几个空格并保存，作为输入 | 不生成空文字记录，提示没有有效文字，退出码为 `1` |
| 数字为 0 | 在临时工作簿的 `A1` 输入数字 `0`，作为输入 | 输出 `"text": "0"`，退出码为 `0` |

将文本文件改成 `.xlsx` 只用于构造无效输入，并不会把它转换成真正的 Excel 文件。`BadZipFile` 仅覆盖部分无效或损坏情况；缺少必要文件、XML 损坏等问题仍可能抛出其他异常。

## 本地验证记录

验证日期：2026-11-15。以下为当前样本与脚本的本地结果，尚不代表同伴已复现或 Issue 已验收。

| 检查项 | 结果 |
| --- | --- |
| policy-003 | 正常运行，输出 540 条记录，文字均非空 |
| policy-004 | 正常运行，输出 52 条记录，文字均非空 |
| 函数调用与导入 | 导入无读取和打印副作用；连续调用两个样本返回各自结果 |
| 命令行参数 | 两个样本路径均可直接传入；无路径退出码为 `2`，`--help` 退出码为 `0` |
| policy-004 合并范围 | `Sheet2!A1` 为 `A1:E1`，`Sheet2!A6` 为 `null`；已核对全部记录的范围及位置无重复 |
| 缺失文件、PDF 输入 | 核对对应分支，退出码均为 `1` |
| 无效 ZIP 内容、空表、纯空白 | 使用内存构造输入验证脚本分支，均显示提示并以 `1` 退出；磁盘文件的人工复现方法见上表 |
| 数字 0 | 使用内存工作簿验证，保留为 `"0"`，退出码为 `0` |
| 原始附件 | 两份 Excel 在本轮验证前后的 SHA256 一致 |

记录数用于复现当前样本，不是所有政策文件的固定要求；输出数量也不等于政策语义或表头关联已经验证正确。

## 当前限制

- 每次函数调用或命令运行处理单份本地文件。
- 当前记录是原始单元格数据，不是最终 RAG 检索片段。后续需要结合表头、行和合并说明组织上下文。
- 不执行 OCR，不读取图片中的文字；字体、颜色、批注和超链接目标等未单独提取。
- 缓存反映工作簿保存时的结果。核对时可根据工作表和单元格坐标查看原件。
- 合并范围用于保留位置，不自动把共同条件分配给各专业。
- 原文写“详见学院网站”等内容时保持原样；当前脚本不会继续访问网站或推断缺失要求。
- 当前异常处理覆盖上表所列场景，不保证识别所有损坏文件或操作系统读取错误。

## 同伴复现清单

以下项目由评审人实际完成后勾选：

- [ ] 在自己的环境中按说明安装依赖并运行两个样本，确认退出码和输出结构。
- [ ] 导入并调用 read_excel，确认只导入时不读取文件、不打印，连续调用结果不混用。
- [ ] 在 policy-003 原表中选取至少两个专业，核对相关条件文字、单元格坐标及共同表头或说明的位置。
- [ ] 核对 policy-004 的一个合并单元格与一个普通单元格，确认范围分别为字符串和 `null`。
- [ ] 按“失败场景与复现方法”至少复现一个失败场景，确认提示和退出码。
- [ ] 确认样本附件未修改，未提交临时测试文件、`.venv` 或缓存。
- [ ] 在 PR 中记录实际复现结果及发现的问题，再决定是否批准。
