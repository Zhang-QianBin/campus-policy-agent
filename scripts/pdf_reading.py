import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader


def read_pdf(file_path):
    """读取 PDF，返回逐页文字记录列表。"""
    records = []
    reader = PdfReader(file_path)
    try:
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            records.append({
                "type": "page",
                "text": text.strip(),
                "location": {"page": page_number},
            })
    finally:
        reader.close()

    return records


def main():
    parser = argparse.ArgumentParser(description="读取 PDF 政策附件并输出 JSON。")
    parser.add_argument("file_path", type=Path, help="PDF 文件路径")
    args = parser.parse_args()

    try:
        records = read_pdf(args.file_path)
        if not records:
            raise ValueError(f"PDF 中没有页记录：{args.file_path}")
    except Exception as error:
        print(f"无法读取 PDF 文件：{args.file_path}", file=sys.stderr)
        print(f"错误信息：{error}", file=sys.stderr)
        return 1

    for record in records:
        if not record["text"]:
            print(
                f"第 {record['location']['page']} 页未提取到文字，请人工核对原 PDF。",
                file=sys.stderr,
            )

    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
