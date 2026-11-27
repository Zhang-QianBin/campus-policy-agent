import argparse
import json
import sys
from pathlib import Path

from openpyxl import load_workbook


def read_excel(file_path):
    """读取 Excel，返回有效单元格记录列表。"""
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

                        merged_range = None
                        for region in worksheet.merged_cells.ranges:
                            if cell.coordinate in region:
                                merged_range = str(region)
                                break

                        records.append({
                            "type": "cell",
                            "text": text,
                            "location": {
                                "sheet": worksheet.title,
                                "cell": cell.coordinate,
                                "merged_range": merged_range,
                            },
                        })
    finally:
        workbook.close()

    if not records:
        raise ValueError(f"工作簿中未读取到有效文字：{file_path}")

    return records


def main():
    parser = argparse.ArgumentParser(description="读取 Excel 政策附件并输出 JSON。")
    parser.add_argument("file_path", type=Path, help="Excel 文件路径")
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
