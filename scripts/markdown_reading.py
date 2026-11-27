from pathlib import Path


def read_markdown(file_path):
    """读取 UTF-8 Markdown，返回包含完整正文的记录列表。"""
    markdown_file = Path(file_path)

    if markdown_file.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError(f"不支持的 Markdown 文件格式：{file_path}")

    text = markdown_file.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []

    return [{"type": "body", "text": text, "location": {}}]
