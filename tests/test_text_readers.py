import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from docx import Document

from scripts.docx_reading import read_docx
from scripts.markdown_reading import read_markdown


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TextReaderTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        previous_directory = Path.cwd()
        self.addCleanup(os.chdir, previous_directory)
        os.chdir(self.temporary.name)
        self.sample = Path("data/samples/policy-test")
        self.sample.mkdir(parents=True)

    def run_cli(self, script, *arguments):
        return subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / script), *arguments],
            capture_output=True,
            encoding="utf-8",
        )

    def test_markdown_preserves_body_and_uses_first_nonempty_line(self):
        path = self.sample / "body.md"
        body = "政策标题\n\n第一段。\n\n    保留缩进。"
        path.write_text("\n" + body + "\n", encoding="utf-8-sig")

        result = read_markdown(path)

        self.assertEqual(result["metadata"], {
            "source_id": "policy-test",
            "title": "政策标题",
            "file_path": path.as_posix(),
        })
        self.assertEqual(result["records"], [{"page": None, "text": body}])

    def test_markdown_rejects_empty_and_invalid_encoding(self):
        path = self.sample / "empty.md"
        path.write_text(" \n\t", encoding="utf-8")
        with self.assertRaises(ValueError):
            read_markdown(path)
        path.write_bytes(b"\xff\xfe\x00")
        with self.assertRaises(UnicodeDecodeError):
            read_markdown(path)

    def test_missing_files_remain_exceptions_for_callers(self):
        for reader, filename in [
            (read_markdown, "missing.md"),
            (read_docx, "missing.docx"),
        ]:
            with self.subTest(filename=filename), self.assertRaises(FileNotFoundError):
                reader(self.sample / filename)

    def test_docx_preserves_paragraph_table_order_and_cell_locations(self):
        path = self.sample / "policy.docx"
        document = Document()
        document.add_paragraph("通知标题")
        document.add_paragraph("  ")
        table = document.add_table(rows=2, cols=2)
        table.cell(0, 0).text = "专业"
        table.cell(0, 1).text = "条件"
        table.cell(1, 0).text = "计算机"
        table.cell(1, 1).text = "绩点要求\n另有条件"
        document.add_paragraph("办理截止时间")
        document.save(path)

        result = read_docx(path)
        records = result["records"]

        self.assertEqual(result["metadata"]["title"], "policy")
        self.assertEqual(result["metadata"]["source_id"], "policy-test")
        self.assertEqual([r["text"] for r in records], [
            "通知标题", "专业", "条件", "计算机", "绩点要求\n另有条件", "办理截止时间",
        ])
        self.assertEqual([r["block"] for r in records], [1, 3, 3, 3, 3, 4])
        self.assertEqual(records[4], {
            "type": "table_cell", "block": 3, "table": 1,
            "row": 2, "column": 2, "text": "绩点要求\n另有条件",
        })

    def test_docx_table_only_document_and_merged_cells(self):
        path = self.sample / "table.docx"
        document = Document()
        table = document.add_table(rows=2, cols=2)
        table.cell(0, 0).merge(table.cell(0, 1)).text = "合并标题"
        table.cell(1, 0).text = "0"
        document.save(path)

        records = read_docx(path)["records"]

        self.assertEqual([r["text"] for r in records], ["合并标题", "合并标题", "0"])
        self.assertEqual([r["column"] for r in records], [1, 2, 1])

    def test_docx_rejects_empty_unsupported_and_invalid_archive(self):
        path = self.sample / "empty.docx"
        Document().save(path)
        with self.assertRaises(ValueError):
            read_docx(path)
        with self.assertRaises(ValueError):
            read_docx(self.sample / "old.doc")
        path.write_bytes(b"not a docx archive")
        from zipfile import BadZipFile
        with self.assertRaises(BadZipFile):
            read_docx(path)

    def test_readers_do_not_print_and_calls_are_independent(self):
        first = self.sample / "first.md"
        second = self.sample / "second.md"
        first.write_text("第一份", encoding="utf-8")
        second.write_text("第二份", encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            a = read_markdown(first)
            b = read_markdown(second)
            for name in ["scripts.markdown_reading", "scripts.docx_reading"]:
                importlib.reload(importlib.import_module(name))
        self.assertEqual(out.getvalue(), "")
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(a["records"][0]["text"], "第一份")
        self.assertEqual(b["records"][0]["text"], "第二份")

    def test_cli_outputs_json_and_reports_failures(self):
        markdown_path = self.sample / "body.md"
        markdown_path.write_text("政策正文", encoding="utf-8")
        docx_path = self.sample / "policy.docx"
        document = Document()
        document.add_paragraph("Word 正文")
        document.save(docx_path)

        for script, path, reader in [
            ("markdown_reading.py", markdown_path, read_markdown),
            ("docx_reading.py", docx_path, read_docx),
        ]:
            with self.subTest(script=script):
                result = self.run_cli(script, path.as_posix())
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(json.loads(result.stdout), reader(path))

                missing = self.run_cli(script, (self.sample / ("missing" + path.suffix)).as_posix())
                self.assertEqual(missing.returncode, 1)
                self.assertEqual(missing.stdout, "")
                self.assertTrue(missing.stderr)

                self.assertEqual(self.run_cli(script).returncode, 2)
                self.assertEqual(self.run_cli(script, "--help").returncode, 0)


if __name__ == "__main__":
    unittest.main()
