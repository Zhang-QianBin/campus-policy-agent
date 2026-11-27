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
