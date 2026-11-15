from pypdf import PdfReader
from pathlib import Path
from pypdf.errors import PdfReadError

pdf_path = "data/samples/policy-001/attachments/unpacked/2024级本科专业培养方案/03电子信息学院2024级本科专业培养方案.pdf"
title = Path(pdf_path).stem

try:
    reader = PdfReader(pdf_path)
    page_count = reader.get_num_pages()
    print(f"PDF 总页数: {page_count}")

    sample_root = Path("data/samples")
    relative_path = Path(pdf_path).relative_to(sample_root)
    source_id = relative_path.parts[0]

    records = []

    for page_index in range(page_count):

        page = reader.get_page(page_index)
        text = page.extract_text()

        if(text is None or text.strip() == ""):
            record = {
                "source_id": source_id,
                "title": title,
                "file_path": pdf_path,
                "page": page_index + 1,
                "text": ""
            }
        else:
            record = {
                "source_id": source_id,
                "title": title,
                "file_path": pdf_path,
                "page": page_index + 1,
                "text": text.strip()
            }

        records.append(record)

    for record in records:
        print("来源 ID：", record["source_id"])
        print("文件路径：", record["file_path"])
        print("标题：", record["title"])
        print("页码：", record["page"])
        print("字符数：", len(record["text"]))
        print("正文：", record["text"])

        if not record["text"].strip():
            print("未提取到有效文字，请人工核对原 PDF。")

except FileNotFoundError:
    print("文件不存在:", pdf_path)
    raise SystemExit(1)

except PdfReadError as error:
    print("无法读取 PDF 文件:", pdf_path)
    print(error)
    raise SystemExit(1)
    


