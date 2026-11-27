import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook
from pypdf import PdfWriter

from scripts.excel_reading import read_excel
from scripts.paths import PROJECT_ROOT
from scripts.pdf_reading import read_pdf


class AttachmentReaderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def make_blank_pdf(self):
        path = self.directory / "blank.pdf"
        writer = PdfWriter()
        for _ in range(2):
            writer.add_blank_page(width=72, height=72)
        with path.open("wb") as stream:
            writer.write(stream)
        return path

    def test_pdf_preserves_original_page_numbers_including_empty_pages(self):
        path = self.make_blank_pdf()

        self.assertEqual(read_pdf(path), [
            {"type": "page", "text": "", "location": {"page": 1}},
            {"type": "page", "text": "", "location": {"page": 2}},
        ])

    def test_pdf_cli_prints_records_and_warns_on_stderr(self):
        path = self.make_blank_pdf()
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "pdf_reading.py"), str(path)],
            capture_output=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([record["location"]["page"] for record in json.loads(result.stdout)], [1, 2])
        self.assertIn("第 1 页未提取到文字", result.stderr)
        self.assertIn("第 2 页未提取到文字", result.stderr)

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
        second["C3"] = "=1+1"
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
                "text": "=1+1",
                "location": {"sheet": "附件", "cell": "C3", "merged_range": None},
            },
        ])
