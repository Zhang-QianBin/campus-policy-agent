import argparse
import json
import sys
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


def main():
    parser = argparse.ArgumentParser(description="读取 DOCX 政策附件并输出 JSON。")
    parser.add_argument("file_path", type=Path, help="DOCX 文件路径")
    args = parser.parse_args()

    try:
        records = read_docx(args.file_path)
        if not records:
            raise ValueError(f"Word 文档中未读取到有效文字：{args.file_path}")
    except Exception as error:
        print(f"无法读取 Word 文件：{args.file_path}", file=sys.stderr)
        print(f"错误信息：{error}", file=sys.stderr)
        return 1

    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
