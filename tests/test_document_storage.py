import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pypdf import PdfWriter
from pypdf.errors import PdfReadError
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from scripts.document_storage import READERS, load_document, read_document, save_document
from scripts.paths import PROJECT_ROOT


PROJECT_BODY = "data/samples/policy-002/body.md"
SCANNED_PDF = (
    "data/samples/policy-005/attachments/"
    "关于印发《杭州电子科技大学本科生奖学金评审办法》的通知（杭电学〔2026〕79号）.pdf"
)


class DocumentStorageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.samples = self.directory / "samples"
        self.body = self.samples / "policy-test" / "body.md"
        self.body.parent.mkdir(parents=True)
        self.body.write_text("# 正文标题\n\n中文正文。", encoding="utf-8")
        self.sources = {"sources": [{
            "source_id": "policy-test",
            "title": "清单里的发布标题",
            "files": [{"path": "body.md", "role": "body", "parse": True}],
        }]}

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "scripts.document_storage", *arguments],
            capture_output=True,
            encoding="utf-8",
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def register_attachment(self, filename):
        self.sources["sources"][0]["files"].append({
            "path": filename, "role": "attachment", "parse": True,
        })
        return self.body.with_name(filename)

    def test_registered_absolute_path_uses_manifest_title_and_sample_relative_path(self):
        result = read_document(self.body.resolve(), self.sources, self.samples)

        self.assertEqual(result["metadata"], {
            "source_id": "policy-test",
            "title": "清单里的发布标题",
            "file_path": "policy-test/body.md",
            "format": "markdown",
            "schema_version": 2,
        })
        self.assertIs(type(result["metadata"]["schema_version"]), int)
        self.assertEqual(result["records"], [
            {"type": "body", "text": "# 正文标题\n\n中文正文。", "location": {}},
        ])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["warnings"], [])

    def test_whitespace_markdown_returns_empty_with_file_warning(self):
        self.body.write_text(" \n\t", encoding="utf-8")

        result = read_document(self.body, self.sources, self.samples)

        self.assertEqual(result["status"], "empty")
        self.assertEqual(result["records"], [])
        self.assertEqual(len(result["warnings"]), 1)
        warning = result["warnings"][0]
        self.assertEqual(set(warning), {"code", "message", "location"})
        self.assertEqual(warning["code"], "empty_document")
        self.assertEqual(warning["location"], {})
        self.assertTrue(warning["message"])
        target = self.directory / "empty.json"
        save_document(result, target)
        self.assertEqual(load_document(target), result)

    def test_pdf_status_tracks_text_pages_and_preserves_empty_pages(self):
        path = self.register_attachment("pages.pdf")
        cases = [
            ((True,), "ok", []),
            ((False, True, False), "partial", [1, 3]),
            ((False, False), "empty", [1, 2]),
        ]
        for text_pages, status, empty_pages in cases:
            with self.subTest(text_pages=text_pages):
                writer = PdfWriter()
                for has_text in text_pages:
                    page = writer.add_blank_page(width=72, height=72)
                    if has_text:
                        # Minimal text layer using a standard PDF font.
                        page[NameObject("/Resources")] = DictionaryObject({
                            NameObject("/Font"): DictionaryObject({
                                NameObject("/F1"): DictionaryObject({
                                    NameObject("/Type"): NameObject("/Font"),
                                    NameObject("/Subtype"): NameObject("/Type1"),
                                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                                }),
                            }),
                        })
                        contents = DecodedStreamObject()
                        contents.set_data(b"BT /F1 12 Tf 10 10 Td (Policy text) Tj ET")
                        page.replace_contents(contents)
                with path.open("wb") as output:
                    writer.write(output)

                result = read_document(path, self.sources, self.samples)

                self.assertEqual(result["status"], status)
                self.assertEqual(result["records"], [
                    {
                        "type": "page",
                        "text": "Policy text" if has_text else "",
                        "location": {"page": number},
                    }
                    for number, has_text in enumerate(text_pages, start=1)
                ])
                warnings = result["warnings"]
                self.assertEqual([warning["code"] for warning in warnings], ["empty_page"] * len(empty_pages))
                self.assertEqual([warning["location"] for warning in warnings], [
                    {"page": page} for page in empty_pages
                ])
                for warning in warnings:
                    self.assertEqual(set(warning), {"code", "message", "location"})
                    self.assertIn(f"第 {warning['location']['page']} 页", warning["message"])

    def test_registered_corrupt_pdf_remains_a_reader_error(self):
        path = self.register_attachment("corrupt.pdf")
        path.write_bytes(b"%PDF-1.7\n")

        with self.assertRaises(PdfReadError):
            read_document(path, self.sources, self.samples)

    def test_same_name_attachments_are_matched_by_path_and_markdown_alias_works(self):
        other = {"source_id": "policy-other", "title": "另一条发布", "files": []}
        self.sources["sources"].append(other)

        for source in self.sources["sources"]:
            with self.subTest(source=source["source_id"]):
                relative_path = "attachments/同名.MARKDOWN"
                source["files"].append({
                    "path": relative_path, "role": "attachment", "parse": True,
                })
                file_path = f"{source['source_id']}/{relative_path}"
                attachment = self.samples / file_path
                attachment.parent.mkdir(parents=True)
                attachment.write_text(source["title"], encoding="utf-8")

                result = read_document(attachment, self.sources, self.samples)

                self.assertEqual(result["metadata"]["title"], "同名")
                self.assertEqual(result["metadata"]["source_id"], source["source_id"])
                self.assertEqual(result["metadata"]["file_path"], file_path)
                self.assertEqual(result["metadata"]["format"], "markdown")
                self.assertEqual(result["records"][0]["text"], source["title"])

    def test_unregistered_file_is_rejected_before_dispatch(self):
        unregistered = self.body.with_name("unregistered.xls")
        unregistered.write_bytes(b"unregistered file")
        with self.assertRaisesRegex(LookupError, "未在来源清单中登记"):
            read_document(unregistered, self.sources, self.samples)

    def test_archive_is_rejected_before_dispatch(self):
        archive = self.body.with_name("archive.zip")
        archive.write_bytes(b"archived file")
        self.sources["sources"][0]["files"].append({
            "path": archive.name, "role": "archive", "parse": False,
        })
        reader = Mock()
        with patch.dict(READERS, {".zip": reader}):
            with self.assertRaisesRegex(ValueError, "仅留档"):
                read_document(archive, self.sources, self.samples)
        reader.assert_not_called()

    def test_registered_unsupported_format_is_rejected(self):
        unsupported = self.register_attachment("body.xls")
        unsupported.write_bytes(b"unsupported file")
        with self.assertRaisesRegex(ValueError, "不支持的文档类型"):
            read_document(unsupported, self.sources, self.samples)

    def test_registered_missing_file_remains_a_reader_error(self):
        self.body.unlink()
        with self.assertRaises(FileNotFoundError):
            read_document(self.body, self.sources, self.samples)

    def test_save_load_round_trip_preserves_chinese_and_null(self):
        document = {"text": "中文正文", "merged_range": None}
        target = self.directory / "output" / "nested" / "body.json"
        save_document(document, target)
        self.assertEqual(load_document(target), document)
        self.assertIn("中文正文", target.read_text(encoding="utf-8"))
        self.assertIn("null", target.read_text(encoding="utf-8"))

    def test_existing_file_is_not_overwritten(self):
        target = self.directory / "existing.json"
        target.write_text('{"existing": true}', encoding="utf-8")
        original = target.read_bytes()
        with self.assertRaises(FileExistsError):
            save_document({"text": "新内容"}, target)
        self.assertEqual(target.read_bytes(), original)

    def test_serialization_error_does_not_leave_partial_file(self):
        target = self.directory / "output" / "invalid.json"
        with self.assertRaises(TypeError):
            save_document({"unsupported": object()}, target)
        self.assertFalse(target.exists())

    def test_load_missing_or_invalid_json(self):
        with self.assertRaises(FileNotFoundError):
            load_document(self.directory / "missing.json")
        invalid = self.directory / "invalid.json"
        invalid.write_text("not JSON", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            load_document(invalid)

    def test_cli_accepts_short_and_long_output_options(self):
        expected = read_document(PROJECT_ROOT / PROJECT_BODY)
        self.assertEqual(expected["metadata"]["file_path"], "policy-002/body.md")
        for index, option in enumerate(["-o", "--output"]):
            with self.subTest(option=option):
                target = self.directory / "output" / f"{index}.json"
                result = self.run_cli(PROJECT_BODY, option, str(target))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")
                self.assertEqual(load_document(target), expected)

    def test_cli_exports_scanned_pdf_with_partial_status_and_page_warnings(self):
        target = self.directory / "scan.json"

        completed = self.run_cli(SCANNED_PDF, "-o", str(target))

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = load_document(target)
        self.assertEqual(result["status"], "partial")
        self.assertEqual([record["location"]["page"] for record in result["records"]], list(range(1, 8)))
        self.assertEqual([record["text"] for record in result["records"][:6]], [""] * 6)
        self.assertTrue(result["records"][6]["text"])
        self.assertEqual([warning["location"]["page"] for warning in result["warnings"]], list(range(1, 7)))
        self.assertTrue(all(warning["code"] == "empty_page" for warning in result["warnings"]))

    def test_cli_reports_missing_arguments_and_file_errors(self):
        no_output = self.run_cli(PROJECT_BODY)
        self.assertEqual(no_output.returncode, 2)
        self.assertEqual(no_output.stdout, "")

        output = self.directory / "output.json"
        unregistered = self.run_cli(str(self.body), "-o", str(output))
        self.assertEqual(unregistered.returncode, 1)
        self.assertEqual(unregistered.stdout, "")
        self.assertIn("未在来源清单中登记", unregistered.stderr)
        self.assertFalse(output.exists())

        target = self.directory / "existing.json"
        target.write_text("existing", encoding="utf-8")
        existing = self.run_cli(PROJECT_BODY, "--output", str(target))
        self.assertEqual(existing.returncode, 1)
        self.assertEqual(existing.stdout, "")
        self.assertTrue(existing.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), "existing")

        help_result = self.run_cli("--help")
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--output", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
