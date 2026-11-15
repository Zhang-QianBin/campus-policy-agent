import json
from pathlib import Path
from zipfile import BadZipFile
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

excel_path = (
"data/samples/policy-003/attachments/2026级本科生普通类转专业（类）转入实施细则.xlsx"
)

excel_file = Path(excel_path)
sample_root = Path("data/samples")

metadata = {
    "source_id": excel_file.relative_to(sample_root).parts[0],
    "title": excel_file.stem,
    "file_path": excel_file.as_posix(),
}

records = []
try:
    workbook = load_workbook(excel_path)

    try:
        for worksheet in workbook.worksheets:
            for row in worksheet.iter_rows(
                min_row=1,
                max_row=worksheet.max_row,
                min_col=1,
                max_col=worksheet.max_column,
            ):
                for cell in row:

                    if cell.value is not None:
                        text = str(cell.value).strip()
                        if text == "":
                            continue

                        record = {
                            "sheet": worksheet.title,
                            "cell": cell.coordinate,
                            "text": text,
                            "merged_range":None
                        }
                        for region in worksheet.merged_cells.ranges:
                            if cell.coordinate in region:
                                record["merged_range"] = str(region)
                                break

                        records.append(record)
    finally:
        workbook.close()

    if not records:
        print(f"工作簿中未读取到有效文字：{excel_path}")
        raise SystemExit(1)

    result = {
        "metadata": metadata,
        "records": records,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))

except FileNotFoundError:
    print(f"文件未找到: {excel_path}")
    raise SystemExit(1)
except InvalidFileException as error:
    print(f"无效的Excel文件: {excel_path}")
    print(f"错误信息: {error}")
    raise SystemExit(1)
except BadZipFile as error:
    print(f"Excel文件损坏或无法解压: {excel_path}")
    print(f"错误信息: {error}")
    raise SystemExit(1)