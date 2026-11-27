import json
import os
import subprocess
import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from openpyxl import Workbook
from pypdf import PdfWriter

from scripts.document_storage import read_document
from scripts.excel_reading import read_excel
from scripts.paths import PROJECT_ROOT
from scripts.pdf_reading import read_pdf


class AttachmentReaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def make_blank_pdf(self, page_count=2):
        path = self.directory / "blank.pdf"
        writer = PdfWriter()
        for _ in range(page_count):
            writer.add_blank_page(width=72, height=72)
        with path.open("wb") as stream:
            writer.write(stream)
        return path

    def run_cli(self, script, path):
        return subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / script), str(path)],
            capture_output=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def make_excel(self, cells, cached_values=None):
        path = self.directory / "policy-test" / "formulas.xlsx"
        path.parent.mkdir()
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "计算"
        for coordinate, value in cells.items():
            sheet[coordinate] = value

        if cached_values is None:
            workbook.save(path)
        else:
            buffer = BytesIO()
            workbook.save(buffer)
            # openpyxl saves formulas without calculated values. Add known caches to the test fixture.
            namespace = {"sheet": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            with ZipFile(buffer) as source, ZipFile(path, "w") as target:
                for entry in source.infolist():
                    data = source.read(entry)
                    if entry.filename == "xl/worksheets/sheet1.xml":
                        worksheet_xml = ElementTree.fromstring(data)
                        for coordinate, value in cached_values.items():
                            value_node = worksheet_xml.find(
                                f".//sheet:c[@r='{coordinate}']/sheet:v", namespace
                            )
                            self.assertIsNotNone(value_node)
                            value_node.text = str(value)
                        data = ElementTree.tostring(worksheet_xml, encoding="utf-8")
                    target.writestr(entry, data)
        workbook.close()
        return path

    def read_registered_excel(self, path):
        sources = {"sources": [{
            "source_id": "policy-test",
            "title": "测试政策",
            "files": [{"path": path.name, "role": "attachment", "parse": True}],
        }]}
        return read_document(path, sources=sources, samples_dir=self.directory)

    def test_pdf_preserves_original_page_numbers_including_empty_pages(self):
        path = self.make_blank_pdf()

        self.assertEqual(read_pdf(path), [
            {"type": "page", "text": "", "location": {"page": 1}},
            {"type": "page", "text": "", "location": {"page": 2}},
        ])

    def test_pdf_cli_prints_records_and_warns_on_stderr(self):
        path = self.make_blank_pdf()
        result = self.run_cli("pdf_reading.py", path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([record["location"]["page"] for record in json.loads(result.stdout)], [1, 2])
        self.assertIn("第 1 页未提取到文字", result.stderr)
        self.assertIn("第 2 页未提取到文字", result.stderr)

    def test_pdf_with_no_pages_returns_no_records_and_cli_reports_no_pages(self):
        path = self.make_blank_pdf(page_count=0)

        self.assertEqual(read_pdf(path), [])
        result = self.run_cli("pdf_reading.py", path)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("没有页记录", result.stderr)

    def test_empty_excel_returns_no_records_and_cli_reports_no_text(self):
        path = self.directory / "empty.xlsx"
        workbook = Workbook()
        workbook.active["A1"] = "   "
        workbook.save(path)
        workbook.close()

        self.assertEqual(read_excel(path), [])
        result = self.run_cli("excel_reading.py", path)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("未读取到有效文字", result.stderr)

    def test_excel_uses_saved_formula_values_including_zero(self):
        path = self.make_excel({"A1": "=1+1", "B2": "=2-2"}, {"A1": 2, "B2": 0})
        expected = [
            {
                "type": "cell",
                "text": "2",
                "location": {"sheet": "计算", "cell": "A1", "merged_range": None},
            },
            {
                "type": "cell",
                "text": "0",
                "location": {"sheet": "计算", "cell": "B2", "merged_range": None},
            },
        ]

        self.assertEqual(read_excel(path), expected)
        result = self.read_registered_excel(path)
        self.assertEqual(result["records"], expected)
        self.assertEqual(result["metadata"]["schema_version"], 2)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["warnings"], [])

    def test_excel_reports_uncached_formula_and_keeps_other_records(self):
        path = self.make_excel({"A1": "政策标题", "B2": "=1+1"})
        expected = [{
            "type": "cell",
            "text": "政策标题",
            "location": {"sheet": "计算", "cell": "A1", "merged_range": None},
        }]

        result = self.read_registered_excel(path)
        self.assertEqual(result["records"], expected)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(len(result["warnings"]), 1)
        warning = result["warnings"][0]
        self.assertEqual(set(warning), {"code", "message", "location"})
        self.assertEqual(warning["code"], "missing_formula_cache")
        self.assertEqual(warning["location"], {"sheet": "计算", "cell": "B2"})

        cli = self.run_cli("excel_reading.py", path)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(json.loads(cli.stdout), expected)
        self.assertIn(warning["message"], cli.stderr)
        self.assertIn("计算", warning["message"])
        self.assertIn("B2", warning["message"])

    def test_excel_with_only_uncached_formulas_is_empty(self):
        path = self.make_excel({"A1": "=1+1"})

        result = self.read_registered_excel(path)
        self.assertEqual(result["records"], [])
        self.assertEqual(result["status"], "empty")
        self.assertEqual(len(result["warnings"]), 1)
        warning = result["warnings"][0]
        self.assertEqual(warning["code"], "missing_formula_cache")
        self.assertEqual(warning["location"], {"sheet": "计算", "cell": "A1"})

        cli = self.run_cli("excel_reading.py", path)
        self.assertEqual(cli.returncode, 1)
        self.assertEqual(cli.stdout, "")
        self.assertIn(warning["message"], cli.stderr)
        self.assertIn("未读取到有效文字", cli.stderr)

    def test_excel_preserves_sheet_order_coordinates_and_merged_range(self):
        path = self.directory / "policy.xlsx"
        workbook = Workbook()
        first = workbook.active
        first.title = "政策"
        first.merge_cells("A1:B1")
        first["A1"] = "  标题  "
        first["B2"] = 0
        first["C2"] = "  "
        second = workbook.create_sheet("附件")
        second["C3"] = "第二张表"
        workbook.save(path)
        workbook.close()

        self.assertEqual(read_excel(path), [
            {
                "type": "cell",
                "text": "标题",
                "location": {"sheet": "政策", "cell": "A1", "merged_range": "A1:B1"},
            },
            {
                "type": "cell",
                "text": "0",
                "location": {"sheet": "政策", "cell": "B2", "merged_range": None},
            },
            {
                "type": "cell",
                "text": "第二张表",
                "location": {"sheet": "附件", "cell": "C3", "merged_range": None},
            },
        ])
