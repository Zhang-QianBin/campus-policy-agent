from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph


def read_docx(file_path):
    """读取 DOCX 顶层段落与表格，返回带位置的文字记录列表。"""
    docx_file = Path(file_path)

    if docx_file.suffix.lower() != ".docx":
        raise ValueError(f"仅支持 .docx 文件，旧版 .doc 请先另行转换：{file_path}")

    with docx_file.open("rb") as stream:
        document = Document(stream)

    records = []
    table_index = 0
    for block_index, block in enumerate(document.iter_inner_content(), start=1):
        if isinstance(block, Paragraph):
            text = block.text.strip()
            if text:
                records.append({
                    "type": "paragraph",
                    "text": text,
                    "location": {"block": block_index},
                })
        else:
            table_index += 1
            for row_index, row in enumerate(block.rows, start=1):
                for column_index, cell in enumerate(
                    row.cells, start=row.grid_cols_before + 1
                ):
                    text = cell.text.strip()
                    if text:
                        records.append({
                            "type": "table_cell",
                            "text": text,
                            "location": {
                                "block": block_index,
                                "table": table_index,
                                "row": row_index,
                                "column": column_index,
                            },
                        })

    return records
