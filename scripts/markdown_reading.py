import argparse
import json
import sys
from pathlib import Path


def read_markdown(file_path):
    """读取 UTF-8 Markdown，返回文件元数据和完整正文记录。"""
    markdown_file = Path(file_path)
    sample_root = Path("data/samples")

    if markdown_file.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError(f"不支持的 Markdown 文件格式：{file_path}")

    source_id = markdown_file.relative_to(sample_root).parts[0]
    text = markdown_file.read_text(encoding="utf-8-sig").strip()
    if not text:
        raise ValueError(f"Markdown 中未读取到有效文字：{file_path}")

    metadata = {
        "source_id": source_id,
        "title": text.splitlines()[0].strip(),
        "file_path": markdown_file.as_posix(),
    }

    return {
        "metadata": metadata,
        "records": [{"page": None, "text": text}],
    }


def main():
    parser = argparse.ArgumentParser(description="读取 Markdown 政策正文并输出 JSON。")
    parser.add_argument("file_path", help="data/samples 下的项目相对文件路径")
    args = parser.parse_args()

    try:
        result = read_markdown(args.file_path)
    except Exception as error:
        print(f"无法读取 Markdown 文件：{args.file_path}", file=sys.stderr)
        print(f"错误信息：{error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
