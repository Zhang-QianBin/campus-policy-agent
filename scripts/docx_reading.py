import argparse
import json
import sys
from pathlib import Path

from docx import Document
from docx.text.paragraph import Paragraph


def read_docx(file_path):
    """读取 DOCX 顶层段落与表格，返回文件元数据和有位置的文字记录。"""
    docx_file = Path(file_path)
    sample_root = Path("data/samples")

    if docx_file.suffix.lower() != ".docx":
        raise ValueError(f"仅支持 .docx 文件，旧版 .doc 请先另行转换：{file_path}")

    metadata = {
        "source_id": docx_file.relative_to(sample_root).parts[0],
        "title": docx_file.stem,
        "file_path": docx_file.as_posix(),
    }

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
                    "block": block_index,
                    "text": text,
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
                            "block": block_index,
                            "table": table_index,
                            "row": row_index,
                            "column": column_index,
                            "text": text,
                        })

    if not records:
        raise ValueError(f"Word 文档中未读取到有效文字：{file_path}")

    return {
        "metadata": metadata,
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description="读取 DOCX 政策附件并输出 JSON。")
    parser.add_argument("file_path", type=Path, help="data/samples 下的项目相对 .docx 文件路径")
    args = parser.parse_args()

    try:
        result = read_docx(args.file_path)
    except Exception as error:
        print(f"无法读取 Word 文件：{args.file_path}", file=sys.stderr)
        print(f"错误信息：{error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
