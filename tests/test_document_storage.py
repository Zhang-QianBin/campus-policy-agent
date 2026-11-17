import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.document_storage import load_document, read_document, save_document


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DocumentStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        previous_directory = Path.cwd()
        self.addCleanup(os.chdir, previous_directory)
        os.chdir(self.temporary.name)
        self.source = Path("data/samples/policy-test/body.md")
        self.source.parent.mkdir(parents=True)
        self.source.write_text("政策标题\n\n中文正文。", encoding="utf-8")

    def run_cli(self, *arguments):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        # 临时样本目录作为 cwd，通过 PYTHONPATH 找到项目模块。
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        return subprocess.run(
            [sys.executable, "-m", "scripts.document_storage", *arguments],
            capture_output=True,
            encoding="utf-8",
            env=env,
        )

    def test_markdown_alias_is_dispatched(self):
        alias = self.source.with_suffix(".MARKDOWN")
        alias.write_text("另一个标题\n\n正文", encoding="utf-8")
        result = read_document(alias)
        self.assertEqual(result["metadata"]["title"], "另一个标题")
        self.assertEqual(result["records"][0]["text"], "另一个标题\n\n正文")

    def test_unsupported_format_is_rejected(self):
        with self.assertRaises(ValueError):
            read_document(self.source.with_suffix(".xls"))

    def test_save_load_round_trip_preserves_chinese_and_null(self):
        document = read_document(self.source)
        target = Path("output/nested/body.json")
        save_document(document, target)
        self.assertEqual(load_document(target), document)
        self.assertIsNone(load_document(target)["records"][0]["page"])
        self.assertIn("中文正文", target.read_text(encoding="utf-8"))

    def test_existing_file_is_not_overwritten(self):
        target = Path("existing.json")
        target.write_text('{"existing": true}', encoding="utf-8")
        original = target.read_bytes()
        with self.assertRaises(FileExistsError):
            save_document(read_document(self.source), target)
        self.assertEqual(target.read_bytes(), original)

    def test_serialization_error_does_not_leave_partial_file(self):
        target = Path("output/invalid.json")
        with self.assertRaises(TypeError):
            save_document({"unsupported": object()}, target)
        self.assertFalse(target.exists())

    def test_load_missing_or_invalid_json(self):
        with self.assertRaises(FileNotFoundError):
            load_document("missing.json")
        invalid = Path("invalid.json")
        invalid.write_text("not JSON", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            load_document(invalid)

    def test_cli_accepts_short_and_long_output_options(self):
        for index, option in enumerate(["-o", "--output"]):
            with self.subTest(option=option):
                target = Path(f"output/{index}.json")
                result = self.run_cli(str(self.source), option, str(target))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(load_document(target), read_document(self.source))

    def test_cli_reports_missing_arguments_and_file_errors(self):
        no_output = self.run_cli(str(self.source))
        self.assertEqual(no_output.returncode, 2)
        self.assertEqual(no_output.stdout, "")

        missing = self.run_cli(
            str(self.source.with_name("missing.md")), "-o", "output.json"
        )
        self.assertEqual(missing.returncode, 1)
        self.assertEqual(missing.stdout, "")
        self.assertTrue(missing.stderr)
        self.assertFalse(Path("output.json").exists())

        target = Path("existing.json")
        target.write_text("existing", encoding="utf-8")
        existing = self.run_cli(str(self.source), "--output", str(target))
        self.assertEqual(existing.returncode, 1)
        self.assertEqual(existing.stdout, "")
        self.assertTrue(existing.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "existing")

        help_result = self.run_cli("--help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--output", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
