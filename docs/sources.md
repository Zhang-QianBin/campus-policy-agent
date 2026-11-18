# 政策样本来源清单

样本来源的数据统一记录在 [data/samples/sources.json](../data/samples/sources.json)，程序和测试都读取这一份文件；本文只说明整理约定和字段含义，不再逐条重复来源数据，避免两处记录不一致。

当前样本为杭州电子科技大学的 5 条发布记录（policy-001～policy-005）。一条发布记录可以关联多份附件，不能直接等同于 5 份独立政策文件。

## 整理约定

- 每个发布页面对应一个稳定编号 `policy-NNN`，即 `source_id`；该页面的正文和附件放在同名目录 `data/samples/policy-NNN/` 内。
- `body.md` 保存人工整理的网页正文，`attachments/` 保存下载的原始附件；没有附件的页面不必创建附件目录。附件保留下载时的文件名。
- 压缩包保留原文件用于追溯下载来源，解压内容放在 `attachments/unpacked/<压缩包名>/`。后续解析只读取解压出的具体文件，不重复导入压缩包。
- `data/samples/` 下的每个文件都必须在 sources.json 中登记；新增、删除或改名样本文件时同步修改清单。
- 程序取得 `source_id` 等来源信息时，只按文件路径到 sources.json 中查找对应登记（`scripts/sources.py` 的 `find_source_file`），不从路径中解析目录名；未登记的文件会报错。相对路径和绝对路径都可以，与运行时所在目录无关。目录名与 `source_id` 一致仅是存放约定，由校验测试保证。
- 发布日期、来源和发布者沿用人工记录；不知道的字段写 `null`，不推测补写。
- 样本已保存不等于解析成功；PDF、Excel 等文件的文字提取与检索效果需在后续实验中验证。

## 字段说明

顶层 `schema_version` 当前为 1，清单结构发生不兼容变化时递增。`sources` 中每条来源包含：

| 字段 | 含义 |
| --- | --- |
| `source_id` | 发布记录编号，必须与样本目录名一致且不重复 |
| `title` | 发布页面标题 |
| `page_url` | 发布页面地址 |
| `category` | 页面上的信息类型，如“部门通知”；未标注为 `null` |
| `department` | 发布部门（页面上的“来源”）；未标注为 `null` |
| `publisher` | 页面上的发布者（个人或账号）；未标注为 `null` |
| `published_date` | 发布日期，`YYYY-MM-DD` |
| `collected_date` | 本地保存日期，`YYYY-MM-DD` |
| `files` | 本条来源下的文件列表，见下表 |

`files` 中每个文件包含：

| 字段 | 含义 |
| --- | --- |
| `path` | 相对 `data/samples/<source_id>/` 的路径，使用 `/` 分隔 |
| `role` | `body`（网页正文）、`attachment`（附件）或 `archive`（压缩包） |
| `download_url` | 原始下载地址；人工整理的正文或解压出的文件为 `null` |
| `parse` | 是否参与解析；压缩包必须为 `false` |
| `extracted_from` | 可选，仅解压出的文件使用，指向本来源中的压缩包 `path` |

## 校验

[test_sources.py](../tests/test_sources.py) 会检查：清单字段与日期格式、`source_id` 与目录一致且不重复、登记的文件都存在、没有未登记或重复登记的文件、压缩包规则，以及按路径查找登记信息的行为。随全部测试一起运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

只运行清单校验：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_sources -v
```
