import argparse
import json
import sys
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


def main():
    parser = argparse.ArgumentParser(description="读取 Markdown 政策正文并输出 JSON。")
    parser.add_argument("file_path", type=Path, help="Markdown 文件路径")
    args = parser.parse_args()

    try:
        records = read_markdown(args.file_path)
        if not records:
            raise ValueError(f"Markdown 中未读取到有效文字：{args.file_path}")
    except Exception as error:
        print(f"无法读取 Markdown 文件：{args.file_path}", file=sys.stderr)
        print(f"错误信息：{error}", file=sys.stderr)
        return 1

    print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
