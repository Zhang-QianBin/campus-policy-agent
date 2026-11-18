import json
from datetime import date
from pathlib import Path, PurePosixPath, PureWindowsPath

from scripts.paths import SAMPLES_DIR, SOURCES_FILE


SCHEMA_VERSION = 1
SOURCE_KEYS = {
    "source_id", "title", "page_url", "category", "department",
    "publisher", "published_date", "collected_date", "files",
}
FILE_KEYS = {"path", "role", "download_url", "parse"}
OPTIONAL_FILE_KEYS = {"extracted_from"}
ROLES = {"body", "attachment", "archive"}


def load_sources(path=SOURCES_FILE):
    """读取 UTF-8 来源清单，返回 Python 数据；文件缺失或 JSON 错误时抛出异常。"""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def find_source_file(path, data, samples_dir=SAMPLES_DIR):
    """按文件路径在清单中查找登记信息，返回 (来源条目, 文件条目)。

    source_id 等信息只从清单读取，不从路径解析。相对路径按当前目录转成
    绝对路径后再比较，因此在任何目录运行、传相对或绝对路径都能找到。
    未登记的文件抛出 LookupError。
    """
    target = Path(path).resolve()
    samples_dir = Path(samples_dir)
    for source in data["sources"]:
        for entry in source["files"]:
            registered = samples_dir / source["source_id"] / entry["path"]
            if registered.resolve() == target:
                return source, entry
    raise LookupError(f"文件未在来源清单中登记：{path}")


def validate_sources(data, samples_dir=SAMPLES_DIR):
    """检查清单与样本目录是否一致，返回问题描述列表；空列表表示通过。"""
    samples_dir = Path(samples_dir)
    problems = []

    if data.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version 应为 {SCHEMA_VERSION}：{data.get('schema_version')!r}")

    registered = set()
    seen_ids = set()
    for index, source in enumerate(data.get("sources", []), start=1):
        source_id = source.get("source_id")
        label = source_id or f"第 {index} 条来源"
        problems += _check_keys(label, source, SOURCE_KEYS, set())

        if source_id in seen_ids:
            problems.append(f"{label}：source_id 重复")
        seen_ids.add(source_id)

        source_dir = samples_dir / str(source_id)
        if not source_dir.is_dir():
            problems.append(f"{label}：找不到同名样本目录 {source_dir.name}/")

        for key in ["published_date", "collected_date"]:
            value = source.get(key)
            if value is not None and not _is_iso_date(value):
                problems.append(f"{label}：{key} 不是 YYYY-MM-DD 日期：{value!r}")

        files = source.get("files", [])
        archives = {f.get("path") for f in files if f.get("role") == "archive"}
        for entry in files:
            problems += _check_file(label, entry, source_dir, archives)
            path = entry.get("path")
            if isinstance(path, str):
                full_path = (source_dir / path).resolve()
                if full_path in registered:
                    problems.append(f"{label}：文件重复登记：{path}")
                registered.add(full_path)

    sources_file = (samples_dir / SOURCES_FILE.name).resolve()
    for file in sorted(samples_dir.rglob("*")):
        resolved = file.resolve()
        if file.is_file() and resolved != sources_file and resolved not in registered:
            problems.append(f"未登记的文件：{file.relative_to(samples_dir).as_posix()}")

    return problems


def _check_file(label, entry, source_dir, archives):
    path = entry.get("path")
    problems = _check_keys(f"{label} 的文件 {path}", entry, FILE_KEYS, OPTIONAL_FILE_KEYS)
    if not isinstance(path, str):
        return problems + [f"{label}：文件条目缺少字符串 path"]

    posix = PurePosixPath(path)
    if "\\" in path or posix.is_absolute() or PureWindowsPath(path).drive or ".." in posix.parts:
        problems.append(f"{label}：path 须为来源目录内的相对 POSIX 路径：{path}")
    elif not (source_dir / path).is_file():
        problems.append(f"{label}：登记的文件不存在：{path}")

    role = entry.get("role")
    if role not in ROLES:
        problems.append(f"{label}：{path} 的 role 无效：{role!r}")
    if not isinstance(entry.get("parse"), bool):
        problems.append(f"{label}：{path} 的 parse 应为布尔值")
    if role == "archive" and entry.get("parse") is not False:
        problems.append(f"{label}：压缩包 {path} 的 parse 应为 false")

    extracted_from = entry.get("extracted_from")
    if extracted_from is not None and extracted_from not in archives:
        problems.append(f"{label}：{path} 的 extracted_from 未指向本来源的压缩包：{extracted_from}")
    return problems


def _check_keys(label, item, required, optional):
    problems = []
    missing = required - item.keys()
    unknown = item.keys() - required - optional
    if missing:
        problems.append(f"{label}：缺少字段 {', '.join(sorted(missing))}")
    if unknown:
        problems.append(f"{label}：未知字段 {', '.join(sorted(unknown))}")
    return problems


def _is_iso_date(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False
