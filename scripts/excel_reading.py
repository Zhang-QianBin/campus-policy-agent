import argparse
import json
import sys
from pathlib import Path

from openpyxl import load_workbook


def read_excel(file_path):
    """读取样本 Excel，返回文件元数据和有效单元格记录。"""
    excel_file = Path(file_path)
    sample_root = Path("data/samples")

    metadata = {
        "source_id": excel_file.relative_to(sample_root).parts[0],
        "title": excel_file.stem,
        "file_path": excel_file.as_posix(),
    }

    records = []
    workbook = load_workbook(file_path)
    try:
        for worksheet in workbook.worksheets:
            for row in worksheet.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        text = str(cell.value).strip()
                        if text == "":
                            continue

                        record = {
                            "sheet": worksheet.title,
                            "cell": cell.coordinate,
                            "text": text,
                            "merged_range": None,
                        }
                        for region in worksheet.merged_cells.ranges:
                            if cell.coordinate in region:
                                record["merged_range"] = str(region)
                                break

                        records.append(record)
    finally:
        workbook.close()

    if not records:
        raise ValueError(f"工作簿中未读取到有效文字：{file_path}")

    return {
        "metadata": metadata,
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description="读取 Excel 政策附件并输出 JSON。")
    parser.add_argument("file_path", type=Path, help="data/samples 下的项目相对文件路径")
    args = parser.parse_args()

    try:
        result = read_excel(args.file_path)
    except Exception as error:
        print(f"无法读取 Excel 文件：{args.file_path}", file=sys.stderr)
        print(f"错误信息：{error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
