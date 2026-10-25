from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jarvis import automation


class ApprovedFileOperationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.roots = {
            "desktop": root / "Desktop",
            "documents": root / "Documents",
            "downloads": root / "Downloads",
        }
        for path in self.roots.values():
            path.mkdir(parents=True)
        patcher = patch.dict(automation.ROOTS, self.roots)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_copy_requires_approval_and_keeps_source(self) -> None:
        source = self.roots["documents"] / "notes.txt"
        source.write_text("JARVIS notes", encoding="utf-8")
        denied = Mock(return_value=False)
        result = automation.copy_file("Documents", "notes.txt", "Downloads", "notes-copy.txt", denied)
        self.assertIn("Cancelled", result)
        self.assertTrue(source.is_file())
        self.assertFalse((self.roots["downloads"] / "notes-copy.txt").exists())
        denied.assert_called_once()
        self.assertIn(str(source), denied.call_args.args[1])
        self.assertIn(str(self.roots["downloads"] / "notes-copy.txt"), denied.call_args.args[1])

        approved = Mock(return_value=True)
        result = automation.copy_file("Documents", "notes.txt", "Downloads", "notes-copy.txt", approved)
        self.assertIn("Copied file", result)
        self.assertTrue(source.is_file())
        self.assertEqual((self.roots["downloads"] / "notes-copy.txt").read_text(encoding="utf-8"), "JARVIS notes")

    def test_move_removes_source_only_after_copy_succeeds(self) -> None:
        source = self.roots["desktop"] / "report.md"
        destination = self.roots["documents"] / "report.md"
        source.write_text("# Report", encoding="utf-8")
        result = automation.move_file("Desktop", "report.md", "Documents", "report.md", lambda *_: True)
        self.assertIn("Moved file", result)
        self.assertFalse(source.exists())
        self.assertEqual(destination.read_text(encoding="utf-8"), "# Report")

    def test_rename_stays_in_same_folder(self) -> None:
        source = self.roots["downloads"] / "draft.txt"
        destination = self.roots["downloads"] / "final.txt"
        source.write_text("final content", encoding="utf-8")
        result = automation.rename_file("Downloads", "draft.txt", "final.txt", lambda *_: True)
        self.assertIn("Renamed file", result)
        self.assertFalse(source.exists())
        self.assertEqual(destination.read_text(encoding="utf-8"), "final content")

    def test_existing_destination_is_never_overwritten_or_approved(self) -> None:
        source = self.roots["documents"] / "source.txt"
        destination = self.roots["downloads"] / "target.txt"
        source.write_text("source data", encoding="utf-8")
        destination.write_text("keep existing data", encoding="utf-8")
        approval = Mock(return_value=True)
        result = automation.copy_file("Documents", "source.txt", "Downloads", "target.txt", approval)
        self.assertIn("Destination already exists", result)
        self.assertEqual(destination.read_text(encoding="utf-8"), "keep existing data")
        self.assertTrue(source.exists())
        approval.assert_not_called()

    def test_blocks_path_traversal(self) -> None:
        source = self.roots["documents"] / "source.txt"
        source.write_text("safe", encoding="utf-8")
        result = automation.copy_file("Documents", "../source.txt", "Downloads", "target.txt", lambda *_: True)
        self.assertIn("File operation blocked", result)
        self.assertFalse((self.roots["downloads"] / "target.txt").exists())

    def test_blocks_symbolic_link_sources(self) -> None:
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.roots["documents"] / "linked.txt"
        link.symlink_to(outside)
        result = automation.move_file("Documents", "linked.txt", "Downloads", "moved.txt", lambda *_: True)
        self.assertIn("Symbolic links are not supported", result)
        self.assertTrue(outside.exists())
        self.assertFalse((self.roots["downloads"] / "moved.txt").exists())


if __name__ == "__main__":
    unittest.main()
