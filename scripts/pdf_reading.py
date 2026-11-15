import sys
from pypdf import PdfReader
from pathlib import Path

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
        page_count = reader.get_num_pages()

        for page_index in range(page_count):
            page = reader.get_page(page_index)
            text = page.extract_text()

            if text is None or text.strip() == "":
                record = {
                    "page": page_index + 1,
                    "text": ""
                }
            else:
                record = {
                    "page": page_index + 1,
                    "text": text.strip()
                }

            records.append(record)
    finally:
        reader.close()

    if not records:
        raise ValueError(f"PDF 中没有页记录：{file_path}")

    return {
        "metadata": metadata,
        "records": records,
    }



def main():
    import argparse
    import json

    parser = argparse.ArgumentParser(description="读取 PDF 文件并输出元数据和记录。")
    parser.add_argument("file_path", type=str, help="PDF 文件路径")
    args = parser.parse_args()

    try:
        result = read_pdf(args.file_path)
        for record in result["records"]:
            if not record["text"]:
                print(
                    f"第 {record['page']} 页未提取到文字，请人工核对原 PDF。",
                    file=sys.stderr,
                )
        print(json.dumps(result, ensure_ascii=False, indent=4))
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
