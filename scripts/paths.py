from pathlib import Path


# 以本文件位置推断项目根目录，不依赖运行命令时所在的目录。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLES_DIR = PROJECT_ROOT / "data" / "samples"
SOURCES_FILE = SAMPLES_DIR / "sources.json"
