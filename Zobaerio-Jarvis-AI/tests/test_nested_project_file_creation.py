from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis import automation


class NestedProjectFileCreationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Desktop"
        (self.root / "CivilOS" / "Reports").mkdir(parents=True)
        self.roots = {
            "desktop": self.root,
            "documents": Path(self.temp.name) / "Documents",
            "downloads": Path(self.temp.name) / "Downloads",
        }
        patcher = patch.dict(automation.ROOTS, self.roots)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_creates_file_in_existing_project_subfolder_after_approval(self) -> None:
        approvals = []
        result = automation.create_text_file(
            "Desktop",
            "CivilOS/Reports/summary.md",
            "# Project summary\n",
            lambda title, detail: approvals.append((title, detail)) or True,
        )
        target = self.root / "CivilOS" / "Reports" / "summary.md"
        self.assertIn("Created file:", result)
        self.assertEqual(target.read_text(encoding="utf-8"), "# Project summary\n")
        self.assertEqual(len(approvals), 1)
        self.assertIn(str(target), approvals[0][1])

    def test_cancel_does_not_create_nested_file(self) -> None:
        result = automation.create_text_file(
            "Desktop", "CivilOS/Reports/summary.md", "draft", lambda *_: False
        )
        self.assertIn("Cancelled", result)
        self.assertFalse((self.root / "CivilOS" / "Reports" / "summary.md").exists())

    def test_blocks_traversal_and_reserved_paths(self) -> None:
        for path in ("../outside.md", "CivilOS/../../outside.md", "CivilOS/Reports/bad?.md", "/tmp/escape.md"):
            with self.subTest(path=path):
                result = automation.create_text_file("Desktop", path, "x", lambda *_: True)
                self.assertIn("blocked", result.casefold())
        self.assertFalse((Path(self.temp.name) / "outside.md").exists())

    def test_requires_parent_folder_to_exist(self) -> None:
        result = automation.create_text_file(
            "Desktop", "CivilOS/Missing/file.md", "x", lambda *_: True
        )
        self.assertIn("parent folder must already exist", result.casefold())
        self.assertFalse((self.root / "CivilOS" / "Missing").exists())

    def test_never_overwrites_existing_file(self) -> None:
        target = self.root / "CivilOS" / "Reports" / "summary.md"
        target.write_text("keep me", encoding="utf-8")
        result = automation.create_text_file(
            "Desktop", "CivilOS/Reports/summary.md", "replace me", lambda *_: True
        )
        self.assertIn("will not overwrite", result)
        self.assertEqual(target.read_text(encoding="utf-8"), "keep me")


if __name__ == "__main__":
    unittest.main()
