import argparse
import json
import sys
from pathlib import Path

from scripts.docx_reading import read_docx
from scripts.excel_reading import read_excel
from scripts.markdown_reading import read_markdown
from scripts.pdf_reading import read_pdf


READERS = {
    ".docx": read_docx,
    ".xlsx": read_excel,
    ".md": read_markdown,
    ".markdown": read_markdown,
    ".pdf": read_pdf,
}


def read_document(path):
    """根据扩展名选择读取器，返回统一的文档结果。"""
    path = Path(path)
    reader = READERS.get(path.suffix.lower())
    if reader is None:
        supported = ", ".join(sorted(READERS))
        raise ValueError(f"不支持的文档类型：{path.suffix}；支持：{supported}")
    return reader(path)


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
    parser.add_argument("input_path", type=Path, help="data/samples 下的项目相对文件路径")
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
