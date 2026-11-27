import argparse
import json
import sys
from contextlib import ExitStack
from pathlib import Path

from openpyxl import load_workbook


def read_excel(file_path):
    """读取 Excel，返回有效单元格记录列表。"""
    records, _ = read_excel_with_warnings(file_path)
    return records


def read_excel_with_warnings(file_path):
    """读取 Excel，返回单元格记录和公式缓存缺失告警。"""
    records = []
    warnings = []
    with ExitStack() as workbooks:
        workbook = load_workbook(file_path)
        workbooks.callback(workbook.close)
        cached_workbook = None
        for worksheet in workbook.worksheets:
            for row in worksheet.iter_rows():
                for cell in row:
                    value = cell.value
                    if cell.data_type == "f":
                        if cached_workbook is None:
                            cached_workbook = load_workbook(file_path, data_only=True)
                            workbooks.callback(cached_workbook.close)
                        value = cached_workbook[worksheet.title][cell.coordinate].value
                        if value is None:
                            warnings.append({
                                "code": "missing_formula_cache",
                                "message": (
                                    f"工作表「{worksheet.title}」的 {cell.coordinate} "
                                    "公式缺少已保存的计算值。"
                                ),
                                "location": {"sheet": worksheet.title, "cell": cell.coordinate},
                            })
                            continue

                    if value is None:
                        continue
                    text = str(value).strip()
                    if not text:
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

    return records, warnings


def main():
    parser = argparse.ArgumentParser(description="读取 Excel 政策附件并输出 JSON。")
    parser.add_argument("file_path", type=Path, help="Excel 文件路径")
    args = parser.parse_args()

    try:
        records, warnings = read_excel_with_warnings(args.file_path)
        for warning in warnings:
            print(warning["message"], file=sys.stderr)
        if not records:
            raise ValueError(f"工作簿中未读取到有效文字：{args.file_path}")
    except Exception as error:
        print(f"无法读取 Excel 文件：{args.file_path}", file=sys.stderr)
        print(f"错误信息：{error}", file=sys.stderr)
        return 1

    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
