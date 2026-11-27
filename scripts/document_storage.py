import argparse
import json
import sys
from pathlib import Path

from scripts.docx_reading import read_docx
from scripts.excel_reading import read_excel_with_warnings
from scripts.markdown_reading import read_markdown
from scripts.paths import SAMPLES_DIR
from scripts.pdf_reading import read_pdf
from scripts.sources import find_source_file, load_sources


DOCUMENT_SCHEMA_VERSION = 2
READERS = {
    ".docx": read_docx,
    ".xlsx": read_excel_with_warnings,
    ".md": read_markdown,
    ".markdown": read_markdown,
    ".pdf": read_pdf,
}


def read_document(path, sources=None, samples_dir=SAMPLES_DIR):
    """读取已登记的文件，返回元数据、文字记录和提取状态。"""
    path = Path(path)
    if sources is None:
        sources = load_sources()
    source, entry = find_source_file(path, sources, samples_dir)
    if not entry["parse"]:
        raise ValueError(f"文件仅留档，不参与解析：{path}")

    suffix = path.suffix.lower()
    reader = READERS.get(suffix)
    if reader is None:
        supported = ", ".join(sorted(READERS))
        raise ValueError(f"不支持的文档类型：{path.suffix}；支持：{supported}")

    source_id = source["source_id"]
    registered_path = Path(entry["path"])
    title = source["title"] if entry["role"] == "body" else registered_path.stem
    file_format = "markdown" if suffix in {".md", ".markdown"} else suffix[1:]
    if suffix == ".xlsx":
        records, warnings = reader(path)
    else:
        records = reader(path)
        warnings = [
            {
                "code": "empty_page",
                "message": f"第 {record['location']['page']} 页未提取到文字，请人工核对原 PDF。",
                "location": record["location"].copy(),
            }
            for record in records
            if record["type"] == "page" and not record["text"]
        ]
    if any(record["text"] for record in records):
        status = "partial" if warnings else "ok"
    else:
        status = "empty"
        if not warnings:
            warnings.append({
                "code": "empty_document",
                "message": "未提取到文字，请核对原文件。",
                "location": {},
            })

    return {
        "metadata": {
            "source_id": source_id,
            "title": title,
            "file_path": (Path(source_id) / registered_path).as_posix(),
            "format": file_format,
            "schema_version": DOCUMENT_SCHEMA_VERSION,
        },
        "records": records,
        "status": status,
        "warnings": warnings,
    }


def save_document(result, output_path):
    """以 UTF-8 新建 JSON 文件；目标已存在时不覆盖。"""
    text = json.dumps(result, ensure_ascii=False, indent=2)
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("x", encoding="utf-8") as file:
        file.write(text)
        file.write("\n")


def load_document(file_path):
    """读取 JSON 文件，还原 Python 数据；读取失败时向调用方抛出异常。"""
    json_file = Path(file_path)

    with json_file.open("r", encoding="utf-8") as file:
        return json.load(file)


def main():
    parser = argparse.ArgumentParser(description="读取文档并导出为 UTF-8 JSON 文件。")
    parser.add_argument("input_path", type=Path, help="已登记样本的相对或绝对路径")
    parser.add_argument(
        "-o", "--output",
        dest="output_path",
        type=Path,
        required=True,
        help="输出 JSON 文件路径；目标文件不能已存在",
    )
    args = parser.parse_args()

    try:
        result = read_document(args.input_path)
        save_document(result, args.output_path)
    except Exception as error:
        print(f"无法导出文档：{args.input_path}", file=sys.stderr)
        print(f"错误信息：{error}", file=sys.stderr)
        return 1

    print(f"已保存：{args.output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
