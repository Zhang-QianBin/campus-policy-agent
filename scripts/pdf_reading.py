import argparse
import json
import sys
from pathlib import Path

from pypdf import PdfReader


def read_pdf(file_path):
    """读取样本 PDF，返回文件元数据和逐页文字记录。"""
    pdf_file = Path(file_path)
    sample_root = Path("data/samples")

    metadata = {
        "source_id": pdf_file.relative_to(sample_root).parts[0],
        "title": pdf_file.stem,
        "file_path": pdf_file.as_posix(),
    }

    records = []
    reader = PdfReader(file_path)
    try:
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            records.append({
                "page": page_number,
                "text": text.strip(),
            })
    finally:
        reader.close()

    if not records:
        raise ValueError(f"PDF 中没有页记录：{file_path}")

    return {
        "metadata": metadata,
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description="读取 PDF 政策附件并输出 JSON。")
    parser.add_argument("file_path", type=Path, help="data/samples 下的项目相对文件路径")
    args = parser.parse_args()

    try:
        result = read_pdf(args.file_path)
    except Exception as error:
        print(f"无法读取 PDF 文件：{args.file_path}", file=sys.stderr)
        print(f"错误信息：{error}", file=sys.stderr)
        return 1

    for record in result["records"]:
        if not record["text"]:
            print(
                f"第 {record['page']} 页未提取到文字，请人工核对原 PDF。",
                file=sys.stderr,
            )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
