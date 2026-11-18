import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.paths import SAMPLES_DIR, SOURCES_FILE
from scripts.sources import find_source_file, load_sources, validate_sources


VALID_MANIFEST = {
    "schema_version": 1,
    "sources": [{
        "source_id": "policy-test",
        "title": "测试政策",
        "page_url": "https://example.com/page",
        "category": None,
        "department": "教务处",
        "publisher": None,
        "published_date": "2026-01-02",
        "collected_date": "2026-01-03",
        "files": [
            {"path": "body.md", "role": "body", "download_url": None, "parse": True},
            {
                "path": "attachments/files.zip", "role": "archive",
                "download_url": "https://example.com/files.zip", "parse": False,
            },
            {
                "path": "attachments/unpacked/a.pdf", "role": "attachment",
                "download_url": None, "parse": True,
                "extracted_from": "attachments/files.zip",
            },
        ],
    }],
}


class RealManifestTests(unittest.TestCase):
    def test_project_manifest_matches_sample_files(self):
        problems = validate_sources(load_sources())
        self.assertEqual(problems, [], "\n".join(problems))

    def test_project_file_is_found_by_absolute_path(self):
        body = SAMPLES_DIR / "policy-002" / "body.md"
        source, entry = find_source_file(body, load_sources())
        self.assertEqual(source["source_id"], "policy-002")
        self.assertEqual(entry["role"], "body")

    def test_manifest_is_at_expected_location(self):
        self.assertEqual(SOURCES_FILE.parent, SAMPLES_DIR)
        self.assertTrue(SOURCES_FILE.is_file())


class ValidateSourcesTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.samples = Path(self.temporary.name) / "samples"
        for relative in ["body.md", "attachments/files.zip", "attachments/unpacked/a.pdf"]:
            file = self.samples / "policy-test" / relative
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b"x")
        self.manifest = copy.deepcopy(VALID_MANIFEST)

    def problems(self):
        return validate_sources(self.manifest, self.samples)

    def assertProblem(self, fragment):
        problems = self.problems()
        self.assertTrue(
            any(fragment in problem for problem in problems),
            f"未找到包含“{fragment}”的问题：{problems}",
        )

    def test_valid_manifest_has_no_problems(self):
        (self.samples / "sources.json").write_text("{}", encoding="utf-8")
        self.assertEqual(self.problems(), [])

    def test_missing_and_unregistered_files_are_reported(self):
        (self.samples / "policy-test" / "body.md").unlink()
        (self.samples / "policy-test" / "extra.pdf").write_bytes(b"x")
        self.assertProblem("登记的文件不存在：body.md")
        self.assertProblem("未登记的文件：policy-test/extra.pdf")

    def test_source_id_must_match_directory_and_be_unique(self):
        duplicate = copy.deepcopy(self.manifest["sources"][0])
        duplicate["files"] = []
        self.manifest["sources"].append(duplicate)
        self.assertProblem("source_id 重复")

        self.manifest["sources"][0]["source_id"] = "policy-other"
        self.assertProblem("找不到同名样本目录")

    def test_fields_roles_and_dates_are_checked(self):
        source = self.manifest["sources"][0]
        del source["publisher"]
        source["extra"] = 1
        source["published_date"] = "2026/01/02"
        source["files"][0]["role"] = "main"
        self.assertProblem("缺少字段 publisher")
        self.assertProblem("未知字段 extra")
        self.assertProblem("published_date 不是 YYYY-MM-DD 日期")
        self.assertProblem("role 无效")

    def test_archive_rules_and_paths_are_checked(self):
        files = self.manifest["sources"][0]["files"]
        files[1]["parse"] = True
        files[2]["extracted_from"] = "attachments/missing.zip"
        files[0]["path"] = "../body.md"
        self.assertProblem("parse 应为 false")
        self.assertProblem("extracted_from 未指向本来源的压缩包")
        self.assertProblem("相对 POSIX 路径")

    def test_parse_must_be_boolean(self):
        self.manifest["sources"][0]["files"][0]["parse"] = "true"
        self.assertProblem("parse 应为布尔值")

    def test_duplicate_registration_and_schema_version(self):
        files = self.manifest["sources"][0]["files"]
        files.append(copy.deepcopy(files[0]))
        self.manifest["schema_version"] = 2
        self.assertProblem("文件重复登记：body.md")
        self.assertProblem("schema_version 应为 1")

    def test_find_source_file_uses_manifest_for_any_path_form(self):
        pdf = self.samples / "policy-test" / "attachments" / "unpacked" / "a.pdf"
        previous_directory = Path.cwd()
        self.addCleanup(os.chdir, previous_directory)
        os.chdir(pdf.parent)

        # 绝对路径、当前目录下的相对路径、带 .. 的相对路径都应找到同一份登记。
        for path, expected_path in [
            (pdf, "attachments/unpacked/a.pdf"),
            ("a.pdf", "attachments/unpacked/a.pdf"),
            ("../files.zip", "attachments/files.zip"),
        ]:
            with self.subTest(path=str(path)):
                source, entry = find_source_file(path, self.manifest, self.samples)
                self.assertEqual(source["source_id"], "policy-test")
                self.assertEqual(entry["path"], expected_path)

    def test_find_source_file_rejects_unregistered_files(self):
        extra = self.samples / "policy-test" / "extra.pdf"
        extra.write_bytes(b"x")
        outside = Path(self.temporary.name) / "outside.pdf"
        outside.write_bytes(b"x")
        for path in [extra, outside, self.samples / "policy-test" / "missing.pdf"]:
            with self.subTest(path=path.name), self.assertRaises(LookupError):
                find_source_file(path, self.manifest, self.samples)

    def test_load_sources_reads_utf8_and_reports_invalid_json(self):
        manifest_file = self.samples / "sources.json"
        manifest_file.write_text(json.dumps(VALID_MANIFEST, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(load_sources(manifest_file), VALID_MANIFEST)

        manifest_file.write_text("not JSON", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            load_sources(manifest_file)


if __name__ == "__main__":
    unittest.main()
