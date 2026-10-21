"""Release archives must contain only explicitly public, reviewed source files."""

from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from package_source import ROOT_NAME, REQUIRED_SOURCE_FILES, SourcePackageError, collect_files, package


class SourcePackageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        for name in REQUIRED_SOURCE_FILES:
            self.write(name, "Original public fixture")

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, name, contents):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return path

    def test_only_allowlisted_source_and_neutral_examples_are_included(self):
        forbidden = [".env", ".git/config", "dist/company.zip", "screenshots/private.png", "examples/private-catalogue.pdf", "examples/demo/pages/private.png", "scripts/__pycache__/private.pyc", "node_modules/library/index.js", "scripts/token.txt"]
        for name in forbidden:
            self.write(name, "PRIVATE-MUST-NOT-BE-PUBLISHED")
        output = self.root / "source.zip"
        report = package(self.repo, output)
        self.assertTrue(report["crcValid"])
        with zipfile.ZipFile(output) as archive:
            self.assertIsNone(archive.testzip())
            self.assertIn(ROOT_NAME + "/examples/demo/pages/page-012.png", archive.namelist())
            self.assertTrue(all(name.startswith(ROOT_NAME + "/") for name in archive.namelist()))
            self.assertFalse(any(b"PRIVATE-MUST-NOT-BE-PUBLISHED" in archive.read(name) for name in archive.namelist()))
        self.assertIn(report["sha256"], output.with_name("source.zip.sha256").read_text("ascii"))

    def test_existing_archives_and_checksums_are_not_overwritten(self):
        output = self.root / "source.zip"
        output.write_bytes(b"keep original")
        with self.assertRaisesRegex(SourcePackageError, "already exists"):
            package(self.repo, output)
        self.assertEqual(output.read_bytes(), b"keep original")
        another = self.root / "another.zip"
        another.with_name("another.zip.sha256").write_text("keep checksum", encoding="ascii")
        with self.assertRaisesRegex(SourcePackageError, "already exists"):
            package(self.repo, another)
        self.assertFalse(another.exists())

    def test_missing_required_file_is_reported(self):
        (self.repo / "SKILL.md").unlink()
        with self.assertRaisesRegex(SourcePackageError, "SKILL.md"):
            collect_files(self.repo)

    def test_same_source_produces_reproducible_archive(self):
        first = self.root / "first.zip"
        second = self.root / "second.zip"
        package(self.repo, first)
        package(self.repo, second)
        self.assertEqual(first.read_bytes(), second.read_bytes())


if __name__ == "__main__":
    unittest.main()
