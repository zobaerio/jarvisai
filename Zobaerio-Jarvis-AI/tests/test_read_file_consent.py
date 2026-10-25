from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from jarvis import automation


class ConsentGatedReadFileTests(unittest.TestCase):
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

    def test_declined_approval_returns_no_contents(self) -> None:
        path = self.roots["documents"] / "private.md"
        path.write_text("sensitive body text", encoding="utf-8")
        approval = Mock(return_value=False)
        result = automation.read_text_file("Documents", "private.md", approval)
        self.assertIn("Cancelled", result)
        self.assertNotIn("sensitive body text", result)
        approval.assert_called_once()
        self.assertEqual(approval.call_args.args[0], "Confirm read file")
        self.assertIn(str(path), approval.call_args.args[1])
        self.assertIn("may be sent to the configured AI provider", approval.call_args.args[1])

    def test_approved_read_returns_text(self) -> None:
        path = self.roots["desktop"] / "notes.txt"
        path.write_text("hello JARVIS", encoding="utf-8")
        approval = Mock(return_value=True)
        result = automation.read_text_file("Desktop", "notes.txt", approval)
        self.assertIn("Contents of", result)
        self.assertIn("hello JARVIS", result)
        approval.assert_called_once()

    def test_too_large_file_is_rejected_before_approval(self) -> None:
        (self.roots["documents"] / "large.txt").write_text("x" * 100_001, encoding="utf-8")
        approval = Mock(return_value=True)
        result = automation.read_text_file("Documents", "large.txt", approval)
        self.assertIn("larger than 100 KB", result)
        approval.assert_not_called()

    def test_unsupported_executable_is_rejected_before_approval(self) -> None:
        (self.roots["downloads"] / "program.exe").write_bytes(b"not executable")
        approval = Mock(return_value=True)
        result = automation.read_text_file("Downloads", "program.exe", approval)
        self.assertIn("common text and source-code files only", result)
        approval.assert_not_called()

    def test_null_byte_binary_is_not_returned(self) -> None:
        (self.roots["documents"] / "binary.txt").write_bytes(b"text \x00payload")
        approval = Mock(return_value=True)
        result = automation.read_text_file("Documents", "binary.txt", approval)
        self.assertIn("binary data", result)
        self.assertNotIn("payload", result)

    def test_blocks_symlink_and_path_traversal(self) -> None:
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("outside", encoding="utf-8")
        link = self.roots["documents"] / "linked.txt"
        link.symlink_to(outside)
        result = automation.read_text_file("Documents", "linked.txt", lambda *_: True)
        self.assertIn("Symbolic links are not supported", result)
        traversal = automation.read_text_file("Documents", "../outside.txt", lambda *_: True)
        self.assertIn("File read blocked", traversal)

    def test_file_changed_during_approval_is_not_returned(self) -> None:
        path = self.roots["documents"] / "mutable.md"
        path.write_text("old content", encoding="utf-8")
        def change_file(_title, _detail):
            path.write_text("new content which is longer", encoding="utf-8")
            return True
        result = automation.read_text_file("Documents", "mutable.md", change_file)
        self.assertIn("changed after confirmation", result)
        self.assertNotIn("old content", result)
        self.assertNotIn("new content which is longer", result)


if __name__ == "__main__":
    unittest.main()
